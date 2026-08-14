from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

from Foodcourt.models import Order

from .models import Payment
from .services import (
    PaystackError,
    cancel_payment,
    initialize_payment,
    verify_payment,
)


def _owned_order(request, order_id):
    return get_object_or_404(
        Order, order_id=order_id, user=request.user
    )


@login_required(login_url='login')
def payment_callback(request):
    """Redirect target for Paystack. We always verify server-side."""
    reference = request.GET.get('reference', '')
    if not reference:
        messages.error(request, 'Missing payment reference.')
        return redirect('dashboard')

    payment = Payment.objects.filter(paystack_reference=reference).first()
    if payment is None:
        payment = Payment.objects.filter(transaction_reference=reference).first()

    if payment is None or payment.order.user != request.user:
        messages.error(request, 'Payment not found for this account.')
        return redirect('dashboard')

    try:
        verify_payment(payment)
    except PaystackError as exc:
        messages.error(request, str(exc))

    return redirect('payments:payments_result', order_id=payment.order.order_id)


@login_required(login_url='login')
def payment_result(request, order_id):
    """Show the outcome of a payment attempt with retry / receipt actions."""
    order = _owned_order(request, order_id)
    payment = getattr(order, 'payment', None)
    if payment is None:
        return redirect('dashboard')

    return render(request, 'payments/result.html', {
        'order': order,
        'payment': payment,
    })


@login_required(login_url='login')
def payment_receipt(request, order_id):
    """Printable receipt for a successful order."""
    order = _owned_order(request, order_id)
    payment = getattr(order, 'payment', None)

    return render(request, 'payments/receipt.html', {
        'order': order,
        'payment': payment,
        'items': order.items.all(),
    })


@login_required(login_url='login')
@require_GET
def payment_retry(request, order_id):
    """Re-initialise a Paystack transaction for a previously failed order."""
    order = _owned_order(request, order_id)

    if order.status in ('delivered', 'cancelled'):
        messages.error(request, 'This order can no longer be paid for.')
        return redirect('payments:payments_result', order_id=order.order_id)

    cancel_payment(order)

    try:
        result = initialize_payment(order, request)
    except PaystackError as exc:
        messages.error(request, str(exc))
        return redirect('payments:payments_result', order_id=order.order_id)

    return redirect(result['authorization_url'])
