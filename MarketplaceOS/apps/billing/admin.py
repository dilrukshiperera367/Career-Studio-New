from django.contrib import admin
from .models import (
    ProviderPlan, ProviderSubscription, MarketplaceCommissionConfig,
    BookingCommission, CourseCommission, FeaturedListingProduct, FeaturedListingPurchase,
    EnterpriseBudget, EnterpriseBudgetTransaction, CoachingBundle,
)


@admin.register(ProviderPlan)
class ProviderPlanAdmin(admin.ModelAdmin):
    list_display = ["tier", "name", "price_monthly_lkr", "price_annual_lkr"]


@admin.register(ProviderSubscription)
class ProviderSubscriptionAdmin(admin.ModelAdmin):
    list_display = ["provider", "plan", "status", "billing_cycle", "current_period_end"]
    list_filter = ["status", "billing_cycle"]
    search_fields = ["provider__user__email"]


@admin.register(MarketplaceCommissionConfig)
class MarketplaceCommissionConfigAdmin(admin.ModelAdmin):
    list_display = ["category", "base_commission_percent", "is_active", "updated_at"]
    list_filter = ["is_active"]
    list_editable = ["is_active"]


@admin.register(BookingCommission)
class BookingCommissionAdmin(admin.ModelAdmin):
    list_display = ["booking", "provider", "gross_amount_lkr", "commission_amount_lkr",
                    "commission_percent", "status"]
    list_filter = ["status"]


@admin.register(CourseCommission)
class CourseCommissionAdmin(admin.ModelAdmin):
    list_display = ["provider", "gross_amount_lkr", "commission_amount_lkr", "status"]
    list_filter = ["status"]


@admin.register(FeaturedListingProduct)
class FeaturedListingProductAdmin(admin.ModelAdmin):
    list_display = ["name", "slot_type", "price_monthly_lkr", "max_slots", "is_active"]
    list_editable = ["is_active"]


@admin.register(FeaturedListingPurchase)
class FeaturedListingPurchaseAdmin(admin.ModelAdmin):
    list_display = ["provider", "product", "status", "start_date", "end_date"]
    list_filter = ["status"]


@admin.register(EnterpriseBudget)
class EnterpriseBudgetAdmin(admin.ModelAdmin):
    list_display = ["enterprise", "budget_name", "budget_type", "total_budget_lkr", "spent_lkr"]
    list_filter = ["budget_type"]


@admin.register(EnterpriseBudgetTransaction)
class EnterpriseBudgetTransactionAdmin(admin.ModelAdmin):
    list_display = ["budget", "transaction_type", "amount_lkr", "created_at"]
    list_filter = ["transaction_type"]


@admin.register(CoachingBundle)
class CoachingBundleAdmin(admin.ModelAdmin):
    list_display = ["name", "session_count", "price_lkr", "validity_days", "is_active"]
    list_editable = ["is_active"]
