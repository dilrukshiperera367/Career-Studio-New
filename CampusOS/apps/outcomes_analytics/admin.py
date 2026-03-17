from django.contrib import admin
from .models import AccreditationReport, AlumniDestination, CohortOutcome, EmployabilityTrendPoint, PlacementOutcome


@admin.register(PlacementOutcome)
class PlacementOutcomeAdmin(admin.ModelAdmin):
    list_display = ["student", "outcome_type", "employer_name", "ctc_annual_lkr", "is_verified"]
    list_filter = ["outcome_type", "is_verified", "academic_year"]
    search_fields = ["student__email", "employer_name"]
    raw_id_fields = ["student", "campus", "verified_by"]


@admin.register(CohortOutcome)
class CohortOutcomeAdmin(admin.ModelAdmin):
    list_display = ["campus", "academic_year", "program", "total_placed", "placement_rate_pct", "is_published"]
    list_filter = ["is_published", "academic_year"]


@admin.register(AccreditationReport)
class AccreditationReportAdmin(admin.ModelAdmin):
    list_display = ["campus", "report_type", "for_year", "is_finalized", "generated_at"]
    list_filter = ["report_type", "is_finalized"]


@admin.register(EmployabilityTrendPoint)
class EmployabilityTrendPointAdmin(admin.ModelAdmin):
    list_display = ["campus", "program", "as_of_date", "avg_readiness_score", "at_risk_count"]
    list_filter = ["campus"]
