from django.contrib import admin
from .models import AbuseReport, AlumniVerification, EmployerVerification, SuspiciousOpportunityFlag, TrustScore


@admin.register(EmployerVerification)
class EmployerVerificationAdmin(admin.ModelAdmin):
    list_display = ["employer", "status", "trust_score", "verified_by", "verified_at"]
    list_filter = ["status"]


@admin.register(AlumniVerification)
class AlumniVerificationAdmin(admin.ModelAdmin):
    list_display = ["alumni", "status", "verified_by", "verified_at"]
    list_filter = ["status"]


@admin.register(SuspiciousOpportunityFlag)
class SuspiciousOpportunityFlagAdmin(admin.ModelAdmin):
    list_display = ["flagged_by", "content_type", "flag_type", "status"]
    list_filter = ["status", "flag_type", "content_type"]


@admin.register(AbuseReport)
class AbuseReportAdmin(admin.ModelAdmin):
    list_display = ["reported_by", "reported_user", "reason", "status"]
    list_filter = ["status", "reason"]


@admin.register(TrustScore)
class TrustScoreAdmin(admin.ModelAdmin):
    list_display = ["user", "score", "is_flagged", "is_suspended", "last_computed"]
    list_filter = ["is_flagged", "is_suspended"]
