"""Payments admin registrations."""
from django.contrib import admin
from .models import SubscriptionPlan, Subscription, Invoice


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "tier", "price_lkr", "billing_period", "is_active")
    list_filter = ("tier", "is_active", "billing_period")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("employer", "plan", "status", "current_period_start", "current_period_end")
    list_filter = ("status", "plan")
    search_fields = ("employer__company_name_en",)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("subscription", "amount", "status", "paid_at", "created_at")
    list_filter = ("status",)
