"""Business logic for the order delivery and rider assignment system.

All delivery workflow rules live here so views stay thin and the logic is
reusable. The notification helper persists to the Notification model so the
system can later be upgraded to push notifications over WebSockets without
changing the service layer.
"""
import random
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import Delivery, DeliveryStatusLog, Notification, Order, Riders

ACTIVE_STATUSES = ['assigned', 'arrived_at_restaurant', 'picked_up', 'on_the_way', 'arrived']
SEARCHING_STATUSES = ['searching']
FINAL_STATUSES = ['delivered', 'cancelled']

# Rider-driven transition map: current status -> set of allowed next statuses
TRANSITIONS = {
    'assigned': {'arrived_at_restaurant'},
    'arrived_at_restaurant': {'picked_up'},
    'picked_up': {'on_the_way'},
    'on_the_way': {'arrived'},
    'arrived': {'delivered'},
}


# ── Notifications ──────────────────────────────────────────────────────────

def notify_user(user, title, message, kind='info', order=None, delivery=None, link=''):
    if user is None:
        return
    Notification.objects.create(
        user=user, order=order, delivery=delivery, kind=kind,
        title=title, message=message, link=link,
    )


def notify_rider(rider, title, message, kind='info', order=None, delivery=None, link=''):
    if rider is None:
        return
    Notification.objects.create(
        rider=rider, order=order, delivery=delivery, kind=kind,
        title=title, message=message, link=link,
    )


def notify_restaurant(restaurant, title, message, kind='info', order=None, delivery=None, link=''):
    if restaurant is None:
        return
    Notification.objects.create(
        restaurant=restaurant, order=order, delivery=delivery, kind=kind,
        title=title, message=message, link=link,
    )


# ── Eligibility ─────────────────────────────────────────────────────────────

def rider_has_active_delivery(rider):
    return Delivery.objects.filter(rider=rider, status__in=ACTIVE_STATUSES).exists()


def is_rider_eligible(rider):
    if rider is None:
        return False
    if rider.status != 'approved' or not rider.is_active:
        return False
    if not rider.is_online or not rider.is_available:
        return False
    return not rider_has_active_delivery(rider)


def eligible_riders():
    candidates = Riders.objects.filter(status='approved', is_active=True, is_online=True, is_available=True)
    return [r for r in candidates if is_rider_eligible(r)]


# ── Status tracking ─────────────────────────────────────────────────────────

def record_status(delivery, status, note=''):
    label = dict(Delivery.STATUS_CHOICES).get(status, status)
    DeliveryStatusLog.objects.create(delivery=delivery, status=status, label=label, note=note)

    timestamp_map = {
        'assigned': 'accepted_at',
        'arrived_at_restaurant': 'arrived_at_restaurant_at',
        'picked_up': 'picked_up_at',
        'on_the_way': 'on_the_way_at',
        'arrived': 'arrived_at',
        'delivered': 'delivered_at',
        'cancelled': 'cancelled_at',
    }
    timestamp_field = timestamp_map.get(status)
    if timestamp_field and not getattr(delivery, timestamp_field):
        setattr(delivery, timestamp_field, timezone.now())
    delivery.status = status
    delivery.save(update_fields=['status', timestamp_field] if timestamp_field else ['status'])
    return delivery


# ── Delivery creation ───────────────────────────────────────────────────────

def create_delivery_for_order(order):
    """Create a Delivery for a ready order and notify all eligible riders."""
    delivery, created = Delivery.objects.get_or_create(order=order)
    if not created:
        return delivery
    record_status(delivery, 'searching', 'Delivery created — searching for a rider')
    notify_riders_of_delivery(delivery)
    return delivery


def notify_riders_of_delivery(delivery):
    order = delivery.order
    riders = eligible_riders()
    for rider in riders:
        delivery.notified_riders.add(rider)
        notify_rider(
            rider,
            'New delivery request',
            f'{order.restaurant_name} order #{order.order_id} is ready for pickup. Paying ₦{float(delivery.payout or order.delivery_fee or 0):.2f}.',
            kind='delivery',
            order=order,
            delivery=delivery,
            link='/riders/dashboard/',
        )


