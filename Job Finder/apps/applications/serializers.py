"""Applications serializers — apply, track, manage."""
from rest_framework import serializers
from .models import Application, ApplicationStatusHistory, ApplicationNote, InterviewSchedule, JobOffer
from apps.jobs.serializers import JobListSerializer


class ApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ["job", "resume", "cover_letter", "screening_answers"]

    def validate_job(self, job):
        if job.status != "active":
            raise serializers.ValidationError("This job is not accepting applications.")
        return job

    def validate(self, data):
        user = self.context["request"].user
        if Application.objects.filter(job=data["job"], applicant=user).exists():
            raise serializers.ValidationError("You have already applied to this job.")
        return data


class ApplicationSerializer(serializers.ModelSerializer):
    job_detail = JobListSerializer(source="job", read_only=True)

    class Meta:
        model = Application
        fields = [
            "id", "job", "job_detail", "applicant", "employer", "status",
            "resume", "cover_letter", "screening_answers",
            "match_score", "match_breakdown",
            "ats_application_id", "ats_stage",
            "submitted_at", "viewed_at", "shortlisted_at",
            "interviewed_at", "offered_at", "hired_at",
            "rejected_at", "withdrawn_at",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "applicant", "employer", "match_score", "match_breakdown",
            "ats_application_id", "ats_stage", "ats_synced_at",
            "submitted_at", "viewed_at", "shortlisted_at",
            "interviewed_at", "offered_at", "hired_at",
            "rejected_at", "withdrawn_at", "created_at", "updated_at",
        ]


class ApplicationEmployerSerializer(serializers.ModelSerializer):
    """Employer view with notes and rating."""
    applicant_name = serializers.SerializerMethodField()
    applicant_email = serializers.EmailField(source="applicant.email", read_only=True)

    class Meta:
        model = Application
        fields = [
            "id", "job", "applicant", "applicant_name", "applicant_email",
            "status", "resume", "cover_letter", "screening_answers",
            "match_score", "match_breakdown",
            "employer_notes", "employer_rating",
            "submitted_at", "viewed_at", "shortlisted_at",
            "interviewed_at", "offered_at", "hired_at",
            "rejected_at", "withdrawn_at",
        ]
        read_only_fields = ["id", "job", "applicant", "applicant_name", "applicant_email", "submitted_at"]

    def get_applicant_name(self, obj):
        profile = getattr(obj.applicant, "seeker_profile", None)
        if profile:
            return f"{profile.first_name} {profile.last_name}".strip()
        return obj.applicant.email


class ApplicationStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Application.Status.choices)
    notes = serializers.CharField(required=False, default="")


class ApplicationStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_email = serializers.EmailField(source="changed_by.email", read_only=True, default="")

    class Meta:
        model = ApplicationStatusHistory
        fields = ["id", "old_status", "new_status", "changed_by", "changed_by_email", "notes", "changed_at"]
        read_only_fields = fields


class ApplicationNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationNote
        fields = ["id", "note", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class InterviewScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewSchedule
        fields = [
            "id", "interview_type", "scheduled_at", "duration_minutes",
            "location", "notes", "is_confirmed", "outcome",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class JobOfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobOffer
        fields = [
            "id", "offered_salary", "start_date", "offer_letter_url",
            "additional_benefits", "offer_status", "declined_reason",
            "expires_at", "responded_at", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class OfferRespondSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["accept", "decline", "negotiate"])
    declined_reason = serializers.CharField(required=False, default="")


class ApplicationDraftSerializer(serializers.ModelSerializer):
    """Save a draft application before submitting."""
    class Meta:
        model = Application
        fields = ["job", "resume", "cover_letter", "screening_answers"]

    def validate_job(self, job):
        if job.status != "active":
            raise serializers.ValidationError("This job is not accepting applications.")
        return job

