"""Business logic for Paystack payments.

All Paystack API calls and the post-payment fulfilment flow live here so the
views and webhook stay thin. The service layer is also where notifications,
receipt data and order status transitions are coordinated.
"""
import requests
import time
from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.urls import reverse
from django.utils import timezone
from urllib.parse import urljoin

from .models import Payment
from .signals import payment_completed
from .utils import from_kobo, generate_reference, log_payment, to_kobo

from Foodcourt.notifications import send_order_confirmation_emails
from Foodcourt.models import Coupon

PAYSTACK_BASE_URL = 'https://api.paystack.co'
PAYSTACK_INITIALIZE_URL = urljoin(PAYSTACK_BASE_URL, '/transaction/initialize')
PAYSTACK_VERIFY_URL = urljoin(PAYSTACK_BASE_URL, '/transaction/verify')
PAYSTACK_BANKS_URL = urljoin(PAYSTACK_BASE_URL, '/bank')
PAYSTACK_BANK_RESOLVE_URL = urljoin(PAYSTACK_BASE_URL, '/bank/resolve')
PAYSTACK_TIMEOUT = 15

_BANKS_CACHE = {'at': 0.0, 'data': []}
_BANKS_TTL = 86400  # refresh the bank list at most once a day

DEFAULT_CHANNELS = ['card', 'bank', 'ussd', 'apple_pay', 'google_pay']


class PaystackError(Exception):
    """Raised for any problem talking to the Paystack API or validating a key."""


def secret_key():
    key = getattr(settings, 'PAYSTACK_SECRET_KEY', '')
    if not key or key == 'PAYSTACK_TEST_SECRET_KEY':
        raise PaystackError(
            'PAYSTACK_SECRET_KEY is not configured. Set it in your environment.'
        )
    return key


def public_key():
    return getattr(settings, 'PAYSTACK_PUBLIC_KEY', '')


def currency():
    return getattr(settings, 'PAYSTACK_CURRENCY', 'NGN')


def _headers():
    return {
        'Authorization': f'Bearer {secret_key()}',
        'Content-Type': 'application/json',
    }


