"""CampusOS — Placements admin."""

from django.contrib import admin
from .models import DriveEligibilityRule, DriveOffer, DriveSlot, PlacementDrive, PlacementSeason, StudentDriveRegistration


@admin.register(PlacementSeason)
class PlacementSeasonAdmin(admin.ModelAdmin):
    list_display = ["name", "campus", "status", "season_start", "season_end"]
    list_filter = ["campus", "status"]


class RegistrationInline(admin.TabularInline):
    model = StudentDriveRegistration
    extra = 0
    fields = ["student", "status", "is_eligible"]
    raw_id_fields = ["student"]


@admin.register(PlacementDrive)
class PlacementDriveAdmin(admin.ModelAdmin):
    list_display = [
        "company_name", "role_title", "campus", "drive_type",
        "status", "drive_date", "openings", "total_offers",
    ]
    list_filter = ["campus", "status", "drive_type", "is_dream_company"]
    search_fields = ["company_name", "role_title"]
    inlines = [RegistrationInline]


@admin.register(DriveOffer)
class DriveOfferAdmin(admin.ModelAdmin):
    list_display = ["student", "drive", "status", "ctc_lkr", "is_final_offer", "accepted_at"]
    list_filter = ["status", "is_final_offer"]
    raw_id_fields = ["student", "drive", "registration"]
