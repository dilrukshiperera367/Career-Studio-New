"""
Feature 11 — Marketplace Trust, Fraud & Safety
Extra views: full employer/recruiter trust score, suspicious-job auto-detection,
duplicate job detection, bot-application detection, JD clone detection,
scam-warning banners, domain verification, recruiter badge checks,
report flow (job/employer/recruiter), moderation queue overview,
safe-document-sharing controls, masked contact info, reputation history.
"""
from django.db.models import Count, Q, Avg
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import StrikeRecord, SuspensionRecord, ScamAlert, PhishingMessageReport, IdentityProofRequest


SCAM_PHRASES = [
    "guaranteed income", "no experience needed", "earn from home", "earn $", "earn usd",
    "daily payment", "whatsapp only", "no interview required", "send cv via whatsapp",
    "registration fee", "upfront fee", "send money", "western union", "gift card",
    "crypto payment", "bitcoin", "task-based income", "part-time earn", "data entry earn",
    "copy paste job", "referral bonus unlimited", "100% work from home earn",
    "agent needed", "reseller needed urgently", "no experience earn",
]


# ── Trust Score Engine ────────────────────────────────────────────────────────

class EmployerTrustScoreView(APIView):
    """
    GET /trust-ops/trust-score/employer/<slug>/
    Composite trust score (0-100) for an employer.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        from apps.employers.models import EmployerAccount
        try:
            employer = EmployerAccount.objects.get(slug=slug)
        except EmployerAccount.DoesNotExist:
            return Response(status=404)

        from apps.jobs.models import JobListing
        from apps.reviews.models import CompanyReview
        from apps.moderation.models import Report

        score = 0
        components = []

        # 1. Employer verified
        is_verified = getattr(employer, 'is_verified', False) or getattr(employer, 'verification_status', '') == 'verified'
        if is_verified:
            score += 25
            components.append({"label": "Employer Verified", "points": 25, "passed": True})
        else:
            components.append({"label": "Employer Verified", "points": 0, "max": 25, "passed": False, "tip": "Complete employer verification to boost trust score"})

        # 2. Business domain matches email
        has_domain = bool(getattr(employer, 'website', ''))
        if has_domain:
            score += 10
            components.append({"label": "Company Website", "points": 10, "passed": True})
        else:
            components.append({"label": "Company Website", "points": 0, "max": 10, "passed": False})

        # 3. Active jobs with salary shown
        jobs_with_salary = JobListing.objects.filter(
            employer=employer, status="active", salary_min__isnull=False
        ).count()
        total_active = JobListing.objects.filter(employer=employer, status="active").count()
        salary_pct = (jobs_with_salary / total_active * 100) if total_active else 0
        sal_pts = min(15, int(salary_pct / 100 * 15))
        score += sal_pts
        components.append({"label": "Salary Transparency", "points": sal_pts, "max": 15,
                           "detail": f"{int(salary_pct)}% of jobs show salary", "passed": sal_pts >= 10})

        # 4. Review score
        review_avg = CompanyReview.objects.filter(
            employer=employer, status="approved"
        ).aggregate(avg=Avg("overall_rating"))["avg"] or 0
        review_pts = min(15, int(review_avg / 5 * 15))
        score += review_pts
        components.append({"label": "Review Rating", "points": review_pts, "max": 15,
                           "detail": f"{round(review_avg, 1)} / 5.0", "passed": review_avg >= 3.5})

        # 5. Active scam alerts (penalty)
        active_alerts = ScamAlert.objects.filter(employer=employer, is_resolved=False, is_public=True).count()
        alert_penalty = min(25, active_alerts * 10)
        score = max(0, score - alert_penalty)
        if active_alerts:
            components.append({"label": "Active Scam Alerts", "points": -alert_penalty, "detail": f"{active_alerts} unresolved alerts", "passed": False})

        # 6. Strike count (penalty)
        strikes = StrikeRecord.objects.filter(target_employer=employer, is_active=True).count()
        strike_penalty = min(20, strikes * 7)
        score = max(0, score - strike_penalty)
        if strikes:
            components.append({"label": "Policy Strikes", "points": -strike_penalty, "detail": f"{strikes} active strikes", "passed": False})

        # 7. Active suspension (hard cap)
        is_suspended = SuspensionRecord.objects.filter(target_employer=employer, is_active=True).exists()
        if is_suspended:
            score = min(score, 10)
            components.append({"label": "Account Suspended", "points": 0, "detail": "Score capped at 10 during suspension", "passed": False})

        # 8. Reports count
        report_count = Report.objects.filter(
            content_type="employer", content_id=employer.id
        ).exclude(status="dismissed").count()
        report_penalty = min(15, report_count * 3)
        score = max(0, score - report_penalty)

        score = max(0, min(100, score))

        return Response({
            "employer_slug": slug,
            "trust_score": score,
            "trust_label": (
                "Highly Trusted" if score >= 80
                else "Trusted" if score >= 60
                else "Moderate" if score >= 40
                else "Low Trust" if score >= 20
                else "Not Recommended"
            ),
            "trust_color": (
                "emerald" if score >= 80 else "blue" if score >= 60
                else "amber" if score >= 40 else "orange" if score >= 20 else "red"
            ),
            "badge": "verified_employer" if score >= 80 and is_verified else None,
            "is_suspended": is_suspended,
            "active_scam_alerts": active_alerts,
            "components": components,
        })


# ── Suspicious Job Auto-Detection ─────────────────────────────────────────────

class SuspiciousJobDetectionView(APIView):
    """
    POST /trust-ops/detect-suspicious-job/
    Auto-scan a job posting for scam signals and flag patterns.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        d = request.data
        title = (d.get("title") or "").lower()
        desc = (d.get("description") or "").lower()
        company = (d.get("company_name") or "").lower()
        salary_text = str(d.get("salary_max", 0) or 0)

        signals = []
        risk_score = 0

        # Phrase scanning
        for phrase in SCAM_PHRASES:
            if phrase in title or phrase in desc:
                signals.append({"type": "scam_phrase", "phrase": phrase, "severity": "high"})
                risk_score += 15

        # Very high salary with no requirements
        try:
            sal = float(salary_text)
            desc_len = len(desc)
            if sal > 500000 and desc_len < 100:
                signals.append({"type": "high_salary_thin_desc", "severity": "high"})
                risk_score += 20
        except ValueError:
            pass

        # Duplicate title check  
        from apps.jobs.models import JobListing
        similar = JobListing.objects.filter(
            title__iexact=d.get("title", ""),
            status="active",
        ).values("employer__company_name").annotate(count=Count("id")).filter(count__gt=2)
        if similar.exists():
            signals.append({"type": "potential_duplicate", "severity": "medium", "count": similar.first()["count"]})
            risk_score += 10

        # WhatsApp-only contact
        if "wa.me" in desc or "whatsapp" in desc and "@" not in desc:
            signals.append({"type": "whatsapp_only_contact", "severity": "high"})
            risk_score += 15

        # Missing key fields
        if not d.get("company_registration"):
            risk_score += 5
        if not d.get("salary_min") and not d.get("salary_max"):
            risk_score += 5
        if len(desc) < 100:
            signals.append({"type": "very_short_description", "severity": "low"})
            risk_score += 8

        risk_score = min(100, risk_score)
        risk_level = "critical" if risk_score >= 70 else "high" if risk_score >= 45 else "medium" if risk_score >= 25 else "low"
        requires_hold = risk_score >= 45

        # Auto-create scam alert if critical
        if risk_score >= 70:
            job_id = d.get("job_id")
            if job_id:
                ScamAlert.objects.get_or_create(
                    job_id=job_id,
                    defaults={
                        "alert_level": "high_risk",
                        "alert_message": f"Auto-detected scam signals: {', '.join(s['type'] for s in signals[:3])}",
                        "is_public": True,
                    }
                )

        return Response({
            "risk_score": risk_score,
            "risk_level": risk_level,
            "requires_hold": requires_hold,
            "auto_flagged": risk_score >= 70,
            "signals": signals,
            "recommendation": (
                "Block and escalate to moderation team" if risk_score >= 70
                else "Hold for manual review before publishing" if risk_score >= 45
                else "Flag for priority review" if risk_score >= 25
                else "Cleared — publishable"
            ),
        })


