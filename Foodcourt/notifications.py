"""Shared email helpers for FoodCourt.

Kept out of ``Foodcourt.views`` so the payments service layer can send
order-confirmation emails without creating a circular import.
"""
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags


def _site_url(path):
    base = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000').rstrip('/')
    return f"{base}{path}"


def send_email(subject, template_name, context, recipient_list):
    try:
        html = render_to_string(template_name, context)
        plain = strip_tags(html)
        send_mail(subject, plain, settings.DEFAULT_FROM_EMAIL, recipient_list, html_message=html)
        return True
    except Exception as e:
        print(f"[send_email] Failed to send '{subject}' to {recipient_list}: {e}")
        return False


def _fmt(value):
    try:
        return f"{Decimal(str(value)):,.2f}"
    except (InvalidOperation, TypeError, ValueError):
        return '0.00'


def _order_context(order):
    return {
        'order_id': order.order_id,
        'restaurant_name': order.restaurant_name,
        'customer_name': order.user.get_full_name() or order.user.email,
        'customer_email': order.user.email,
        'delivery_address': order.delivery_address,
        'payment_method': order.payment_method.title(),
        'subtotal': _fmt(order.subtotal),
        'delivery_fee': _fmt(order.delivery_fee),
        'discount': _fmt(order.discount),
        'total': _fmt(order.total),
        'created_at': order.created_at,
        'tracking_url': _site_url(reverse('tracking_detail', args=[order.order_id])),
        'items': [
            {
                'name': i.name,
                'quantity': i.quantity,
                'price': _fmt(i.price),
                'line_total': _fmt(i.price * i.quantity),
            }
            for i in order.items.all()
        ],
    }


def send_order_confirmation_emails(order):
    """Email the customer (order confirmation) and the restaurant (new order).

    Safe to call more than once — sending is cheap and the templates are static.
    """
    context = _order_context(order)

    send_email(
        subject=f"Order confirmed — {order.order_id}",
        template_name="emails/order_confirmation.html",
        context=context,
        recipient_list=[order.user.email],
    )

    restaurant = order.restaurant
    if restaurant is not None:
        restaurant_email = (restaurant.email or '').strip()
        if not restaurant_email and restaurant.owner:
            restaurant_email = restaurant.owner.email or ''
        if restaurant_email:
            send_email(
                subject=f"New order received — {order.order_id}",
                template_name="emails/order_restaurant_notification.html",
                context={**context, 'dashboard_url': _site_url(reverse('restaurant_dashboard'))},
                recipient_list=[restaurant_email],
            )
