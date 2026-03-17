"""Foreign Employment admin registrations."""
from django.contrib import admin
from .models import ForeignEmploymentAgency, OverseasJob, PreDepartureChecklist


@admin.register(ForeignEmploymentAgency)
class ForeignEmploymentAgencyAdmin(admin.ModelAdmin):
    list_display = ("name", "license_number", "is_verified", "is_slbfe_registered")
    list_filter = ("is_verified", "is_slbfe_registered")
    search_fields = ("name", "license_number")


@admin.register(OverseasJob)
class OverseasJobAdmin(admin.ModelAdmin):
    list_display = ("title", "agency", "country", "status", "created_at")
    list_filter = ("status", "country")
    search_fields = ("title", "agency__name")


@admin.register(PreDepartureChecklist)
class PreDepartureChecklistAdmin(admin.ModelAdmin):
    list_display = ("title", "country", "is_mandatory", "sort_order")
    list_filter = ("is_mandatory", "country")
