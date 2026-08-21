from decimal import Decimal, InvalidOperation

from django import template


register = template.Library()


@register.filter(is_safe=True)
def money(value):
    """Format a number as money with thousands separators, e.g. 6,000.00."""
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return value
    return f'{amount:,.2f}'


@register.filter(is_safe=True)
def compact(value):
    """Abbreviate large numbers: 1500 → 1.5k, 2300000 → 2.3m, 1000000000 → 1b."""
    try:
        num = float(value)
    except (TypeError, ValueError):
        return value
    sign = '-' if num < 0 else ''
    num = abs(num)
    if num >= 1_000_000_000:
        val = num / 1_000_000_000
        return f'{sign}{val:g}b'
    if num >= 1_000_000:
        val = num / 1_000_000
        return f'{sign}{val:g}m'
    if num >= 1_000:
        val = num / 1_000
        return f'{sign}{val:g}k'
    return f'{sign}{num:g}'
