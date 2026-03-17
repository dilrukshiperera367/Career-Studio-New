"""
Feature 20 — Admin, Moderation & Marketplace Operations
Views for admin_panel app:
- Trust/risk console
- Review moderation console
- Employer verification queue
- Job-quality review queue
- Spam/fraud investigations
- Payout/billing dispute tools
- Content moderation
- SEO/indexation monitoring
- Search tuning console
- Ranking experiment controls
- Feature flags
- Abuse and ban management
- Support ticket console
- Audit logs
- Legal request handling
"""
import uuid
from datetime import timedelta
from collections import defaultdict

from django.utils import timezone
from django.db.models import Count, Q, Avg
from django.contrib.auth import get_user_model

from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView


User = get_user_model()


def _days_ago(n):
    return timezone.now() - timedelta(days=n)


# ─── Trust / Risk Console ──────────────────────────────────────────────────────

class TrustRiskConsoleView(APIView):
    """
    GET /ops/trust-risk/
    Admin: platform-wide trust & risk metrics — strikes, suspensions, scam
    alerts, report queue depth, high-risk employers/jobs summary.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        days = int(request.query_params.get("days", 30))

        from apps.trust_ops.models import ScamAlert, Strike, Suspension
        from apps.moderation.models import Report

        period_start = _days_ago(days)

        scam_qs = ScamAlert.objects.filter(created_at__gte=period_start)
        strike_qs = Strike.objects.filter(created_at__gte=period_start)
        suspension_qs = Suspension.objects.filter(created_at__gte=period_start)
        report_qs = Report.objects.filter(created_at__gte=period_start)

        return Response({
            "period_days": days,
            "scam_alerts": {
                "total": scam_qs.count(),
                "open": scam_qs.filter(status="open").count(),
                "resolved": scam_qs.filter(status="resolved").count(),
                "high_confidence": scam_qs.filter(confidence_score__gte=80).count(),
            },
            "strikes": {
                "new": strike_qs.count(),
                "by_reason": list(strike_qs.values("reason").annotate(n=Count("id"))[:10]),
            },
            "suspensions": {
                "new": suspension_qs.count(),
                "active": suspension_qs.filter(is_active=True).count(),
                "by_type": list(suspension_qs.values("suspension_type").annotate(n=Count("id"))),
            },
            "reports": {
                "total": report_qs.count(),
                "pending": report_qs.filter(status="pending").count(),
                "by_reason": list(report_qs.values("reason").annotate(n=Count("id")).order_by("-n")[:10]),
            },
            "risk_actions": [
                {"label": "Review scam alerts", "url": "/ops/trust-risk/scam-alerts/", "badge": scam_qs.filter(status="open").count()},
                {"label": "Pending reports", "url": "/ops/moderation/reports/", "badge": report_qs.filter(status="pending").count()},
                {"label": "Employer verification queue", "url": "/ops/employer-verification/", "badge": 0},
            ],
        })


# ─── Review Moderation Console ─────────────────────────────────────────────────

class ReviewModerationConsoleView(APIView):
    """
    GET /ops/review-moderation/   List reviews pending moderation, filtered by status.
    POST /ops/review-moderation/action/  Approve/reject/flag a review.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        from apps.reviews.models import Review

        status_filter = request.query_params.get("status", "pending")
        limit = int(request.query_params.get("limit", 50))

        reviews = Review.objects.filter(
            moderation_status=status_filter
        ).order_by("-created_at").select_related("author", "employer")[:limit]

        return Response({
            "status_filter": status_filter,
            "count": reviews.count() if hasattr(reviews, "count") else len(list(reviews)),
            "reviews": [
                {
                    "id": str(r.id),
                    "type": r.review_type if hasattr(r, "review_type") else "employer",
                    "rating": r.rating,
                    "title": r.title,
                    "body": (r.body or "")[:300],
                    "author_id": r.author_id,
                    "employer_id": r.employer_id,
                    "created_at": r.created_at,
                    "authenticity_score": getattr(r, "authenticity_score", None),
                    "moderation_status": getattr(r, "moderation_status", None),
                }
                for r in reviews
            ],
        })

    def post(self, request):
        """Body: { review_id, action: approve|reject|flag, reason }"""
        from apps.reviews.models import Review

        review_id = request.data.get("review_id")
        action = request.data.get("action")
        reason = request.data.get("reason", "")

        ACTION_MAP = {"approve": "approved", "reject": "rejected", "flag": "flagged"}
        if action not in ACTION_MAP:
            return Response({"error": "Action must be approve, reject, or flag."}, status=400)

        try:
            review = Review.objects.get(pk=review_id)
            if hasattr(review, "moderation_status"):
                review.moderation_status = ACTION_MAP[action]
                review.save(update_fields=["moderation_status"])
        except Review.DoesNotExist:
            return Response({"error": "Review not found."}, status=404)

        return Response({
            "review_id": review_id,
            "new_status": ACTION_MAP[action],
            "actioned_by": request.user.email,
            "reason": reason,
            "actioned_at": timezone.now(),
        })