# ── Duplicate Job Detection ────────────────────────────────────────────────────

class DuplicateJobDetectionView(APIView):
    """
    POST /trust-ops/detect-duplicate-job/
    Check if a job listing is a near-duplicate of an existing one.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from apps.jobs.models import JobListing
        title = request.data.get("title", "").strip()
        employer_id = request.data.get("employer_id")

        if not title:
            return Response({"detail": "title required"}, status=400)

        # Exact title dupes
        exact_dupes = JobListing.objects.filter(
            title__iexact=title, status="active"
        ).exclude(
            *([Q(employer_id=employer_id)] if employer_id else [])
        )

        # Partial title dupes (same employer)
        fuzzy_dupes = []
        if employer_id:
            words = [w for w in title.split() if len(w) > 3]
            if words:
                q = Q()
                for w in words[:3]:
                    q &= Q(title__icontains=w)
                fuzzy_dupes = list(
                    JobListing.objects.filter(
                        q, employer_id=employer_id, status="active"
                    ).exclude(title__iexact=title)
                    .values("id", "title", "created_at")[:5]
                )

        return Response({
            "is_duplicate": exact_dupes.count() > 0,
            "exact_duplicate_count": exact_dupes.count(),
            "exact_duplicates": list(exact_dupes.values("id", "title", "employer__company_name", "created_at")[:5]),
            "fuzzy_duplicates": fuzzy_dupes,
            "recommendation": (
                "Block — likely stolen JD or mass duplication" if exact_dupes.count() >= 5
                else "Review — multiple similar jobs found" if exact_dupes.count() > 0
                else "Cleared"
            ),
        })


# ── Bot Application Detection ──────────────────────────────────────────────────

class BotApplicationDetectionView(APIView):
    """
    POST /trust-ops/detect-bot-application/
    Signals that suggest a bot / bulk-apply farm submitted an application.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from apps.applications.models import Application
        user_id = request.data.get("user_id")
        application_id = request.data.get("application_id")

        if not user_id:
            return Response({"detail": "user_id required"}, status=400)

        signals = []
        risk = 0

        # Rapid application velocity
        from django.utils.timezone import now, timedelta
        from datetime import timedelta as td
        recent_applies = Application.objects.filter(
            applicant_id=user_id,
            applied_at__gte=now() - td(hours=1)
        ).count()
        if recent_applies > 15:
            signals.append({"type": "high_velocity", "detail": f"{recent_applies} apps in last hour", "severity": "high"})
            risk += 30
        elif recent_applies > 7:
            signals.append({"type": "elevated_velocity", "detail": f"{recent_applies} apps in last hour", "severity": "medium"})
            risk += 15

        # Identical cover letters across multiple applications
        identical_cover = Application.objects.filter(
            applicant_id=user_id
        ).values("cover_letter").annotate(count=Count("id")).filter(count__gt=3)
        if identical_cover.exists():
            signals.append({"type": "identical_cover_letters", "severity": "high", "count": identical_cover.first()["count"]})
            risk += 25

        # Applications with zero time-on-page (instant application)
        if request.data.get("time_on_page_seconds", 60) < 10:
            signals.append({"type": "instant_application", "detail": f"< 10s on page", "severity": "medium"})
            risk += 20

        risk = min(100, risk)
        is_likely_bot = risk >= 50

        return Response({
            "user_id": user_id,
            "risk_score": risk,
            "is_likely_bot": is_likely_bot,
            "signals": signals,
            "action": "flag_and_hold" if is_likely_bot else "monitor",
        })


