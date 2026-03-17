"""CampusOS — Alumni Mentors admin."""

from django.contrib import admin
from .models import AlumniProfile, AlumniJobShare, GroupMentoringCircle, MentorRequest, MentorSession


@admin.register(AlumniProfile)
class AlumniProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "graduation_year", "current_employer", "is_mentor", "is_verified", "mentor_rating"]
    list_filter = ["is_mentor", "is_verified", "current_industry"]
    search_fields = ["user__email", "user__first_name", "current_employer"]
    raw_id_fields = ["user", "campus"]


@admin.register(MentorRequest)
class MentorRequestAdmin(admin.ModelAdmin):
    list_display = ["student", "mentor", "status", "created_at"]
    list_filter = ["status"]
    raw_id_fields = ["student", "mentor"]


@admin.register(MentorSession)
class MentorSessionAdmin(admin.ModelAdmin):
    list_display = ["mentorship", "scheduled_at", "mode", "is_completed"]
    list_filter = ["mode", "is_completed"]


@admin.register(GroupMentoringCircle)
class GroupMentoringCircleAdmin(admin.ModelAdmin):
    list_display = ["title", "host", "campus", "scheduled_at", "max_participants", "is_completed"]
    list_filter = ["is_completed", "is_public"]


@admin.register(AlumniJobShare)
class AlumniJobShareAdmin(admin.ModelAdmin):
    list_display = ["title", "company", "opportunity_type", "shared_by", "is_active", "view_count"]
    list_filter = ["opportunity_type", "is_active"]