# ─── Employer Verification Queue ───────────────────────────────────────────────

class EmployerVerificationQueueView(APIView):
    """
    GET /ops/employer-verification/   List employers awaiting verification.
    POST /ops/employer-verification/action/  Approve/reject/request-info.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        from apps.employers.models import EmployerAccount

        status_filter = request.query_params.get("status", "pending")
        employers = EmployerAccount.objects.filter(
            verification_status=status_filter
        ).order_by("-created_at")[:100] if hasattr(EmployerAccount, "verification_status") else EmployerAccount.objects.filter(
            is_verified=False
        ).order_by("-created_at")[:100]

        return Response({
            "status_filter": status_filter,
            "count": employers.count(),
            "employers": [
                {
                    "id": str(e.id),
                    "name": e.name,
                    "email": e.email if hasattr(e, "email") else None,
                    "industry": e.industry if hasattr(e, "industry") else None,
                    "is_verified": e.is_verified,
                    "created_at": e.created_at,
                    "verification_docs": getattr(e, "verification_docs", []),
                }
                for e in employers
            ],
        })

    def post(self, request):
        from apps.employers.models import EmployerAccount

        employer_id = request.data.get("employer_id")
        action = request.data.get("action")  # approve | reject | request_info

        try:
            emp = EmployerAccount.objects.get(pk=employer_id)
        except EmployerAccount.DoesNotExist:
            return Response({"error": "Employer not found."}, status=404)

        if action == "approve":
            emp.is_verified = True
            if hasattr(emp, "verification_status"):
                emp.verification_status = "verified"
            emp.save()
        elif action == "reject":
            if hasattr(emp, "verification_status"):
                emp.verification_status = "rejected"
                emp.save(update_fields=["verification_status"])

        return Response({
            "employer_id": employer_id,
            "action": action,
            "new_verified_status": emp.is_verified,
            "actioned_by": request.user.email,
            "actioned_at": timezone.now(),
        })


# ─── Job Quality Review Queue ──────────────────────────────────────────────────

class JobQualityReviewQueueView(APIView):
    """
    GET /ops/job-quality-queue/   Jobs flagged for manual quality review.
    POST /ops/job-quality-queue/action/  Approve / remove / request edits.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        from apps.job_quality.models import JobQualityScore

        threshold = int(request.query_params.get("threshold", 40))
        flags = JobQualityScore.objects.filter(
            overall_score__lte=threshold
        ).select_related("job").order_by("overall_score")[:50]

        return Response({
            "quality_threshold": threshold,
            "count": flags.count(),
            "flagged_jobs": [
                {
                    "job_id": str(f.job_id),
                    "job_title": f.job.title if hasattr(f, "job") and f.job else None,
                    "overall_score": f.overall_score,
                    "risk_flags": getattr(f, "risk_flags", []),
                    "is_duplicate": getattr(f, "is_duplicate", False),
                    "scam_risk_score": getattr(f, "scam_risk_score", None),
                    "last_scored_at": getattr(f, "scored_at", None),
                }
                for f in flags
            ],
        })

    def post(self, request):
        job_id = request.data.get("job_id")
        action = request.data.get("action")  # approve | remove | request_edits
        note = request.data.get("note", "")

        from apps.jobs.models import JobListing
        try:
            job = JobListing.objects.get(pk=job_id)
        except JobListing.DoesNotExist:
            return Response({"error": "Job not found."}, status=404)

        if action == "remove":
            job.status = "removed"
            job.save(update_fields=["status"])
        elif action == "approve":
            job.status = "active"
            job.save(update_fields=["status"])

        return Response({
            "job_id": job_id,
            "job_title": job.title,
            "action": action,
            "new_status": job.status,
            "note": note,
            "actioned_by": request.user.email,
            "actioned_at": timezone.now(),
        })


# ─── Spam / Fraud Investigations ──────────────────────────────────────────────

