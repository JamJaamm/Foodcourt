"""Small, framework-agnostic helpers for the payments app.

Kept dependency-free so services.py / webhooks.py / views.py stay thin and
reusable outside Django request/response handling where possible.
"""
import logging
import uuid
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger('payments')


def generate_reference(prefix='FC'):
    """Build a unique, human-friendly transaction reference.

    Format: FC-20260804-<uuid-hex> — unique even for many payments a day.
    """
    stamp = datetime.now().strftime('%Y%m%d')
    tail = uuid.uuid4().hex[:10].upper()
    return f"{prefix}-{stamp}-{tail}"


def to_kobo(amount):
    """Convert a naira Decimal/float into an integer kobo value for Paystack."""
    amount = Decimal(str(amount))
    return int((amount * 100).to_integral_value(rounding=ROUND_HALF_UP))


def from_kobo(kobo):
    """Convert an integer kobo value back into a naira Decimal."""
    return Decimal(str(kobo)) / Decimal(100)


def log_payment(message, extra=None, level=logging.INFO):
    """Centralised payment logging so gateway activity is easy to trace."""
    if extra:
        logger.log(level, "%s | %s", message, extra)
    else:
        logger.log(level, message)
