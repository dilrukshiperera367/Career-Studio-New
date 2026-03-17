from django.contrib import admin
from .models import EmployerVerification, RecruiterVerification, FraudReport, TrustScore


@admin.register(EmployerVerification)
class EmployerVerificationAdmin(admin.ModelAdmin):
    list_display = ['employer', 'status', 'method', 'verified_at', 'created_at']
    list_filter = ['status', 'method']


@admin.register(RecruiterVerification)
class RecruiterVerificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'status', 'trust_score', 'verified_at']
    list_filter = ['status']


@admin.register(FraudReport)
class FraudReportAdmin(admin.ModelAdmin):
    list_display = ['report_type', 'entity_type', 'status', 'risk_score', 'created_at']
    list_filter = ['report_type', 'status']
    search_fields = ['description']


@admin.register(TrustScore)
class TrustScoreAdmin(admin.ModelAdmin):
    list_display = ['entity_type', 'entity_id', 'overall_score', 'last_computed']
    list_filter = ['entity_type']
