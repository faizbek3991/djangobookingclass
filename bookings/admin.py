from django.contrib import admin

from .models import Booking, PaymentSettings


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("user", "session", "status", "amount_due", "booked_at", "submitted_at", "paid_at")
    list_filter = ("status",)
    search_fields = ("user__username", "user__email", "session__course__title")


@admin.register(PaymentSettings)
class PaymentSettingsAdmin(admin.ModelAdmin):
    list_display = ("bank_name", "account_holder", "account_number")
