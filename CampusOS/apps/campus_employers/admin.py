"""CampusOS — Campus Employers admin."""

from django.contrib import admin
from .models import CampusEmployer, RecruiterContact, EmployerEngagementLog, EmployerMOU, EmployerSatisfactionSurvey


@admin.register(CampusEmployer)
class CampusEmployerAdmin(admin.ModelAdmin):
    list_display = ["name", "campus", "partner_tier", "engagement_status", "is_verified", "total_hires"]
    list_filter = ["partner_tier", "engagement_status", "is_verified", "campus"]
    search_fields = ["name", "industry", "hq_city"]
    raw_id_fields = ["campus", "primary_contact"]


@admin.register(RecruiterContact)
class RecruiterContactAdmin(admin.ModelAdmin):
    list_display = ["full_name", "employer", "designation", "email", "is_primary"]
    list_filter = ["is_primary"]
    search_fields = ["full_name", "email", "employer__name"]


@admin.register(EmployerEngagementLog)
class EmployerEngagementLogAdmin(admin.ModelAdmin):
    list_display = ["employer", "activity_type", "logged_by", "activity_date"]
    list_filter = ["activity_type"]
    raw_id_fields = ["employer", "logged_by"]


@admin.register(EmployerMOU)
class EmployerMOUAdmin(admin.ModelAdmin):
    list_display = ["employer", "status", "signed_date", "valid_until", "annual_hire_commitment"]
    list_filter = ["status"]


@admin.register(EmployerSatisfactionSurvey)
class EmployerSatisfactionSurveyAdmin(admin.ModelAdmin):
    list_display = ["employer", "survey_year", "overall_satisfaction", "nps_score"]
    list_filter = ["survey_year"]
