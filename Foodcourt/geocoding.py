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


def _nominatim_query(query):
    """Send a single query to Nominatim. Returns (lat, lon) or (None, None)."""
    global _last_request_time

    if not query or not query.strip():
        return None, None

    elapsed = time.time() - _last_request_time
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)

    params = urllib.parse.urlencode({
        'q': query.strip(),
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
        logger.warning("Geocoding failed for '%s': %s", query[:80], e)

    return None, None


def geocode_address(address_string):
    """
    Convert a text address to (latitude, longitude).
    Returns (lat: float, lon: float) on success, (None, None) on failure.
    """
    return _nominatim_query(address_string)


def geocode_restaurant(street='', area='', city='', state='', country='Nigeria', fallback_address=''):
    """
    Geocode a restaurant address with multiple fallback strategies.
    Tries increasingly simpler queries to maximise success rate.
    Returns (lat, lon) or (None, None).
    """
    strategies = []

    full = build_geocoding_query(street=street, area=area, city=city, state=state, country=country)
    if full.strip():
        strategies.append(full)

    simplified = build_geocoding_query(street='', area='', city=city, state=state, country=country)
    if simplified.strip() and simplified != full:
        strategies.append(simplified)

    state_country = build_geocoding_query(street='', area='', city='', state=state, country=country)
    if state_country.strip() and state_country not in strategies:
        strategies.append(state_country)

    if fallback_address and fallback_address.strip() and fallback_address not in strategies:
        strategies.append(fallback_address.strip())

    for query in strategies:
        lat, lon = _nominatim_query(query)
        if lat is not None and lon is not None:
            logger.info("Geocoded '%s' → %s, %s", query[:60], lat, lon)
            return lat, lon

    logger.warning("All geocoding strategies failed for state=%s, city=%s", state, city)
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
