"""CampusOS — Billing admin."""

from django.contrib import admin
from .models import (
    CampusBillingEvent,
    CampusInvoice,
    CampusPlan,
    CampusServiceProduct,
    CampusSubscription,
    EmployabilityProgram,
    EmployabilityProgramEnrollment,
    EmployerCampusCampaign,
    PlacementDriveFeeConfig,
    StudentPremiumPlan,
)


@admin.register(CampusPlan)
class CampusPlanAdmin(admin.ModelAdmin):
    list_display = ["name", "price_monthly_lkr", "price_annual_lkr", "is_active"]
    list_filter = ["is_active"]


@admin.register(CampusSubscription)
class CampusSubscriptionAdmin(admin.ModelAdmin):
    list_display = ["campus", "plan", "status", "start_date", "end_date"]
    list_filter = ["status"]
    raw_id_fields = ["campus"]


@admin.register(StudentPremiumPlan)
class StudentPremiumPlanAdmin(admin.ModelAdmin):
    list_display = ["student", "plan_type", "status", "expires_at"]
    list_filter = ["plan_type", "status"]


@admin.register(EmployerCampusCampaign)
class EmployerCampusCampaignAdmin(admin.ModelAdmin):
    list_display = ["employer", "campaign_type", "campus", "status", "total_amount_lkr"]
    list_filter = ["campaign_type", "status"]


@admin.register(PlacementDriveFeeConfig)
class PlacementDriveFeeConfigAdmin(admin.ModelAdmin):
    list_display = ["campus", "drive_type", "fee_per_drive_lkr", "is_active"]
    list_filter = ["drive_type", "is_active"]


@admin.register(CampusInvoice)
class CampusInvoiceAdmin(admin.ModelAdmin):
    list_display = ["campus", "invoice_number", "amount_lkr", "status", "due_date"]
    list_filter = ["status"]


@admin.register(CampusBillingEvent)
class CampusBillingEventAdmin(admin.ModelAdmin):
    list_display = ["campus", "event_type", "amount_lkr", "created_at"]
    list_filter = ["event_type"]
