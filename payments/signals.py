"""Django signals for the payments app.

A single ``payment_completed`` signal is emitted whenever a payment is
confirmed (via webhook, callback verification or manual admin verify).
Receivers persist structured notifications (already shown in the notification
bell) and are the extension point for pushing live updates over WebSockets.
"""
from django.db.models.signals import post_save
from django.dispatch import Signal, receiver

from Foodcourt.delivery_services import notify_restaurant, notify_user

from .models import Payment

# Sent with ``payment=<Payment instance>`` after a payment succeeds.
payment_completed = Signal()


@receiver(payment_completed)
def on_payment_completed(sender, payment, **kwargs):
    order = payment.order
    restaurant = order.restaurant

    if restaurant is not None:
        notify_restaurant(
            restaurant,
            title='New paid order received',
            message=f"Order {order.order_id} has been paid. Total {payment.amount:.2f} {payment.currency}.",
            kind='order',
            order=order,
            link='/restaurant-admin/',
        )

    notify_user(
        order.user,
        title='Payment successful',
        message=f"Your payment for order {order.order_id} of {payment.amount:.2f} {payment.currency} was received.",
        kind='order',
        order=order,
        link=f'/tracking/{order.order_id}/',
    )


@receiver(post_save, sender=Payment)
def log_payment_saved(sender, instance, created, **kwargs):
    """Record failed/cancelled outcomes as info notifications for the user."""
    if created:
        return
    if instance.status == Payment.Status.FAILED:
        notify_user(
            instance.customer,
            title='Payment failed',
            message=f"Your payment for order {instance.order.order_id} failed. You can retry it.",
            kind='order',
            order=instance.order,
            link=f'/payments/result/{instance.order.order_id}/',
        )