def list_banks(currency_code='NGN'):
    """Return supported banks as ``[{'name': ..., 'code': ...}, ...]``.

    Fetched from Paystack and cached in memory for a day so the rider
    registration form doesn't hit the API on every page view.
    """
    now = time.time()
    if _BANKS_CACHE['data'] and (now - _BANKS_CACHE['at']) < _BANKS_TTL:
        return _BANKS_CACHE['data']

    try:
        response = requests.get(
            PAYSTACK_BANKS_URL,
            params={'currency': currency_code, 'per_page': 100},
            headers=_headers(),
            timeout=PAYSTACK_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise PaystackError('Could not reach Paystack. Please try again.') from exc

    try:
        body = response.json()
    except ValueError:
        body = {}

    if response.status_code != 200 or not body.get('status'):
        message = body.get('message') or 'Could not load bank list.'
        raise PaystackError(message)

    banks = [
        {'name': item.get('name'), 'code': item.get('code')}
        for item in body.get('data', [])
        if item.get('code') and item.get('name')
    ]
    _BANKS_CACHE.update(at=now, data=banks)
    return banks


def resolve_bank_account(bank_code, account_number):
    """Resolve an account name for a NUBAN account via Paystack.

    Returns the account holder name, or raises :class:`PaystackError` if
    the bank/number pair can't be resolved.
    """
    params = {
        'bank_code': str(bank_code),
        'account_number': str(account_number),
    }
    try:
        response = requests.get(
            PAYSTACK_BANK_RESOLVE_URL,
            params=params,
            headers=_headers(),
            timeout=PAYSTACK_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise PaystackError('Could not reach Paystack. Please try again.') from exc

    try:
        body = response.json()
    except ValueError:
        body = {}

    if response.status_code != 200 or not body.get('status'):
        message = body.get('message') or 'Account could not be verified.'
        raise PaystackError(message)

    data = body.get('data') or {}
    account_name = (data.get('account_name') or '').strip()
    if not account_name:
        raise PaystackError('Account could not be verified.')
    return account_name


# ── Lifecycle helpers ─────────────────────────────────────────────────────

def get_or_create_payment(order):
    """Return the Payment row for an order, creating a fresh pending one."""
    payment, created = Payment.objects.get_or_create(
        order=order,
        defaults={
            'customer': order.user,
            'amount': order.total,
            'currency': currency(),
            'transaction_reference': generate_reference(),
        },
    )
    if not created:
        # Reusing an existing row (retry) — reset to a fresh pending attempt.
        payment.status = Payment.Status.PENDING
        payment.paystack_reference = ''
        payment.paid_at = None
        payment.gateway_response = {}
        payment.save(update_fields=[
            'status', 'paystack_reference', 'paid_at', 'gateway_response', 'updated_at',
        ])
    return payment


def _metadata(order):
    return {
        'order_id': order.order_id,
        'customer_id': order.user_id,
        'custom_fields': [
            {'display_name': 'Order ID', 'variable_name': 'order_id', 'value': order.order_id},
            {'display_name': 'Customer Email', 'variable_name': 'customer_email', 'value': order.user.email},
        ],
    }


def initialize_payment(order, request, channels=None):
    """Initialise a Paystack transaction for an order.

    Returns ``{'reference', 'access_code', 'authorization_url'}``. The order
    stays ``pending`` until the webhook / callback confirms payment.
    """
    if not order or order.total <= 0:
        raise PaystackError('Cannot initialise payment for an empty order.')

    payment = get_or_create_payment(order)
    amount_kobo = to_kobo(order.total)
    callback_url = request.build_absolute_uri(reverse('payments:payments_callback'))

    payload = {
        'email': order.user.email,
        'amount': amount_kobo,
        'currency': currency(),
        'reference': payment.transaction_reference,
        'callback_url': callback_url,
        'metadata': _metadata(order),
    }
    if channels:
        payload['channels'] = channels

    try:
        response = requests.post(
            PAYSTACK_INITIALIZE_URL,
            json=payload,
            headers=_headers(),
            timeout=PAYSTACK_TIMEOUT,
        )
    except requests.RequestException as exc:
        log_payment('Paystack initialize network error', {'reference': payment.transaction_reference, 'error': str(exc)}, level=30)
        raise PaystackError('Could not reach Paystack. Please try again.') from exc

    try:
        body = response.json()
    except ValueError:
        body = {}

    log_payment('Paystack initialize response', {
        'reference': payment.transaction_reference,
        'status_code': response.status_code,
        'body': body,
    })

    if response.status_code != 200 or not body.get('status'):
        message = (body.get('message') or 'Paystack initialisation failed. Please try again.')
        raise PaystackError(message)

    data = body.get('data') or {}
    payment.paystack_reference = data.get('reference', payment.transaction_reference)
    payment.gateway_response = data
    payment.save(update_fields=['paystack_reference', 'gateway_response', 'updated_at'])

    return {
        'reference': payment.paystack_reference,
        'access_code': data.get('access_code', ''),
        'authorization_url': data.get('authorization_url', ''),
    }


def verify_payment(payment):
    """Verify a payment server-side. Never trust the browser/redirect alone."""
    reference = payment.paystack_reference or payment.transaction_reference
    verify_url = f"{PAYSTACK_VERIFY_URL}/{reference}"

    try:
        response = requests.get(verify_url, headers=_headers(), timeout=PAYSTACK_TIMEOUT)
    except requests.RequestException as exc:
        log_payment('Paystack verify network error', {'reference': reference, 'error': str(exc)}, level=30)
        raise PaystackError('Could not verify payment with Paystack. Please try again.') from exc

    try:
        body = response.json()
    except ValueError:
        body = {}

    if response.status_code == 404:
        log_payment('Paystack verify: transaction not found', {'reference': reference}, level=30)
        payment.status = Payment.Status.FAILED
        payment.gateway_response = {'error': 'transaction not found'}
        payment.save(update_fields=['status', 'gateway_response', 'updated_at'])
        return payment

    if response.status_code != 200 or not body.get('status'):
        log_payment('Paystack verify: invalid response', {'reference': reference, 'status_code': response.status_code, 'body': body}, level=30)
        raise PaystackError('Paystack verification failed. Please try again.')

    data = body.get('data') or {}
    gateway_status = (data.get('status') or '').lower()

    payment.gateway_response = data

    if gateway_status == 'success':
        _mark_successful(payment, data)
    else:
        payment.status = Payment.Status.CANCELLED if gateway_status == 'abandoned' else Payment.Status.FAILED
        payment.save(update_fields=['status', 'gateway_response', 'updated_at'])

    return payment


def _mark_successful(payment, data):
    """Idempotently mark a payment successful and fulfil its order."""
    if payment.status == Payment.Status.SUCCESSFUL:
        return

    order = payment.order
    with transaction.atomic():
        payment.status = Payment.Status.SUCCESSFUL
        payment.paid_at = timezone.now()
        payment.amount = from_kobo(data.get('amount', to_kobo(payment.amount)))
        payment.save(update_fields=['status', 'paid_at', 'amount', 'gateway_response', 'updated_at'])

        # Order transition: pending payment -> confirmed & accepted.
        order.status = 'confirmed'
        order.is_accepted = True
        order.save(update_fields=['status', 'is_accepted'])

        # Increment coupon usage now that the order is paid & confirmed.
        # Failed/cancelled/abandoned orders never reach here, so they do not
        # consume coupon usage. This runs inside the same transaction as the
        # confirmation, so it is also idempotent (guarded by the status check
        # above when the webhook is delivered more than once).
        coupon_code = order.coupon_code if hasattr(order, 'coupon_code') else None
        if coupon_code:
            Coupon.objects.filter(code=coupon_code, is_active=True).update(
                times_used=F('times_used') + 1
            )

    payment_completed.send(sender=Payment, payment=payment)
    send_order_confirmation_emails(order)
    log_payment('Payment fulfilled', {'reference': payment.transaction_reference, 'order': order.order_id})


# ── Webhook handling ──────────────────────────────────────────────────────

def handle_webhook_event(payload):
    """Process a verified Paystack webhook event (idempotent).

    Returns a boolean indicating whether the event was handled.
    """
    event = payload.get('event', '')
    data = payload.get('data') or {}

    if event != 'charge.success':
        log_payment('Webhook event ignored', {'event': event})
        return False

    reference = data.get('reference') or ''
    if not reference:
        log_payment('Webhook missing reference', {'event': event}, level=30)
        return False

    payment = Payment.objects.filter(
        paystack_reference=reference
    ).select_related('order').first()

    if payment is None:
        log_payment('Webhook for unknown payment', {'reference': reference}, level=30)
        return False

    # Idempotency: already fulfilled payments are ignored.
    if payment.status == Payment.Status.SUCCESSFUL:
        log_payment('Webhook duplicate, already fulfilled', {'reference': reference})
        return True

    payment.gateway_response = data
    _mark_successful(payment, data)
    return True


def cancel_payment(order):
    """Mark an abandoned/failed payment as cancelled (used by retry flow)."""
    payment = getattr(order, 'payment', None)
    if payment is None or payment.status == Payment.Status.SUCCESSFUL:
        return
    payment.status = Payment.Status.CANCELLED
    payment.save(update_fields=['status', 'updated_at'])