# ── Report Flow (Job / Employer / Recruiter) ──────────────────────────────────

class UnifiedReportView(APIView):
    """
    POST /trust-ops/report/
    Unified report endpoint — job, employer, or recruiter.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from apps.moderation.models import Report
        d = request.data
        content_type = d.get("content_type", "")  # job, employer, recruiter, message
        content_id = d.get("content_id", "")
        reason = d.get("reason", "other")
        description = d.get("description", "")
        evidence = d.get("evidence", [])

        if not content_type or not content_id:
            return Response({"detail": "content_type and content_id required."}, status=400)

        # Check for duplicate report by same user
        existing = Report.objects.filter(
            reporter=request.user,
            content_type=content_type,
            content_id=content_id,
        ).first()
        if existing:
            return Response({"detail": "You have already reported this content.", "report_id": str(existing.id)}, status=409)

        report = Report.objects.create(
            reporter=request.user,
            content_type=content_type,
            content_id=content_id,
            reason=reason,
            description=description,
            evidence=evidence,
        )

        # Auto-scan for scam keywords in description
        scam_keywords = ["payment", "fee", "crypto", "gift card", "western union"]
        auto_escalate = any(kw in description.lower() for kw in scam_keywords)

        if auto_escalate:
            report.status = "reviewing"
            report.save(update_fields=["status"])

        return Response({
            "report_id": str(report.id),
            "status": report.status,
            "auto_escalated": auto_escalate,
            "message": "Report submitted. Our trust & safety team will review it within 24 hours.",
        }, status=201)


class ReportStatusView(APIView):
    """GET /trust-ops/report/<uuid:report_id>/status/"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, report_id):
        from apps.moderation.models import Report
        try:
            report = Report.objects.get(pk=report_id, reporter=request.user)
        except Report.DoesNotExist:
            return Response(status=404)
        return Response({
            "id": str(report.id),
            "content_type": report.content_type,
            "reason": report.reason,
            "status": report.status,
            "resolution_notes": report.resolution_notes if report.status in ["resolved", "dismissed"] else None,
            "created_at": report.created_at,
            "resolved_at": report.resolved_at,
        })


