from django.contrib import admin
from .models import (
    CoverLetter, LinkedInAnalysis, InterviewPrepSession,
    MentorProfile, MentorshipRequest, NetworkingDraft,
    BrandScore, CareerRoadmap,
)


@admin.register(CoverLetter)
class CoverLetterAdmin(admin.ModelAdmin):
    list_display = ["user", "job_title", "company", "tone", "created_at"]
    list_filter = ["tone"]


@admin.register(LinkedInAnalysis)
class LinkedInAnalysisAdmin(admin.ModelAdmin):
    list_display = ["user", "total_score", "created_at"]


@admin.register(InterviewPrepSession)
class InterviewPrepSessionAdmin(admin.ModelAdmin):
    list_display = ["user", "role", "total_score", "completed", "created_at"]
    list_filter = ["role", "completed"]


@admin.register(MentorProfile)
class MentorProfileAdmin(admin.ModelAdmin):
    list_display = ["name", "title", "industry", "is_available", "rating"]
    list_filter = ["is_available", "industry"]


@admin.register(MentorshipRequest)
class MentorshipRequestAdmin(admin.ModelAdmin):
    list_display = ["mentor", "seeker", "status", "created_at"]
    list_filter = ["status"]


@admin.register(NetworkingDraft)
class NetworkingDraftAdmin(admin.ModelAdmin):
    list_display = ["user", "template_type", "created_at"]


@admin.register(BrandScore)
class BrandScoreAdmin(admin.ModelAdmin):
    list_display = ["user", "total_score", "grade", "computed_at"]


@admin.register(CareerRoadmap)
class CareerRoadmapAdmin(admin.ModelAdmin):
    list_display = ["user", "title", "target_role", "created_at"]