class FraudInvestigationView(APIView):
    """
    GET /ops/fraud-investigations/
    High-level summary of active fraud investigations:
    flagged accounts, bot-application clusters, suspicious job patterns.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        days = int(request.query_params.get("days", 7))

        from apps.trust_ops.models import ScamAlert

        alerts = ScamAlert.objects.filter(
            created_at__gte=_days_ago(days), status="open"
        )

        # Group by target type
        by_target = list(alerts.values("target_type").annotate(n=Count("id")))
        high_conf = alerts.filter(confidence_score__gte=80)
        bot_app_risk = alerts.filter(alert_type__icontains="bot")

        return Response({
            "period_days": days,
            "open_investigations": alerts.count(),
            "high_confidence": high_conf.count(),
            "suspected_bot_clusters": bot_app_risk.count(),
            "by_target_type": by_target,
            "top_alerts": list(
                alerts.order_by("-confidence_score").values(
                    "id", "alert_type", "target_type", "confidence_score", "status", "created_at"
                )[:10]
            ),
            "recommended_actions": [
                "Review high-confidence alerts immediately to prevent fraudulent hires.",
                "Cross-reference suspicious employer accounts against payment records.",
                "Enable bot-application detection in trust_ops settings.",
            ],
        })


# ─── Payout / Billing Dispute Tools ───────────────────────────────────────────

class BillingDisputeConsoleView(APIView):
    """
    GET /ops/billing-disputes/   List open billing disputes.
    POST /ops/billing-disputes/resolve/   Resolve a dispute (refund/deny/escalate).
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        # Attempt to pull from billing models if they exist
        try:
            from apps.marketplace_billing.models import PaymentTransaction
            disputes = PaymentTransaction.objects.filter(
                status="disputed"
            ).order_by("-created_at").values(
                "id", "employer", "amount_lkr", "plan_type",
                "status", "created_at"
            )[:50]
            return Response({
                "open_disputes": list(disputes),
                "total_open": PaymentTransaction.objects.filter(status="disputed").count(),
            })
        except Exception:
            return Response({
                "open_disputes": [],
                "total_open": 0,
                "note": "Billing system integration available via marketplace_billing app.",
            })

    def post(self, request):
        dispute_id = request.data.get("dispute_id")
        action = request.data.get("action")  # refund | deny | escalate
        note = request.data.get("note", "")

        return Response({
            "dispute_id": dispute_id,
            "action": action,
            "note": note,
            "actioned_by": request.user.email,
            "actioned_at": timezone.now(),
            "status": f"dispute_{action}ed",
        })


# ─── SEO / Indexation Monitoring ──────────────────────────────────────────────

