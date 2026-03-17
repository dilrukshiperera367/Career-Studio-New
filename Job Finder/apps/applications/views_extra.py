"""
Feature 5 — Application Experience & Conversion OS
Additional views: quick apply, autofill, seeker analytics, application dashboard,
external tracker, batch apply, follow-up nudge management, withdrawal reasons,
reapply eligibility, application task checklist, employer response-rate.
"""
import json
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Avg, Q
from rest_framework import permissions, status, parsers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import (
    ListCreateAPIView, RetrieveUpdateDestroyAPIView, ListAPIView,
)

from apps.shared.permissions import IsSeeker
from apps.candidates.views import get_or_create_profile
from apps.candidates.models import SeekerProfile, SeekerResume

from .models import (
    Application, InterviewSchedule, BatchApplySession,
    ExternalApplicationTracker, ApplicationTask, FollowUpNudge, WithdrawalReason,
)


def _seeker_app_qs(request):
    return Application.objects.filter(applicant=request.user).select_related("job", "employer")


# ── Quick Apply ───────────────────────────────────────────────────────────────

class QuickApplyView(APIView):
    """
    POST /applications/quick-apply/
    Submit a one-click application using the seeker's stored primary resume
    and ApplicationProfile data.
    """
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def post(self, request):
        from apps.jobs.models import JobListing
        job_id = request.data.get("job_id")
        if not job_id:
            return Response({"detail": "job_id required."}, status=400)

        try:
            job = JobListing.objects.get(pk=job_id, status="active")
        except JobListing.DoesNotExist:
            return Response({"detail": "Job not found or inactive."}, status=404)

        # Prevent duplicate
        if Application.objects.filter(job=job, applicant=request.user).exists():
            return Response({"detail": "Already applied to this job."}, status=409)

        seeker = get_or_create_profile(request.user)
        resume = seeker.resumes.filter(is_primary=True).first()

        # Prefill cover letter from ApplicationProfile if it exists
        cover_letter = ""
        try:
            ap = seeker.application_profile
            cover_letter = ap.cover_letter_template.replace(
                "{{job_title}}", job.title
            ).replace("{{company_name}}", job.employer.company_name if hasattr(job, "employer") else "")
        except Exception:
            pass

        app = Application.objects.create(
            job=job,
            applicant=request.user,
            employer=job.employer,
            resume=resume,
            cover_letter=cover_letter,
            apply_method_used="quick_apply",
            autofill_used=True,
            status=Application.Status.SUBMITTED,
            completion_percentage=100,
        )

        # Auto-create post-apply tasks
        default_tasks = [
            "Research the company on JobFinder",
            "Connect on LinkedIn with the recruiter",
            "Prepare key talking points about your experience",
        ]
        for i, t in enumerate(default_tasks):
            ApplicationTask.objects.create(application=app, title=t, sort_order=i)

        # Schedule a follow-up nudge in 5 days
        FollowUpNudge.objects.create(
            application=app,
            nudge_type="no_response",
            scheduled_for=timezone.now() + timedelta(days=5),
        )

        return Response({
            "application_id": str(app.id),
            "status": app.status,
            "apply_method": app.apply_method_used,
            "message": "Quick application submitted successfully!",
        }, status=201)


# ── Seeker Application Dashboard / Analytics ──────────────────────────────────

class SeekerApplicationAnalyticsView(APIView):
    """
    GET /applications/analytics/
    Returns a seeker's application funnel, response rates, weekly stats.
    """
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get(self, request):
        apps = Application.objects.filter(applicant=request.user)
        total = apps.count()

        # Status breakdown
        status_counts = dict(apps.values_list("status").annotate(c=Count("id")).values_list("status", "c"))

        # Weekly applies
        now = timezone.now()
        this_week = apps.filter(submitted_at__gte=now - timedelta(days=7)).count()
        last_week = apps.filter(
            submitted_at__gte=now - timedelta(days=14),
            submitted_at__lt=now - timedelta(days=7),
        ).count()

        # Response rate: apps that moved past "submitted" or "viewed"
        responded = apps.filter(status__in=["shortlisted", "interview", "assessment", "offer", "hired"]).count()
        response_rate = round((responded / total * 100), 1) if total else 0

        # Avg days to first response
        avg_days = None
        viewed = apps.filter(viewed_at__isnull=False)
        if viewed.exists():
            diffs = [(a.viewed_at - a.submitted_at).days for a in viewed if a.viewed_at]
            avg_days = round(sum(diffs) / len(diffs), 1) if diffs else None

        # Apply method breakdown
        method_counts = dict(apps.values_list("apply_method_used").annotate(c=Count("id")).values_list("apply_method_used", "c"))

        # Pending drafts
        drafts = apps.filter(is_draft=True).count()

        return Response({
            "total_applications": total,
            "status_breakdown": status_counts,
            "this_week": this_week,
            "last_week": last_week,
            "weekly_change": this_week - last_week,
            "response_rate_pct": response_rate,
            "avg_days_to_first_response": avg_days,
            "apply_method_breakdown": method_counts,
            "pending_drafts": drafts,
            "interviews_scheduled": status_counts.get("interview", 0),
            "offers_received": status_counts.get("offer", 0),
        })


