"""Paystack webhook receiver.

Paystack signs every webhook with an HMAC-SHA512 of the raw request body using
the secret key. We verify the signature before trusting any event and rely on
``services.handle_webhook_event`` for idempotent processing.
"""
import hashlib
import hmac
import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .services import handle_webhook_event, secret_key
from .utils import log_payment


@csrf_exempt
@require_POST
def paystack_webhook(request):
    raw_body = request.body

    signature = request.headers.get('X-Paystack-Signature', '')
    digest = hmac.new(
        secret_key().encode('utf-8'),
        raw_body,
        hashlib.sha512,
    ).hexdigest()

    if not hmac.compare_digest(digest, signature):
        log_payment('Webhook signature mismatch', level=30)
        return HttpResponse('Invalid signature', status=400)

    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        log_payment('Webhook invalid JSON', level=30)
        return HttpResponse('Invalid payload', status=400)

    handled = handle_webhook_event(payload)
    # Paystack expects a 200 to consider delivery successful.
    return HttpResponse('OK' if handled else 'Ignored', status=200)
