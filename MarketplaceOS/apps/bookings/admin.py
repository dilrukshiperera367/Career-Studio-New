from django.contrib import admin
from .models import Booking, BookingIntakeResponse, BookingReminder, RecurringPlan, WaitlistEntry


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ["reference", "buyer", "provider", "status", "start_time", "price_lkr", "created_at"]
    list_filter = ["status", "delivery_mode", "booking_mode"]
    search_fields = ["reference", "buyer__email", "provider__display_name"]
    readonly_fields = ["id", "reference", "created_at", "updated_at"]
    date_hierarchy = "created_at"


@admin.register(RecurringPlan)
class RecurringPlanAdmin(admin.ModelAdmin):
    list_display = ["buyer", "provider", "frequency", "status", "sessions_completed", "start_date"]
    list_filter = ["status", "frequency"]


@admin.register(WaitlistEntry)
class WaitlistAdmin(admin.ModelAdmin):
    list_display = ["buyer", "service", "provider", "notified", "created_at"]
    list_filter = ["notified"]