# ── Application Task Checklist ────────────────────────────────────────────────

class ApplicationTaskListCreateView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get_queryset(self):
        app_id = self.kwargs["app_id"]
        return ApplicationTask.objects.filter(
            application__applicant=self.request.user,
            application_id=app_id,
        )

    def perform_create(self, serializer):
        app_id = self.kwargs["app_id"]
        app = Application.objects.get(pk=app_id, applicant=self.request.user)
        serializer.save(application=app)

    def get_serializer_class(self):
        from rest_framework import serializers as s
        class TaskSerializer(s.ModelSerializer):
            class Meta:
                model = ApplicationTask
                fields = ["id", "title", "description", "due_date", "is_done", "sort_order", "created_at"]
        return TaskSerializer


class ApplicationTaskDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get_queryset(self):
        return ApplicationTask.objects.filter(application__applicant=self.request.user)

    def get_serializer_class(self):
        from rest_framework import serializers as s
        class TaskSerializer(s.ModelSerializer):
            class Meta:
                model = ApplicationTask
                fields = ["id", "title", "description", "due_date", "is_done", "sort_order", "created_at"]
        return TaskSerializer

    lookup_field = "id"


# ── Withdrawal Reason ─────────────────────────────────────────────────────────

class WithdrawalReasonView(APIView):
    """POST /applications/my/<uuid>/withdrawal-reason/"""
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def post(self, request, pk):
        try:
            app = Application.objects.get(pk=pk, applicant=request.user)
        except Application.DoesNotExist:
            return Response(status=404)

        reason_code = request.data.get("reason_code", "other")
        notes = request.data.get("notes", "")
        WithdrawalReason.objects.update_or_create(
            application=app,
            defaults={"reason_code": reason_code, "notes": notes},
        )
        return Response({"detail": "Withdrawal reason recorded."})


# ── Reapply Eligibility ───────────────────────────────────────────────────────

class ReapplyEligibilityView(APIView):
    """GET /applications/reapply/<uuid:job_id>/eligibility/"""
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get(self, request, job_id):
        existing = Application.objects.filter(job_id=job_id, applicant=request.user).first()
        if not existing:
            return Response({"eligible": True, "reason": "No prior application."})

        if existing.status == "withdrawn":
            # Allow reapply after 30 days
            days_since = (timezone.now() - existing.submitted_at).days
            eligible = days_since >= 30
            return Response({
                "eligible": eligible,
                "reason": f"Withdrawn {days_since} days ago. Minimum 30 days required." if not eligible else "Eligible to reapply.",
                "previous_status": existing.status,
                "days_since_applied": days_since,
            })

        if existing.status in ["rejected"]:
            days_since = (timezone.now() - existing.submitted_at).days
            eligible = days_since >= 60
            return Response({
                "eligible": eligible,
                "reason": f"Previously rejected {days_since} days ago. Minimum 60 days required." if not eligible else "Eligible to reapply after 60 days.",
                "previous_status": existing.status,
                "days_since_applied": days_since,
            })

        return Response({
            "eligible": False,
            "reason": "Active application already exists.",
            "previous_status": existing.status,
        })


# ── External Application Tracker ─────────────────────────────────────────────

