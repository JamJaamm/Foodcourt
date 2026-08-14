from django.contrib import admin
from .models import Riders


@admin.register(Riders)
class RidersAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'phone', 'status', 'is_active', 'location', 'created_at')
    list_filter = ('status', 'is_active', 'vehicle_type', 'country')
    search_fields = ('username', 'email', 'phone', 'first_name', 'last_name', 'vehicle_plate', 'account_number', 'location')
    readonly_fields = ('created_at', 'updated_at', 'last_login')