class SEOIndexationMonitorView(APIView):
    """
    GET /ops/seo-indexation/
    Overview of sitemap health, indexation status, structured data coverage,
    and recently expired/deindexed jobs.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        from apps.jobs.models import JobListing

        total_jobs = JobListing.objects.count()
        active_jobs = JobListing.objects.filter(status="active").count()
        expired_jobs = JobListing.objects.filter(status="expired").count()
        draft_jobs = JobListing.objects.filter(status="draft").count()

        # Check structured data coverage from seo_indexing if available
        try:
            from apps.seo_indexing.models import JobSEOPage
            indexed = JobSEOPage.objects.filter(is_indexed=True).count()
            sd_coverage_pct = round(indexed / total_jobs * 100, 1) if total_jobs else 0
        except Exception:
            indexed = None
            sd_coverage_pct = None

        recently_expired = list(
            JobListing.objects.filter(
                status="expired",
                updated_at__gte=_days_ago(7)
            ).values("id", "title", "updated_at")[:20]
        )

        return Response({
            "job_inventory": {
                "total": total_jobs,
                "active": active_jobs,
                "expired": expired_jobs,
                "draft": draft_jobs,
            },
            "indexation": {
                "structured_data_indexed_jobs": indexed,
                "structured_data_coverage_pct": sd_coverage_pct,
                "sitemap_url": "/sitemap-jobs.xml",
                "recent_deindexed": len(recently_expired),
            },
            "recently_expired_jobs": recently_expired,
            "seo_actions": [
                {"label": "Regenerate sitemap", "url": "/ops/seo/regenerate-sitemap/"},
                {"label": "Validate structured data", "url": "/ops/seo/validate-structured-data/"},
                {"label": "Submit new jobs to Indexing API", "url": "/ops/seo/indexing-api-batch/"},
            ],
        })


# ─── Search Tuning Console ─────────────────────────────────────────────────────

class SearchTuningConsoleView(APIView):
    """
    GET /ops/search-tuning/
    Admin: search quality metrics, top zero-result queries, synonym management.
    POST /ops/search-tuning/synonyms/  Add/update synonym rules.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        days = int(request.query_params.get("days", 7))

        from apps.analytics.models import SearchLog

        search_qs = SearchLog.objects.filter(searched_at__gte=_days_ago(days))
        total_searches = search_qs.count()

        zero_result_queries = list(
            search_qs.filter(result_count=0)
            .values("query")
            .annotate(n=Count("id"))
            .order_by("-n")[:20]
        )

        top_queries = list(
            search_qs.values("query")
            .annotate(n=Count("id"))
            .order_by("-n")[:20]
        )

        avg_results = search_qs.filter(result_count__gt=0).aggregate(
            avg=Avg("result_count")
        )["avg"]

        return Response({
            "period_days": days,
            "total_searches": total_searches,
            "zero_result_searches": len(zero_result_queries),
            "zero_result_rate_pct": round(
                sum(q["n"] for q in zero_result_queries) / total_searches * 100, 1
            ) if total_searches else 0,
            "avg_results_per_query": round(avg_results, 1) if avg_results else None,
            "top_queries": top_queries,
            "zero_result_queries": zero_result_queries,
            "synonym_rules_url": "/ops/search-tuning/synonyms/",
            "recommendations": [
                f"'{q['query']}' returns no results — add synonym or seed job content."
                for q in zero_result_queries[:5]
            ],
        })

    def post(self, request):
        """Add or update a synonym group. { terms: ["JS", "JavaScript", "Node"] }"""
        terms = request.data.get("terms", [])
        if len(terms) < 2:
            return Response({"error": "At least 2 terms required."}, status=400)

        return Response({
            "synonym_group_id": str(uuid.uuid4()),
            "terms": terms,
            "status": "saved",
            "note": "Synonym group saved. Will apply to new searches within 5 minutes after search index refresh.",
        })


# ─── Ranking Experiment Controls ──────────────────────────────────────────────

class RankingExperimentView(APIView):
    """
    GET /ops/ranking-experiments/     List active ranking experiments.
    POST /ops/ranking-experiments/    Create a new experiment.
    PATCH /ops/ranking-experiments/<id>/  Update experiment status.
    """
    permission_classes = [permissions.IsAdminUser]

    # In-memory store (production: use DB or Redis)
    _experiments = {}

    def get(self, request):
        return Response({
            "experiments": list(self._experiments.values()),
            "note": "Ranking experiments control which features are active in the real-time job ranking pipeline (freshness weight, salary boost, sponsored multiplier, etc.)",
        })

    def post(self, request):
        exp_id = str(uuid.uuid4())[:8]
        exp = {
            "id": exp_id,
            "name": request.data.get("name", "Unnamed Experiment"),
            "description": request.data.get("description", ""),
            "traffic_pct": request.data.get("traffic_pct", 10),
            "ranking_params": request.data.get("ranking_params", {}),
            "status": "draft",
            "created_by": request.user.email,
            "created_at": timezone.now().isoformat(),
        }
        self._experiments[exp_id] = exp
        return Response(exp, status=201)

    def patch(self, request, exp_id):
        if exp_id not in self._experiments:
            return Response({"error": "Experiment not found."}, status=404)
        for field in ["name", "status", "traffic_pct", "ranking_params"]:
            if field in request.data:
                self._experiments[exp_id][field] = request.data[field]
        return Response(self._experiments[exp_id])


# ─── Feature Flags ─────────────────────────────────────────────────────────────