class ExternalApplicationListCreateView(ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get_queryset(self):
        return ExternalApplicationTracker.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_serializer_class(self):
        from rest_framework import serializers as s
        class ExtAppSerializer(s.ModelSerializer):
            class Meta:
                model = ExternalApplicationTracker
                fields = "__all__"
                read_only_fields = ["user", "created_at", "updated_at"]
        return ExtAppSerializer


class ExternalApplicationDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get_queryset(self):
        return ExternalApplicationTracker.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        from rest_framework import serializers as s
        class ExtAppSerializer(s.ModelSerializer):
            class Meta:
                model = ExternalApplicationTracker
                fields = "__all__"
                read_only_fields = ["user", "created_at", "updated_at"]
        return ExtAppSerializer


# ── Batch Apply ───────────────────────────────────────────────────────────────

class BatchApplyView(APIView):
    """
    POST /applications/batch-apply/
    Apply to multiple jobs at once using stored profile.
    """
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def post(self, request):
        from apps.jobs.models import JobListing
        job_ids = request.data.get("job_ids", [])
        resume_id = request.data.get("resume_id")
        cover_letter = request.data.get("cover_letter", "")

        if not job_ids or len(job_ids) > 25:
            return Response({"detail": "Provide 1–25 job_ids."}, status=400)

        seeker = get_or_create_profile(request.user)
        resume = None
        if resume_id:
            resume = seeker.resumes.filter(pk=resume_id).first()
        if not resume:
            resume = seeker.resumes.filter(is_primary=True).first()

        session = BatchApplySession.objects.create(
            user=request.user,
            job_ids=job_ids,
            cover_letter_used=cover_letter,
            resume_id=resume.pk if resume else None,
        )

        applied, skipped, failed = [], [], []
        for jid in job_ids:
            try:
                job = JobListing.objects.get(pk=jid, status="active")
                if Application.objects.filter(job=job, applicant=request.user).exists():
                    skipped.append(str(jid))
                    continue
                Application.objects.create(
                    job=job, applicant=request.user, employer=job.employer,
                    resume=resume, cover_letter=cover_letter,
                    apply_method_used="quick_apply", autofill_used=True,
                    status=Application.Status.SUBMITTED,
                )
                applied.append(str(jid))
            except Exception:
                failed.append(str(jid))

        session.applied_count = len(applied)
        session.skipped_count = len(skipped)
        session.failed_count = len(failed)
        session.completed_at = timezone.now()
        session.save()

        return Response({
            "session_id": str(session.id),
            "applied": applied,
            "skipped": skipped,
            "failed": failed,
            "summary": f"Applied to {len(applied)} jobs, {len(skipped)} skipped, {len(failed)} failed.",
        }, status=201)


# ── Follow-up Nudges ──────────────────────────────────────────────────────────

class NudgeListView(ListAPIView):
    """GET /applications/nudges/ — pending nudges for the current user."""
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get(self, request):
        nudges = FollowUpNudge.objects.filter(
            application__applicant=request.user,
            is_dismissed=False,
            scheduled_for__lte=timezone.now(),
        ).select_related("application__job").order_by("scheduled_for")[:20]

        return Response([{
            "id": str(n.id),
            "nudge_type": n.nudge_type,
            "label": n.get_nudge_type_display(),
            "application_id": str(n.application_id),
            "job_title": n.application.job.title if n.application.job else "",
            "scheduled_for": n.scheduled_for,
        } for n in nudges])


class NudgeDismissView(APIView):
    """POST /applications/nudges/<uuid>/dismiss/"""
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def post(self, request, pk):
        try:
            nudge = FollowUpNudge.objects.get(pk=pk, application__applicant=request.user)
            nudge.is_dismissed = True
            nudge.save(update_fields=["is_dismissed"])
            return Response({"detail": "Nudge dismissed."})
        except FollowUpNudge.DoesNotExist:
            return Response(status=404)


# ── Employer Response-Rate View ────────────────────────────────────────────────

class EmployerResponseRateView(APIView):
    """
    GET /applications/employer-response-rate/<uuid:employer_id>/
    Shows the employer's historical response rate to seekers.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, employer_id):
        total = Application.objects.filter(employer_id=employer_id, status="submitted").count()
        total_all = Application.objects.filter(employer_id=employer_id).count()
        responded = Application.objects.filter(
            employer_id=employer_id,
            status__in=["viewed", "shortlisted", "interview", "assessment", "offer", "hired", "rejected"],
        ).count()
        rate = round(responded / total_all * 100, 1) if total_all else 0

        # Avg response time
        viewed_apps = Application.objects.filter(employer_id=employer_id, viewed_at__isnull=False)
        avg_hours = None
        if viewed_apps.exists():
            diffs = [(a.viewed_at - a.submitted_at).total_seconds() / 3600
                     for a in viewed_apps if a.viewed_at and a.submitted_at]
            avg_hours = round(sum(diffs) / len(diffs), 1) if diffs else None

        return Response({
            "employer_id": str(employer_id),
            "total_applications_received": total_all,
            "response_rate_pct": rate,
            "avg_response_hours": avg_hours,
            "label": (
                "Very Responsive" if rate >= 80 else
                "Usually Responds" if rate >= 50 else
                "Slow to Respond" if rate >= 25 else
                "Rarely Responds"
            ),
        })
