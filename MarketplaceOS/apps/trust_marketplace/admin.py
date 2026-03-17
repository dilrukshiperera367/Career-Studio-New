from django.contrib import admin
from .models import ProviderReport, ProviderStrike, Dispute, RiskFlag, QualityScore, BackgroundCheckRecord


@admin.register(ProviderReport)
class ProviderReportAdmin(admin.ModelAdmin):
    list_display = ["provider", "reporter", "report_type", "status", "created_at"]
    list_filter = ["report_type", "status"]
    search_fields = ["provider__display_name", "reporter__email"]


@admin.register(ProviderStrike)
class ProviderStrikeAdmin(admin.ModelAdmin):
    list_display = ["provider", "strike_type", "severity", "is_active", "issued_at"]
    list_filter = ["strike_type", "severity", "is_active"]


@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = ["reference", "booking", "raised_by", "dispute_type", "status", "created_at"]
    list_filter = ["dispute_type", "status"]
    search_fields = ["reference", "raised_by__email"]


@admin.register(RiskFlag)
class RiskFlagAdmin(admin.ModelAdmin):
    list_display = ["user", "risk_type", "risk_score", "status", "detected_at"]
    list_filter = ["risk_type", "status"]


@admin.register(QualityScore)
class QualityScoreAdmin(admin.ModelAdmin):
    list_display = ["provider", "composite_score", "tier", "computed_at"]
    list_filter = ["tier"]


@admin.register(BackgroundCheckRecord)
class BackgroundCheckAdmin(admin.ModelAdmin):
    list_display = ["provider", "check_status", "vendor", "requested_at", "cleared_at"]
    list_filter = ["check_status"]