# ── Assignment ──────────────────────────────────────────────────────────────

def accept_delivery(delivery, rider):
    """Atomically assign the first rider to accept. Returns (ok, error)."""
    if delivery is None or rider is None:
        return False, 'Invalid delivery request.'

    with transaction.atomic():
        locked = Delivery.objects.select_for_update().get(pk=delivery.pk)

        if locked.status not in SEARCHING_STATUSES:
            return False, 'This delivery request is no longer available.'

        if not is_rider_eligible(rider):
            return False, 'You cannot accept deliveries while offline, busy, or already on an active delivery.'

        locked.rider = rider
        locked.payout = locked.order.delivery_fee or Decimal('0.00')
        locked.save(update_fields=['rider', 'payout'])
        record_status(locked, 'assigned', f'Assigned to {rider.get_full_name()}')

        rider.is_available = False
        rider.save(update_fields=['is_available'])

        order = locked.order
        order.rider = rider
        order.status = 'out_for_delivery'
        order.save(update_fields=['rider', 'status'])

        notify_user(
            order.user,
            'Rider assigned 🛵',
            f'{rider.get_full_name()} is heading to {order.restaurant_name} to pick up your order #{order.order_id}.',
            kind='delivery',
            order=order,
            delivery=locked,
            link='/tracking/',
        )
        notify_restaurant(
            order.restaurant,
            'Rider assigned',
            f'{rider.get_full_name()} ({rider.phone}) has accepted order #{order.order_id}.',
            kind='delivery',
            order=order,
            delivery=locked,
            link='/restaurant-admin/orders/',
        )

    delivery.refresh_from_db()
    return True, None


def decline_delivery(delivery, rider):
    """Rider turns down a delivery request. It disappears from their view."""
    if delivery is None or rider is None:
        return
    delivery.declined_by.add(rider)


# ── Status advancement ──────────────────────────────────────────────────────

def advance_delivery_status(delivery, rider, next_status):
    """Move a delivery forward through the rider lifecycle. Returns (ok, error)."""
    if delivery is None or rider is None:
        return False, 'Delivery not found.'

    delivery.refresh_from_db()

    if delivery.rider_id != rider.id:
        return False, 'You are not assigned to this delivery.'

    with transaction.atomic():
        locked = Delivery.objects.select_for_update().get(pk=delivery.pk)

        if locked.rider_id != rider.id:
            return False, 'You are not assigned to this delivery.'

        allowed = TRANSITIONS.get(locked.status, set())
        if next_status not in allowed:
            return False, f'Cannot move from "{locked.status_label}" to "{next_status}".'

        order = locked.order
        note = {
            'arrived_at_restaurant': f'Rider arrived at {order.restaurant_name}',
            'picked_up': 'Order picked up by rider',
            'on_the_way': 'Rider is on the way to the customer',
            'arrived': 'Rider has arrived at the delivery address',
        }.get(next_status, '')

        record_status(locked, next_status, note)

        if next_status == 'picked_up':
            generate_otp(locked)
            notify_user(
                order.user,
                'Order picked up 🛵',
                f'Your order #{order.order_id} has been picked up by {rider.get_full_name()}. Your delivery OTP is {locked.otp}.',
                kind='delivery',
                order=order,
                delivery=locked,
                link='/tracking/',
            )
            notify_restaurant(
                order.restaurant,
                'Order picked up',
                f'{rider.get_full_name()} picked up order #{order.order_id}.',
                kind='delivery',
                order=order,
                delivery=locked,
            )
        elif next_status == 'arrived_at_restaurant':
            notify_restaurant(
                order.restaurant,
                'Rider arrived',
                f'{rider.get_full_name()} is at your restaurant for order #{order.order_id}.',
                kind='delivery',
                order=order,
                delivery=locked,
            )
        elif next_status == 'on_the_way':
            notify_user(
                order.user,
                'Rider on the way 🛵',
                f'{rider.get_full_name()} is delivering your order #{order.order_id}.',
                kind='delivery',
                order=order,
                delivery=locked,
                link='/tracking/',
            )
        elif next_status == 'arrived':
            notify_user(
                order.user,
                'Rider has arrived 📍',
                f'{rider.get_full_name()} has arrived with your order #{order.order_id}. Please share your delivery OTP.',
                kind='delivery',
                order=order,
                delivery=locked,
                link='/tracking/',
            )

    return True, None


