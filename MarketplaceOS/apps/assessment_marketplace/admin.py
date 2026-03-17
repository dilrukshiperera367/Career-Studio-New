from django.contrib import admin
from .models import (
    AssessmentVendor, AssessmentProduct, AssessmentRoleMap,
    AssessmentOrder, AssessmentDelivery, AssessmentResult,
)


@admin.register(AssessmentVendor)
class AssessmentVendorAdmin(admin.ModelAdmin):
    list_display = ["vendor_name", "status", "api_integration", "created_at"]
    list_filter = ["status", "api_integration"]
    search_fields = ["vendor_name"]


@admin.register(AssessmentProduct)
class AssessmentProductAdmin(admin.ModelAdmin):
    list_display = ["name", "vendor", "category", "delivery_format", "price_per_unit_lkr", "is_active", "is_featured"]
    list_filter = ["category", "delivery_format", "is_active", "is_featured"]
    search_fields = ["name", "vendor__vendor_name"]
    list_editable = ["is_active", "is_featured"]


@admin.register(AssessmentRoleMap)
class AssessmentRoleMapAdmin(admin.ModelAdmin):
    list_display = ["assessment", "job_role", "industry", "relevance_score"]
    search_fields = ["job_role", "assessment__name"]


@admin.register(AssessmentOrder)
class AssessmentOrderAdmin(admin.ModelAdmin):
    list_display = ["reference", "purchased_by", "assessment", "quantity", "total_price_lkr", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["reference", "purchased_by__email", "assessment__name"]
    readonly_fields = ["reference", "created_at"]


@admin.register(AssessmentDelivery)
class AssessmentDeliveryAdmin(admin.ModelAdmin):
    list_display = ["id", "candidate_email", "status", "is_fraud_flagged", "created_at"]
    list_filter = ["status", "is_fraud_flagged"]
    search_fields = ["candidate_email"]


@admin.register(AssessmentResult)
class AssessmentResultAdmin(admin.ModelAdmin):
    list_display = ["delivery", "normalized_score", "percentile", "band", "passed", "ingested_at"]
    list_filter = ["passed", "is_visible_to_candidate"]
