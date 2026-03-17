from django.contrib import admin
from .models import DigitalBadge, MicroCredential, MicroCredentialEnrollment, SkillEvidenceBundle, StudentBadgeAward, VerifiedCertification


@admin.register(DigitalBadge)
class DigitalBadgeAdmin(admin.ModelAdmin):
    list_display = ["name", "badge_type", "campus", "is_active"]
    list_filter = ["badge_type", "is_active"]
    search_fields = ["name"]


@admin.register(StudentBadgeAward)
class StudentBadgeAwardAdmin(admin.ModelAdmin):
    list_display = ["student", "badge", "awarded_at", "is_revoked"]
    list_filter = ["is_revoked"]
    raw_id_fields = ["student", "badge", "awarded_by"]


@admin.register(VerifiedCertification)
class VerifiedCertificationAdmin(admin.ModelAdmin):
    list_display = ["student", "name", "issuing_organization", "is_verified"]
    list_filter = ["is_verified"]
    search_fields = ["name", "issuing_organization", "student__email"]


@admin.register(MicroCredential)
class MicroCredentialAdmin(admin.ModelAdmin):
    list_display = ["title", "campus", "skill_domain", "duration_hours", "is_active"]
    list_filter = ["is_active"]


@admin.register(SkillEvidenceBundle)
class SkillEvidenceBundleAdmin(admin.ModelAdmin):
    list_display = ["student", "skill_name", "proficiency_level", "endorsements_count"]
