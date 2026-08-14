from django.contrib import admin, messages
from django.utils.html import format_html

from .models import Payment
from .services import PaystackError, verify_payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'transaction_reference', 'order_link', 'customer_email', 'amount_display',
        'status_badge', 'payment_method', 'paid_at', 'created_at',
    )
    list_filter = ('status', 'payment_method', 'currency', 'created_at')
    search_fields = (
        'transaction_reference', 'paystack_reference', 'order__order_id',
        'customer__email', 'customer__username',
    )
    readonly_fields = ('order', 'customer', 'created_at', 'updated_at', 'paid_at')
    ordering = ('-created_at',)
    list_per_page = 25
    actions = ('mark_refunded', 'mark_failed', 'verify_now')

    @admin.display(description='Order')
    def order_link(self, obj):
        return format_html('<a href="/admin/Foodcourt/order/{}/">{}</a>', obj.order_id, obj.order.order_id)

    @admin.display(description='Customer')
    def customer_email(self, obj):
        return obj.customer.email

    @admin.display(description='Amount')
    def amount_display(self, obj):
        return f"{obj.amount:.2f} {obj.currency}"

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {
            Payment.Status.PENDING: 'orange',
            Payment.Status.SUCCESSFUL: 'green',
            Payment.Status.FAILED: 'red',
            Payment.Status.CANCELLED: 'gray',
            Payment.Status.REFUNDED: 'purple',
        }
        color = colors.get(obj.status, 'gray')
        return format_html('<b style="color:{};">{}</b>', color, obj.get_status_display())

    @admin.action(description='Verify selected payments with Paystack')
    def verify_now(self, request, queryset):
        updated = 0
        for payment in queryset:
            try:
                verify_payment(payment)
                updated += 1
            except PaystackError:
                self.message_user(request, f"Could not verify {payment.transaction_reference}", level=messages.ERROR)
        self.message_user(request, f"{updated} payment(s) verified.")

    @admin.action(description='Mark selected as refunded')
    def mark_refunded(self, request, queryset):
        updated = queryset.filter(status=Payment.Status.SUCCESSFUL).update(status=Payment.Status.REFUNDED)
        self.message_user(request, f"{updated} payment(s) marked as refunded.")

    @admin.action(description='Mark selected as failed')
    def mark_failed(self, request, queryset):
        updated = queryset.exclude(status=Payment.Status.SUCCESSFUL).update(status=Payment.Status.FAILED)
        self.message_user(request, f"{updated} payment(s) marked as failed.")