# ── Scam Warning Banner ────────────────────────────────────────────────────────

class ScamWarningBannerView(APIView):
    """
    GET /trust-ops/scam-warning/job/<uuid:job_id>/
    Returns active scam alerts for a job listing to show as a warning banner.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, job_id):
        alerts = ScamAlert.objects.filter(
            job_id=job_id, is_public=True, is_resolved=False
        ).order_by("-alert_level")

        if not alerts.exists():
            return Response({"has_warning": False})

        alert = alerts.first()
        return Response({
            "has_warning": True,
            "alert_level": alert.alert_level,
            "alert_message": alert.alert_message,
            "safe_job_search_tips": [
                "Legitimate employers never ask for upfront payments.",
                "Be cautious of jobs that promise high pay for minimal work.",
                "Avoid sharing financial information via WhatsApp or personal email.",
                "Verify the company using its official website and company registry.",
                "Never pay a registration fee to apply for a job.",
            ],
        })


class EmployerScamWarningView(APIView):
    """GET /trust-ops/scam-warning/employer/<slug>/"""
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        from apps.employers.models import EmployerAccount
        employer = EmployerAccount.objects.filter(slug=slug).first()
        if not employer:
            return Response({"has_warning": False})

        alerts = ScamAlert.objects.filter(
            employer=employer, is_public=True, is_resolved=False
        )
        is_suspended = SuspensionRecord.objects.filter(
            target_employer=employer, is_active=True
        ).exists()

        if not alerts.exists() and not is_suspended:
            return Response({"has_warning": False})

        return Response({
            "has_warning": True,
            "is_suspended": is_suspended,
            "alert_count": alerts.count(),
            "highest_level": alerts.order_by("-alert_level").first().alert_level if alerts.exists() else None,
            "message": "This employer account is under suspension" if is_suspended else f"{alerts.count()} safety alert(s) associated with this employer",
        })


# ── Employer Verification Verification Submit ──────────────────────────────────

class EmployerVerificationSubmitView(APIView):
    """
    POST /trust-ops/employer-verify/submit/
    Submit business registration documents for verification.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from apps.employers.models import EmployerAccount
        employer = EmployerAccount.objects.filter(team_members__user=request.user).first()
        if not employer:
            return Response({"detail": "Employer account not found."}, status=403)

        d = request.data
        documents = d.get("documents", [])  # List of document URLs
        company_reg_number = d.get("company_reg_number", "")
        business_domain = d.get("business_domain", "")

        # Create identity proof request
        proof, created = IdentityProofRequest.objects.get_or_create(
            employer=employer,
            defaults={
                "user": request.user,
                "trigger_reason": "Employer verification request",
                "documents_submitted": documents,
            }
        )
        if not created:
            proof.documents_submitted = documents
            proof.status = "submitted"
            proof.save(update_fields=["documents_submitted", "status"])

        return Response({
            "proof_id": str(proof.id),
            "status": proof.status,
            "message": "Verification documents submitted. Review typically takes 2-3 business days.",
            "submitted_at": proof.created_at if created else timezone.now(),
        }, status=201 if created else 200)