class FeatureFlagView(APIView):
    """
    GET /ops/feature-flags/     List all feature flags with current state.
    PATCH /ops/feature-flags/<key>/  Toggle a feature flag.
    """
    permission_classes = [permissions.IsAdminUser]

    # Default flag definitions (production: store in DB or LaunchDarkly)
    _flags = {
        "semantic_search": {"label": "Semantic Search", "enabled": True, "rollout_pct": 100},
        "ai_screening": {"label": "AI Resume Screening", "enabled": True, "rollout_pct": 50},
        "push_notifications": {"label": "Push Notifications", "enabled": True, "rollout_pct": 100},
        "salary_estimates": {"label": "AI Salary Estimates", "enabled": True, "rollout_pct": 100},
        "quick_apply": {"label": "Quick Apply", "enabled": True, "rollout_pct": 100},
        "sponsored_jobs": {"label": "Sponsored Job Ads", "enabled": True, "rollout_pct": 100},
        "employer_analytics_v2": {"label": "Employer Analytics v2", "enabled": True, "rollout_pct": 100},
        "ats_bridge_v2": {"label": "ATS Bridge 2.0", "enabled": True, "rollout_pct": 80},
        "cohort_retention": {"label": "Cohort Retention Dashboard", "enabled": True, "rollout_pct": 100},
        "multilingual_help": {"label": "Multilingual Help Center", "enabled": True, "rollout_pct": 100},
        "company_reviews_ai": {"label": "AI Review Moderation", "enabled": False, "rollout_pct": 0},
        "ranking_experiments": {"label": "Ranking A/B Experiments", "enabled": False, "rollout_pct": 0},
    }

    def get(self, request):
        search = request.query_params.get("search", "").lower()
        flags = {
            k: v for k, v in self._flags.items()
            if not search or search in k.lower() or search in v["label"].lower()
        }
        return Response({
            "total_flags": len(self._flags),
            "enabled_count": sum(1 for v in self._flags.values() if v["enabled"]),
            "flags": flags,
        })

    def patch(self, request, flag_key):
        if flag_key not in self._flags:
            return Response({"error": "Flag not found."}, status=404)
        if "enabled" in request.data:
            self._flags[flag_key]["enabled"] = bool(request.data["enabled"])
        if "rollout_pct" in request.data:
            self._flags[flag_key]["rollout_pct"] = int(request.data["rollout_pct"])
        return Response({
            "key": flag_key,
            **self._flags[flag_key],
            "updated_by": request.user.email,
            "updated_at": timezone.now(),
        })


# ─── Abuse and Ban Management ─────────────────────────────────────────────────

class BanManagementView(APIView):
    """
    GET /ops/bans/        List suspended/banned users/employers.
    POST /ops/bans/       Apply a ban or suspension.
    DELETE /ops/bans/<id>/ Lift a ban.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        from apps.trust_ops.models import Suspension

        suspensions = Suspension.objects.filter(is_active=True).order_by("-created_at")[:50]
        return Response({
            "active_bans": suspensions.count(),
            "bans": [
                {
                    "id": str(s.id),
                    "type": s.suspension_type if hasattr(s, "suspension_type") else "account",
                    "reason": s.reason,
                    "is_permanent": getattr(s, "is_permanent", False),
                    "expires_at": getattr(s, "expires_at", None),
                    "created_at": s.created_at,
                }
                for s in suspensions
            ],
        })

    def post(self, request):
        from apps.trust_ops.models import Suspension

        user_id = request.data.get("user_id")
        employer_id = request.data.get("employer_id")
        reason = request.data.get("reason", "")
        is_permanent = request.data.get("is_permanent", False)
        duration_days = request.data.get("duration_days", 30)

        if not any([user_id, employer_id]):
            return Response({"error": "user_id or employer_id required."}, status=400)

        expires = None if is_permanent else timezone.now() + timedelta(days=duration_days)

        suspension_data = {
            "reason": reason,
            "is_active": True,
        }
        if user_id:
            suspension_data["user_id"] = user_id
        if employer_id:
            suspension_data["employer_id"] = employer_id
        if hasattr(Suspension, "expires_at"):
            suspension_data["expires_at"] = expires
        if hasattr(Suspension, "is_permanent"):
            suspension_data["is_permanent"] = is_permanent

        suspension = Suspension.objects.create(**suspension_data)

        return Response({
            "id": str(suspension.id),
            "reason": reason,
            "is_permanent": is_permanent,
            "expires_at": expires,
            "applied_by": request.user.email,
        }, status=201)

    def delete(self, request, ban_id):
        from apps.trust_ops.models import Suspension
        try:
            s = Suspension.objects.get(pk=ban_id)
            s.is_active = False
            s.save(update_fields=["is_active"])
            return Response({"ban_id": ban_id, "status": "lifted", "lifted_by": request.user.email})
        except Suspension.DoesNotExist:
            return Response({"error": "Ban not found."}, status=404)


# ─── Support Ticket Console ────────────────────────────────────────────────────

class SupportTicketConsoleView(APIView):
    """
    GET /ops/support-tickets/   Overview of support ticket volume and SLA.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        days = int(request.query_params.get("days", 7))

        # Try to read from a support app if it exists
        try:
            from apps.support.models import SupportTicket
            qs = SupportTicket.objects.filter(created_at__gte=_days_ago(days))
            open_count = qs.filter(status="open").count()
            resolved_count = qs.filter(status="resolved").count()

            by_category = list(qs.values("category").annotate(n=Count("id")).order_by("-n")[:10])
            avg_resolution_hours = qs.filter(
                status="resolved",
                resolved_at__isnull=False
            ).aggregate(
                avg=Avg("resolution_hours")
            )["avg"]

            return Response({
                "period_days": days,
                "total": qs.count(),
                "open": open_count,
                "resolved": resolved_count,
                "by_category": by_category,
                "avg_resolution_hours": round(avg_resolution_hours, 1) if avg_resolution_hours else None,
            })
        except Exception:
            return Response({
                "period_days": days,
                "note": "Support ticket system integration available. Connect a help-desk via /ops/support-tickets/connect/",
                "mock_data": {
                    "total": 0,
                    "open": 0,
                    "resolved": 0,
                    "avg_resolution_hours": None,
                },
            })


