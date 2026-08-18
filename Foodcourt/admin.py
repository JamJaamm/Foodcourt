from django.contrib import admin
from django import forms
from .models import Riders


class RidersAdminForm(forms.ModelForm):
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text='Raw password will be hashed on save. Leave blank when editing to keep the current password.',
        required=False,
    )

    class Meta:
        model = Riders
        exclude = ('password',)

    def save(self, commit=True):
        rider = super().save(commit=False)
        raw_password = self.cleaned_data.get('password')
        if raw_password:
            rider.set_password(raw_password)
        elif not rider.pk:
            rider.set_password('changeme123')
        if commit:
            rider.save()
        return rider


@admin.register(Riders)
class RidersAdmin(admin.ModelAdmin):
    form = RidersAdminForm
    list_display = ('username', 'email', 'phone', 'status', 'is_active', 'location', 'created_at')
    list_filter = ('status', 'is_active', 'vehicle_type', 'country')
    search_fields = ('username', 'email', 'phone', 'first_name', 'last_name', 'vehicle_plate', 'account_number', 'location')
    readonly_fields = ('created_at', 'updated_at', 'last_login')