def generate_otp(delivery):
    delivery.otp = f"{random.randint(100000, 999999)}"
    delivery.otp_attempts = 0
    delivery.save(update_fields=['otp', 'otp_attempts'])


# ── Completion ──────────────────────────────────────────────────────────────

def force_complete_delivery(delivery):
    """Restaurant/admin fallback to mark a delivery complete without OTP."""
    if delivery is None:
        return
    with transaction.atomic():
        locked = Delivery.objects.select_for_update().get(pk=delivery.pk)
        if locked.status in FINAL_STATUSES:
            return
        rider = locked.rider
        record_status(locked, 'delivered', 'Marked delivered by the restaurant')
        order = locked.order
        order.status = 'delivered'
        order.save(update_fields=['status'])
        if rider:
            rider.is_available = True
            rider.save(update_fields=['is_available'])


def complete_delivery(delivery, rider, otp):
    """Verify the OTP and mark the delivery complete. Returns (ok, error)."""
    if delivery is None or rider is None:
        return False, 'Delivery not found.'

    delivery.refresh_from_db()

    if delivery.rider_id != rider.id:
        return False, 'You are not assigned to this delivery.'

    otp = (otp or '').strip()
    if not otp:
        return False, 'Please enter the customer delivery OTP.'

    with transaction.atomic():
        locked = Delivery.objects.select_for_update().get(pk=delivery.pk)

        if locked.rider_id != rider.id:
            return False, 'You are not assigned to this delivery.'

        if locked.status != 'arrived':
            return False, 'You must mark the delivery as arrived before completing it.'

        if not locked.otp:
            return False, 'No delivery OTP has been generated for this order yet.'

        if otp != locked.otp:
            locked.otp_attempts += 1
            locked.save(update_fields=['otp_attempts'])
            return False, 'Incorrect OTP. The customer should read the OTP from their tracking page.'

        record_status(locked, 'delivered', 'Delivery completed')

        locked.otp = ''
        locked.save(update_fields=['otp'])

        order = locked.order
        order.status = 'delivered'
        order.save(update_fields=['status'])

        rider.is_available = True
        rider.payments += locked.payout
        rider.save(update_fields=['is_available', 'payments'])

        notify_user(
            order.user,
            'Order delivered 🎉',
            f'Your order #{order.order_id} has been delivered by {rider.get_full_name()}. Enjoy! Rate your rider to let others know.',
            kind='delivery',
            order=order,
            delivery=locked,
            link='/tracking/',
        )
        notify_restaurant(
            order.restaurant,
            'Order delivered',
            f'Order #{order.order_id} was delivered by {rider.get_full_name()}.',
            kind='delivery',
            order=order,
            delivery=locked,
        )

    return True, None


# ── Cancellation ────────────────────────────────────────────────────────────

def cancel_delivery(delivery, reason=''):
    """Cancel a delivery (restaurant or admin) and free the rider."""
    if delivery is None:
        return

    with transaction.atomic():
        locked = Delivery.objects.select_for_update().get(pk=delivery.pk)

        if locked.status in FINAL_STATUSES:
            return

        rider = locked.rider
        record_status(locked, 'cancelled', reason or 'Delivery cancelled')

        order = locked.order
        order.status = 'cancelled'
        order.save(update_fields=['status'])

        if rider:
            rider.is_available = True
            rider.save(update_fields=['is_available'])

        notify_user(
            order.user,
            'Order cancelled',
            f'Your order #{order.order_id} has been cancelled.',
            kind='delivery',
            order=order,
            delivery=locked,
        )
        if order.restaurant:
            notify_restaurant(
                order.restaurant,
                'Delivery cancelled',
                f'The delivery for order #{order.order_id} was cancelled.',
                kind='delivery',
                order=order,
                delivery=locked,
            )
