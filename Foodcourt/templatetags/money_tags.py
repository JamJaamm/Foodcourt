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