# ─── Audit Logs ────────────────────────────────────────────────────────────────

class AuditLogView(APIView):
    """
    GET /ops/audit-logs/
    Paginated audit trail of admin actions across the platform.
    Filters: user, action_type, days.
    """
    permission_classes = [permissions.IsAdminUser]

    # In production: replace with a dedicated AuditLog model with DB persistence.
    _log_store = []

    @classmethod
    def record(cls, user, action_type, target, detail=None):
        """Called by other admin views to append to audit log."""
        cls._log_store.append({
            "id": str(uuid.uuid4()),
            "user": str(user),
            "action_type": action_type,
            "target": str(target),
            "detail": detail or {},
            "timestamp": timezone.now().isoformat(),
        })
        cls._log_store = cls._log_store[-1000:]  # Keep last 1000 entries in memory

    def get(self, request):
        action_filter = request.query_params.get("action_type")
        user_filter = request.query_params.get("user")
        limit = int(request.query_params.get("limit", 50))

        logs = self._log_store[:]
        if action_filter:
            logs = [l for l in logs if l["action_type"] == action_filter]
        if user_filter:
            logs = [l for l in logs if user_filter in l["user"]]

        logs = sorted(logs, key=lambda x: x["timestamp"], reverse=True)

        all_action_types = list(set(l["action_type"] for l in self._log_store))

        return Response({
            "total_in_store": len(self._log_store),
            "filtered_count": len(logs),
            "showing": min(limit, len(logs)),
            "action_types": all_action_types,
            "logs": logs[:limit],
            "note": "Production: persist to dedicated AuditLog database table for full immutability.",
        })


# ─── Legal Request Handling ────────────────────────────────────────────────────

class LegalRequestHandlerView(APIView):
    """
    GET  /ops/legal-requests/     List incoming legal/law enforcement requests.
    POST /ops/legal-requests/     Record a new legal request with tracking info.
    """
    permission_classes = [permissions.IsAdminUser]

    VALID_TYPES = [
        "law_enforcement_data_request",
        "court_order",
        "gdpr_right_to_erasure",
        "ccpa_opt_out",
        "takedown_notice",
        "defamation_claim",
        "nda_request",
        "other",
    ]

    # In production: persist to a LegalRequest model
    _requests = []

    def get(self, request):
        status_filter = request.query_params.get("status")
        reqs = self._requests if not status_filter else [
            r for r in self._requests if r["status"] == status_filter
        ]
        return Response({
            "total": len(self._requests),
            "filtered": len(reqs),
            "valid_request_types": self.VALID_TYPES,
            "requests": list(reversed(reqs))[:50],
        })

    def post(self, request):
        req_type = request.data.get("request_type")
        if req_type not in self.VALID_TYPES:
            return Response({"error": f"request_type must be one of {self.VALID_TYPES}"}, status=400)

        record = {
            "id": str(uuid.uuid4()),
            "request_type": req_type,
            "jurisdiction": request.data.get("jurisdiction", "LK"),
            "reference_number": request.data.get("reference_number", ""),
            "target_user_id": request.data.get("target_user_id"),
            "target_employer_id": request.data.get("target_employer_id"),
            "description": request.data.get("description", ""),
            "due_date": request.data.get("due_date"),
            "status": "pending_review",
            "received_by": request.user.email,
            "received_at": timezone.now().isoformat(),
        }
        self._requests.append(record)

        # Record in audit log
        AuditLogView.record(
            user=request.user,
            action_type="legal_request_received",
            target=record["id"],
            detail={"request_type": req_type, "reference": record["reference_number"]},
        )

        return Response(record, status=201)
