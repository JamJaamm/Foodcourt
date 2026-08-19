"""
Geocoding service for converting addresses to latitude/longitude.

Uses Nominatim (OpenStreetMap) — free, no API key required.
Rate limited to 1 request/second per policy.

Can be swapped out for Google Maps, Mapbox, etc. by changing geocode_address().
"""
import logging
import urllib.request
import urllib.parse
import json
import time

logger = logging.getLogger(__name__)

_last_request_time = 0


def geocode_address(address_string):
    """
    Convert a text address to (latitude, longitude).

    Returns:
        (lat: float, lon: float) on success
        (None, None) on failure
    """
    global _last_request_time

    if not address_string or not address_string.strip():
        return None, None

    # Rate limiting: 1 request per second
    elapsed = time.time() - _last_request_time
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)

    params = urllib.parse.urlencode({
        'q': address_string.strip(),
        'format': 'json',
        'limit': 1,
        'addressdetails': 1,
    })
    url = f"https://nominatim.openstreetmap.org/search?{params}"

    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'FoodCourt/1.0 (restaurant-registration)',
            'Accept': 'application/json',
        })
        with urllib.request.urlopen(req, timeout=8) as resp:
            _last_request_time = time.time()
            data = json.loads(resp.read().decode())
            if data and len(data) > 0:
                lat = float(data[0]['lat'])
                lon = float(data[0]['lon'])
                return lat, lon
    except Exception as e:
        logger.warning("Geocoding failed for '%s': %s", address_string[:80], e)

    return None, None


def build_geocoding_query(street='', area='', city='', state='', country='Nigeria'):
    """
    Build a structured address string from components for geocoding.
    Nominatim works best with a single combined string.
    """
    parts = []
    if street:
        parts.append(street)
    if area:
        parts.append(area)
    if city:
        parts.append(city)
    if state:
        parts.append(state)
    if country:
        parts.append(country)
    return ', '.join(parts)
