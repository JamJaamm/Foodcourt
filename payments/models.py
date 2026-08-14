from django.conf import settings
from django.db import models


class Payment(models.Model):
    """A single payment attempt against an order.

    `transaction_reference` is our own unique reference generated before the
    user is sent to Paystack (used for idempotency). `paystack_reference` is
    the reference Paystack echoes back during redirect / webhook calls.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SUCCESSFUL = 'successful', 'Successful'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'
        REFUNDED = 'refunded', 'Refunded'

    class Method(models.TextChoices):
        PAYSTACK = 'paystack', 'Paystack'
        CASH = 'cash', 'Cash on Delivery'

    order = models.OneToOneField(
        'Foodcourt.Order',
        on_delete=models.CASCADE,
        related_name='payment',
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments',
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='NGN')
    payment_method = models.CharField(
        max_length=20, choices=Method.choices, default=Method.PAYSTACK
    )
    transaction_reference = models.CharField(max_length=100, unique=True)
    paystack_reference = models.CharField(max_length=100, blank=True, default='')
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    gateway_response = models.JSONField(default=dict, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_reference} ({self.status})"