# ── Trust Badge / Reputation History ──────────────────────────────────────────

class EmployerReputationHistoryView(APIView):
    """
    GET /trust-ops/reputation/<slug>/history/
    Public reputation timeline for an employer.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        from apps.employers.models import EmployerAccount
        employer = EmployerAccount.objects.filter(slug=slug).first()
        if not employer:
            return Response(status=404)

        # Scam alerts
        alerts = list(ScamAlert.objects.filter(employer=employer).order_by("-created_at")[:10].values(
            "alert_level", "alert_message", "is_public", "is_resolved", "created_at", "resolved_at"
        ))

        # Strikes
        strikes = list(StrikeRecord.objects.filter(target_employer=employer).order_by("-created_at")[:10].values(
            "reason", "strike_number", "is_active", "created_at", "expires_at"
        ))

        # Suspensions
        suspensions = list(SuspensionRecord.objects.filter(target_employer=employer).order_by("-created_at")[:5].values(
            "suspension_type", "reason", "is_active", "starts_at", "ends_at", "lifted_at"
        ))

        # Identity proof
        id_proof = IdentityProofRequest.objects.filter(employer=employer).order_by("-created_at").first()

        return Response({
            "employer_slug": slug,
            "identity_verification_status": id_proof.status if id_proof else "not_requested",
            "scam_alerts": alerts,
            "policy_strikes": strikes,
            "suspensions": suspensions,
            "total_reports": ScamAlert.objects.filter(employer=employer).count(),
        })


# ── Moderation Queue Overview (Admin/Moderator) ────────────────────────────────

class ModerationQueueOverviewView(APIView):
    """
    GET /trust-ops/moderation-queue/
    Summary of pending reports and actions for the moderation dashboard.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        from apps.moderation.models import Report, ModerationAction

        pending = Report.objects.filter(status="pending")
        reviewing = Report.objects.filter(status="reviewing")

        by_type = list(
            pending.values("content_type").annotate(count=Count("id")).order_by("-count")
        )
        by_reason = list(
            pending.values("reason").annotate(count=Count("id")).order_by("-count")
        )

        # High priority: scam + payment request
        high_priority = pending.filter(reason__in=["scam", "fake"])

        # Phishing reports pending
        phishing_pending = PhishingMessageReport.objects.filter(status="pending").count()

        return Response({
            "pending_reports": pending.count(),
            "reviewing_reports": reviewing.count(),
            "high_priority_reports": high_priority.count(),
            "phishing_reports_pending": phishing_pending,
            "by_content_type": by_type,
            "by_reason": by_reason,
            "recent_actions": list(
                ModerationAction.objects.order_by("-created_at")[:5].values(
                    "action", "target_type", "created_at"
                )
            ),
        })
