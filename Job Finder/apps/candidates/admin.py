"""Candidates admin registrations."""
from django.contrib import admin
from .models import (
    SeekerProfile, SeekerResume, SeekerSkill, SeekerExperience,
    SeekerEducation, SeekerCertification, SeekerLanguage,
)


class SeekerSkillInline(admin.TabularInline):
    model = SeekerSkill
    extra = 0


class SeekerExperienceInline(admin.StackedInline):
    model = SeekerExperience
    extra = 0


class SeekerEducationInline(admin.StackedInline):
    model = SeekerEducation
    extra = 0


@admin.register(SeekerProfile)
class SeekerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "headline", "district", "profile_completeness", "open_to_work")
    list_filter = ("open_to_work", "recruiter_visibility", "district__province")
    search_fields = ("user__email", "user__full_name", "headline")
    readonly_fields = ("profile_completeness",)
    inlines = [SeekerSkillInline, SeekerExperienceInline, SeekerEducationInline]


@admin.register(SeekerResume)
class SeekerResumeAdmin(admin.ModelAdmin):
    list_display = ("seeker", "title", "is_primary", "uploaded_at")
    list_filter = ("is_primary",)


@admin.register(SeekerSkill)
class SeekerSkillAdmin(admin.ModelAdmin):
    list_display = ("seeker", "skill", "proficiency")


@admin.register(SeekerExperience)
class SeekerExperienceAdmin(admin.ModelAdmin):
    list_display = ("seeker", "company_name", "title", "start_date", "end_date", "is_current")
    list_filter = ("is_current",)


@admin.register(SeekerEducation)
class SeekerEducationAdmin(admin.ModelAdmin):
    list_display = ("seeker", "institution", "level", "field_of_study", "end_year")


@admin.register(SeekerCertification)
class SeekerCertificationAdmin(admin.ModelAdmin):
    list_display = ("seeker", "name", "issuing_org", "issue_date")


@admin.register(SeekerLanguage)
class SeekerLanguageAdmin(admin.ModelAdmin):
    list_display = ("seeker", "language", "proficiency")
