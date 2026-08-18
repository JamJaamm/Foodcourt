"""
Reusable distance and delivery-fee calculation service.

Uses OSRM (Open Source Routing Machine) for road distance when available,
falls back to Haversine straight-line distance with a ×1.3 correction factor.

Designed to be called from: checkout, order creation, admin, API/AJAX.
"""
import math
import logging
import urllib.request
import urllib.parse
import json
from decimal import Decimal

logger = logging.getLogger(__name__)

HAVERSINE_TO_ROAD_FACTOR = Decimal('1.3')


def haversine_distance_km(lat1, lon1, lat2, lon2):
    """Calculate straight-line distance between two points in km."""
    R = 6371.0
    dlat = math.radians(float(lat2) - float(lat1))
    dlon = math.radians(float(lon2) - float(lon1))
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(float(lat1))) *
         math.cos(math.radians(float(lat2))) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_road_distance_km(lat1, lon1, lat2, lon2):
    """
    Try OSRM public demo server for road distance.
    Returns distance in km or None on failure.
    """
    coords = f"{float(lon1)},{float(lat1)};{float(lon2)},{float(lat2)}"
    url = f"http://router.project-osrm.org/route/v1/driving/{coords}?overview=false"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'FoodCourt/1.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            if data.get('code') == 'Ok' and data.get('routes'):
                return Decimal(str(data['routes'][0]['distance'])) / Decimal('1000')
    except Exception as e:
        logger.warning("OSRM lookup failed: %s", e)
    return None


def calculate_distance_km(restaurant_lat, restaurant_lon, customer_lat, customer_lon):
    """
    Calculate delivery distance between restaurant and customer.
    Returns (distance_km, method_used).
    """
    road_km = get_road_distance_km(restaurant_lat, restaurant_lon, customer_lat, customer_lon)
    if road_km is not None:
        return road_km, 'road'

    haversine_km = Decimal(str(haversine_distance_km(
        restaurant_lat, restaurant_lon, customer_lat, customer_lon
    )))
    corrected = (haversine_km * HAVERSINE_TO_ROAD_FACTOR).quantize(Decimal('0.1'))
    return corrected, 'estimated'


def calculate_delivery_fee(restaurant_lat, restaurant_lon, customer_lat, customer_lon):
    """
    Main entry point. Returns a dict with:
      - distance_km: Decimal
      - distance_method: str ('road' or 'estimated')
      - delivery_fee: Decimal
      - error: str or None
      - outside_range: bool
    """
    from .models import DeliverySettings

    settings = DeliverySettings.get_active()

    # Validate inputs
    coords = [restaurant_lat, restaurant_lon, customer_lat, customer_lon]
    if any(c is None for c in coords):
        return {
            'distance_km': None,
            'distance_method': None,
            'delivery_fee': None,
            'error': 'Location data unavailable for this delivery.',
            'outside_range': False,
        }

    distance_km, method = calculate_distance_km(
        restaurant_lat, restaurant_lon, customer_lat, customer_lon
    )

    # Check max distance
    if distance_km > settings.max_distance_km:
        return {
            'distance_km': distance_km,
            'distance_method': method,
            'delivery_fee': None,
            'error': 'This restaurant is outside your delivery area.',
            'outside_range': True,
        }

    # Determine base fee from tiers
    if distance_km <= Decimal('2'):
        fee = settings.tier_0_2
    elif distance_km <= Decimal('5'):
        fee = settings.tier_2_5
    elif distance_km <= Decimal('8'):
        fee = settings.tier_5_8
    elif distance_km <= Decimal('12'):
        fee = settings.tier_8_12
    else:
        fee = settings.tier_12_15

    # Apply surge if enabled
    if settings.surge_enabled and settings.surge_multiplier > 1:
        fee = (fee * settings.surge_multiplier).quantize(Decimal('0.01'))

    return {
        'distance_km': distance_km,
        'distance_method': method,
        'delivery_fee': fee,
        'error': None,
        'outside_range': False,
    }


def recalculate_order_total(order, discount=None):
    """
    Recalculate order total server-side using the verified delivery fee.
    Returns (delivery_fee, distance_km, total, error).
    """
    subtotal = order.subtotal

    if order.restaurant and order.restaurant.has_coordinates:
        # Try to find matching address
        address = _find_matching_address(order)
        if address and address.has_coordinates:
            result = calculate_delivery_fee(
                order.restaurant.latitude, order.restaurant.longitude,
                address.latitude, address.longitude,
            )
            if result['error']:
                return None, None, None, result['error']
            delivery_fee = result['delivery_fee']
            distance_km = result['distance_km']
        else:
            delivery_fee = order.delivery_fee
            distance_km = order.delivery_distance_km
    else:
        delivery_fee = order.delivery_fee
        distance_km = order.delivery_distance_km

    disc = discount if discount is not None else order.discount
    total = subtotal + delivery_fee - disc
    if total < 0:
        total = Decimal('0')

    return delivery_fee, distance_km, total, None


def _find_matching_address(order):
    """Try to find the Address object matching this order's delivery_address text."""
    from .models import Address
    return Address.objects.filter(
        user=order.user,
        street__icontains=order.delivery_address[:50]
    ).first()
