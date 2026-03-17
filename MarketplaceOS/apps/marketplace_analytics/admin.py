from django.contrib import admin
from .models import (
    MarketplaceDailySnapshot, ProviderDailySnapshot,
    SearchEvent, BookingFunnelEvent, ProviderViewEvent, RevenueByCategory,
)


@admin.register(MarketplaceDailySnapshot)
class MarketplaceDailySnapshotAdmin(admin.ModelAdmin):
    list_display = ["date", "gross_merchandise_value_lkr", "total_bookings", "completed_bookings", "take_rate"]
    ordering = ["-date"]


@admin.register(ProviderDailySnapshot)
class ProviderDailySnapshotAdmin(admin.ModelAdmin):
    list_display = ["provider", "date", "bookings_received", "bookings_completed", "earnings_lkr", "avg_rating"]
    list_filter = ["date"]


@admin.register(SearchEvent)
class SearchEventAdmin(admin.ModelAdmin):
    list_display = ["query", "category", "result_count", "resulted_in_booking", "timestamp"]
    list_filter = ["resulted_in_booking"]
    search_fields = ["query"]


@admin.register(BookingFunnelEvent)
class BookingFunnelEventAdmin(admin.ModelAdmin):
    list_display = ["step", "session_id", "timestamp"]
    list_filter = ["step"]


@admin.register(ProviderViewEvent)
class ProviderViewEventAdmin(admin.ModelAdmin):
    list_display = ["provider", "source", "timestamp"]
    list_filter = ["source"]


@admin.register(RevenueByCategory)
class RevenueByCategoryAdmin(admin.ModelAdmin):
    list_display = ["date", "category", "booking_count", "gmv_lkr", "commission_lkr"]
    ordering = ["-date"]
