from django.contrib import admin
from apps.scoring.models import (
    JobScoreBatch, BatchItem, BatchItemScore,
    CandidateProfile, CandidateResumeVersion, CandidateScoreRun,
    ScorecardTemplate, Scorecard,
)

admin.site.register(JobScoreBatch)
admin.site.register(BatchItem)
admin.site.register(BatchItemScore)
admin.site.register(CandidateProfile)
admin.site.register(CandidateResumeVersion)
admin.site.register(CandidateScoreRun)


@admin.register(ScorecardTemplate)
class ScorecardTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "tenant", "created_by", "created_at"]
    list_filter = ["tenant"]
    search_fields = ["name"]
    ordering = ["-created_at"]


@admin.register(Scorecard)
class ScorecardAdmin(admin.ModelAdmin):
    list_display = [
        "id", "application", "interviewer", "overall_score",
        "recommendation", "interview_date", "created_at",
    ]
    list_filter = ["recommendation"]
    search_fields = ["interviewer__email", "notes"]
    ordering = ["-created_at"]
    readonly_fields = ["id", "created_at", "updated_at"]
