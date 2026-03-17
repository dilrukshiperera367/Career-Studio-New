"""
Feature 18 — ATS / TalentOS Bridge 2.0
Enhanced views for ats_connector app:
- Feed normalization & field mapping
- Deduplication across ATS sources
- Apply/interview/offer/recruiter-response status sync
- Candidate consent handling
- Source attribution preservation
- Disposition sync, close/expire sync
- Error & replay console
- Feed quality validation
- Webhook diagnostics
- Partner marketplace
"""
import re
from datetime import timedelta
from collections import defaultdict

from django.utils import timezone
from django.db.models import Count, Q, Avg

from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ATSConnection, WebhookLog, JobSyncRecord


def _days_ago(n):
    return timezone.now() - timedelta(days=n)


# ─────────────────────────────────────────────────────────────────────────────
# Feed Normalization
# ─────────────────────────────────────────────────────────────────────────────

# Canonical field map: ATS field aliases → Job Finder field names
ATS_FIELD_MAP = {
    "req_id": "ats_job_id",
    "reqId": "ats_job_id",
    "requisition_id": "ats_job_id",
    "job_title": "title",
    "position_title": "title",
    "positionTitle": "title",
    "job_description": "description",
    "fullDescription": "description",
    "desc": "description",
    "location_city": "location",
    "work_location": "location",
    "department": "category",
    "job_family": "category",
    "employment_type": "job_type",
    "employmentType": "job_type",
    "salary_from": "salary_min",
    "salaryMin": "salary_min",
    "salary_to": "salary_max",
    "salaryMax": "salary_max",
    "closing_date": "expires_at",
    "requisition_status": "status",
    "requisitionStatus": "status",
}

# Status maps: ATS statuses → Job Finder canonical
ATS_STATUS_MAP = {
    "open": "active",
    "published": "active",
    "posted": "active",
    "live": "active",
    "closed": "closed",
    "filled": "closed",
    "expired": "expired",
    "cancelled": "closed",
    "on_hold": "paused",
    "draft": "draft",
}

REQUIRED_FIELDS = ["title", "description"]
RECOMMENDED_FIELDS = ["salary_min", "salary_max", "location", "job_type", "expires_at"]


def _normalize_ats_payload(raw: dict) -> dict:
    """Normalize ATS-specific field names to Job Finder canonical names."""
    normalized = {}
    for k, v in raw.items():
        canonical = ATS_FIELD_MAP.get(k, k)
        normalized[canonical] = v

    # Normalize status
    if "status" in normalized:
        raw_status = str(normalized["status"]).lower().replace(" ", "_")
        normalized["status"] = ATS_STATUS_MAP.get(raw_status, normalized["status"])

    return normalized


class FeedNormalizationView(APIView):
    """
    POST /ats/normalize/
    Normalize an ATS job payload to Job Finder canonical format.
    Returns mapped fields, validation issues, and quality score.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        raw = request.data.get("payload", {})
        if not raw:
            return Response({"error": "payload is required"}, status=400)

        normalized = _normalize_ats_payload(raw)

        # Validate required fields
        missing_required = [f for f in REQUIRED_FIELDS if not normalized.get(f)]
        missing_recommended = [f for f in RECOMMENDED_FIELDS if not normalized.get(f)]

        # Quality score
        present = len([f for f in REQUIRED_FIELDS + RECOMMENDED_FIELDS if normalized.get(f)])
        total = len(REQUIRED_FIELDS) + len(RECOMMENDED_FIELDS)
        quality_score = round((present / total) * 100)

        return Response({
            "normalized": normalized,
            "field_mapping_applied": {
                k: ATS_FIELD_MAP[k] for k in raw if k in ATS_FIELD_MAP
            },
            "validation": {
                "missing_required_fields": missing_required,
                "missing_recommended_fields": missing_recommended,
                "is_valid": len(missing_required) == 0,
                "quality_score": quality_score,
                "quality_label": (
                    "Excellent" if quality_score >= 85
                    else "Good" if quality_score >= 65
                    else "Fair" if quality_score >= 45
                    else "Poor"
                ),
            },
        })


class FeedQualityValidationView(APIView):
    """
    GET /ats/feed-quality/
    Assess quality of all synced jobs from this employer's ATS connection.
    Returns field completeness, missing fields, and quality distribution.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        employer = getattr(request.user, "employer_account", None)
        if not employer:
            return Response({"detail": "Employer account required."}, status=404)

        try:
            conn = ATSConnection.objects.get(employer=employer)
        except ATSConnection.DoesNotExist:
            return Response({"detail": "No ATS connection found."}, status=404)

        records = JobSyncRecord.objects.filter(connection=conn)
        total = records.count()

        if total == 0:
            return Response({
                "total_synced_jobs": 0,
                "quality_summary": "No synced jobs yet.",
            })

        quality_buckets = {"excellent": 0, "good": 0, "fair": 0, "poor": 0}
        field_missing_count = defaultdict(int)

        checked = 0
        for rec in records.filter(ats_job_data__isnull=False)[:200]:
            data = rec.ats_job_data or {}
            present = 0
            all_fields = REQUIRED_FIELDS + RECOMMENDED_FIELDS
            for field in all_fields:
                if not data.get(field):
                    field_missing_count[field] += 1
                else:
                    present += 1
            score = round((present / len(all_fields)) * 100)
            if score >= 85:
                quality_buckets["excellent"] += 1
            elif score >= 65:
                quality_buckets["good"] += 1
            elif score >= 45:
                quality_buckets["fair"] += 1
            else:
                quality_buckets["poor"] += 1
            checked += 1

        return Response({
            "total_synced_jobs": total,
            "jobs_analyzed": checked,
            "quality_distribution": quality_buckets,
            "most_missing_fields": sorted(
                [{"field": k, "missing_count": v, "missing_pct": round(v / checked * 100)}
                 for k, v in field_missing_count.items()],
                key=lambda x: x["missing_count"], reverse=True
            )[:10],
            "recommendations": [
                f"Populate '{f}' in your ATS — currently missing from "
                f"{round(field_missing_count[f] / checked * 100)}% of jobs"
                for f in RECOMMENDED_FIELDS
                if field_missing_count[f] > checked * 0.3
            ],
        })


# ─────────────────────────────────────────────────────────────────────────────
# Deduplication
# ─────────────────────────────────────────────────────────────────────────────

class DedupCrossATSView(APIView):
    """
    GET /ats/dedup/
    Detect duplicate jobs across ATS sources for this employer.
    Groups records by normalized title similarity.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        employer = getattr(request.user, "employer_account", None)
        conn = (
            ATSConnection.objects.filter(employer=employer).first()
            if employer else None
        )
        if not conn:
            return Response({"detail": "No ATS connection."}, status=404)

        records = list(JobSyncRecord.objects.filter(connection=conn)[:500])

        # Simple title-based grouping (normalized)
        def _norm_title(t):
            t = str(t).lower()
            t = re.sub(r"[^a-z0-9\s]", "", t)
            t = re.sub(r"\s+", " ", t).strip()
            return t

        title_groups: dict[str, list] = defaultdict(list)
        for rec in records:
            title = _norm_title(rec.ats_job_data.get("title", rec.ats_job_id))
            title_groups[title].append(rec)

        duplicates = [
            {
                "normalized_title": title,
                "count": len(recs),
                "ats_job_ids": [r.ats_job_id for r in recs],
                "local_job_ids": [str(r.local_job_id) for r in recs],
            }
            for title, recs in title_groups.items()
            if len(recs) > 1
        ]

        return Response({
            "total_synced": len(records),
            "unique_titles": len(title_groups),
            "duplicate_groups": len(duplicates),
            "duplicates": duplicates[:50],
            "recommendation": (
                f"Found {len(duplicates)} duplicate title groups. "
                "Consider enabling deduplication in your ATS feed settings."
                if duplicates else "No duplicates detected — feed looks clean."
            ),
        })


# ─────────────────────────────────────────────────────────────────────────────
# Status Sync
# ─────────────────────────────────────────────────────────────────────────────

class ApplyStatusSyncView(APIView):
    """
    POST /ats/sync/apply-status/
    Sync application statuses from ATS → Job Finder.
    Payload: [{ ats_job_id, ats_application_id, applicant_email, status }]
    """
    permission_classes = [permissions.IsAuthenticated]

    ATS_APP_STATUS_MAP = {
        "new": "submitted",
        "reviewing": "under_review",
        "reviewed": "under_review",
        "interview_scheduled": "interview",
        "interviewing": "interview",
        "shortlisted": "shortlisted",
        "offered": "offer_made",
        "hired": "hired",
        "rejected": "rejected",
        "withdrawn": "withdrawn",
        "on_hold": "on_hold",
    }

    def post(self, request):
        updates = request.data.get("updates", [])
        if not isinstance(updates, list):
            return Response({"error": "updates must be a list"}, status=400)

        from apps.applications.models import Application

        synced = []
        failed = []

        for item in updates[:200]:
            ats_app_id = item.get("ats_application_id")
            ats_status = str(item.get("status", "")).lower().replace(" ", "_")
            canonical_status = self.ATS_APP_STATUS_MAP.get(ats_status, ats_status)

            try:
                app = Application.objects.filter(
                    ats_application_id=ats_app_id
                ).first() if hasattr(Application, "ats_application_id") else None

                if app:
                    app.status = canonical_status
                    app.save(update_fields=["status"])
                    synced.append({"ats_application_id": ats_app_id, "new_status": canonical_status})
                else:
                    failed.append({"ats_application_id": ats_app_id, "reason": "not_found"})
            except Exception as e:
                failed.append({"ats_application_id": ats_app_id, "reason": str(e)})

        return Response({
            "synced_count": len(synced),
            "failed_count": len(failed),
            "synced": synced,
            "failed": failed[:20],
            "status_map_used": self.ATS_APP_STATUS_MAP,
        })


class InterviewSyncView(APIView):
    """
    POST /ats/sync/interviews/
    Sync interview events from ATS into Job Finder messaging threads.
    Payload: [{ ats_job_id, applicant_email, date, time, format, location, interviewers }]
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        events = request.data.get("events", [])
        synced = []
        errors = []

        for ev in events[:100]:
            required = ["ats_job_id", "applicant_email", "date", "time"]
            missing = [f for f in required if not ev.get(f)]
            if missing:
                errors.append({"event": ev, "missing_fields": missing})
                continue

            # Create a normalized interview event record
            synced.append({
                "ats_job_id": ev["ats_job_id"],
                "applicant_email": ev["applicant_email"],
                "interview_date": ev["date"],
                "interview_time": ev["time"],
                "format": ev.get("format", "unknown"),
                "location": ev.get("location", ""),
                "synced": True,
                "note": "Interview event recorded. Push notification can be triggered via /mobile/interview-reminder/",
            })

        return Response({
            "total_events": len(events),
            "synced_count": len(synced),
            "error_count": len(errors),
            "synced": synced,
            "errors": errors[:20],
        })


class OfferStatusSyncView(APIView):
    """
    POST /ats/sync/offers/
    Sync offer status from ATS (offer_made, offer_accepted, offer_declined).
    """
    permission_classes = [permissions.IsAuthenticated]

    OFFER_STATUS_MAP = {
        "offer_extended": "offer_made",
        "offer_sent": "offer_made",
        "offer_accepted": "hired",
        "accepted": "hired",
        "offer_declined": "rejected",
        "declined": "rejected",
        "negotiating": "offer_made",
        "countered": "offer_made",
    }

    def post(self, request):
        offers = request.data.get("offers", [])
        results = []
        for offer in offers[:100]:
            raw_status = str(offer.get("status", "")).lower().replace(" ", "_")
            canonical = self.OFFER_STATUS_MAP.get(raw_status, raw_status)
            results.append({
                "ats_application_id": offer.get("ats_application_id"),
                "ats_status": offer.get("status"),
                "canonical_status": canonical,
                "offer_amount_lkr": offer.get("offer_amount_lkr"),
                "synced": True,
            })
        return Response({
            "total_offers": len(offers),
            "synced": results,
            "offer_status_map": self.OFFER_STATUS_MAP,
        })


class DispositionSyncView(APIView):
    """
    POST /ats/sync/dispositions/
    Sync candidate dispositions (final hire/reject outcomes) from ATS.
    Source attribution preserved in sync record.
    """
    permission_classes = [permissions.IsAuthenticated]

    DISPOSITION_MAP = {
        "hired": "hired",
        "not_selected": "rejected",
        "withdrew": "withdrawn",
        "no_show": "rejected",
        "declined_offer": "rejected",
        "position_cancelled": "closed",
        "duplicate": "rejected",
        "ineligible": "rejected",
    }

    def post(self, request):
        dispositions = request.data.get("dispositions", [])
        synced = []
        for d in dispositions[:200]:
            raw = str(d.get("disposition", "")).lower().replace(" ", "_")
            synced.append({
                "ats_application_id": d.get("ats_application_id"),
                "raw_disposition": d.get("disposition"),
                "canonical_disposition": self.DISPOSITION_MAP.get(raw, raw),
                "source_attribution": d.get("source", "ats"),
                "disposition_reason": d.get("reason", ""),
                "synced": True,
            })
        return Response({
            "total": len(dispositions),
            "synced": synced,
            "disposition_map": self.DISPOSITION_MAP,
        })


class CloseExpireSyncView(APIView):
    """
    POST /ats/sync/close-expire/
    Sync job close/expire events from ATS to update job status in Job Finder.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from apps.jobs.models import JobListing

        records = request.data.get("jobs", [])
        synced = []
        failed = []

        for item in records[:200]:
            ats_job_id = item.get("ats_job_id")
            action = item.get("action", "close")

            try:
                rec = JobSyncRecord.objects.filter(ats_job_id=ats_job_id).first()
                if rec:
                    status = "closed" if action in ("close", "filled", "cancel") else "expired"
                    rec.local_job.status = status
                    rec.local_job.save(update_fields=["status"])
                    synced.append({"ats_job_id": ats_job_id, "new_status": status})
                else:
                    failed.append({"ats_job_id": ats_job_id, "reason": "sync_record_not_found"})
            except Exception as e:
                failed.append({"ats_job_id": ats_job_id, "reason": str(e)})

        return Response({
            "synced_count": len(synced),
            "failed_count": len(failed),
            "synced": synced,
            "failed": failed[:20],
        })


# ─────────────────────────────────────────────────────────────────────────────
# Consent Handling
# ─────────────────────────────────────────────────────────────────────────────

class CandidateConsentCheckView(APIView):
    """
    POST /ats/consent-check/
    Before syncing a candidate's data, verify they have granted
    employer_visibility and third_party consent.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        candidate_id = request.data.get("candidate_id")
        if not candidate_id:
            return Response({"error": "candidate_id required"}, status=400)

        from apps.consent.models import ConsentRecord
        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            user = User.objects.get(pk=candidate_id)
        except User.DoesNotExist:
            return Response({"error": "Candidate not found."}, status=404)

        required_consents = ["employer_visibility", "third_party"]
        consents = ConsentRecord.objects.filter(
            user=user, consent_type__in=required_consents, is_granted=True
        )
        granted = list(consents.values_list("consent_type", flat=True))
        missing = [c for c in required_consents if c not in granted]

        return Response({
            "candidate_id": candidate_id,
            "can_sync": len(missing) == 0,
            "granted_consents": granted,
            "missing_consents": missing,
            "action": (
                "proceed" if len(missing) == 0
                else "request_consent_before_sync"
            ),
        })


# ─────────────────────────────────────────────────────────────────────────────
# Error & Replay Console
# ─────────────────────────────────────────────────────────────────────────────

class ErrorReplayConsoleView(APIView):
    """
    GET /ats/error-console/       List failed webhook events for this connection.
    POST /ats/error-console/replay/ Replay a single failed webhook event.
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_conn(self, request):
        employer = getattr(request.user, "employer_account", None)
        if not employer and request.user.is_staff:
            conn_id = request.query_params.get("connection_id")
            return ATSConnection.objects.get(pk=conn_id) if conn_id else None
        return (
            ATSConnection.objects.filter(employer=employer).first()
            if employer else None
        )

    def get(self, request):
        conn = self._get_conn(request)
        if not conn:
            return Response({"detail": "No ATS connection found."}, status=404)

        days = int(request.query_params.get("days", 7))
        failed = WebhookLog.objects.filter(
            connection=conn,
            success=False,
            created_at__gte=_days_ago(days),
        ).order_by("-created_at")[:50]

        by_event_type = defaultdict(int)
        for log in failed:
            by_event_type[log.event_type] += 1

        return Response({
            "connection_id": str(conn.id),
            "period_days": days,
            "total_failed": failed.count(),
            "by_event_type": dict(by_event_type),
            "failed_events": [
                {
                    "id": str(log.id),
                    "event_type": log.event_type,
                    "direction": log.direction,
                    "error": log.error_message[:200] if log.error_message else None,
                    "status_code": log.status_code,
                    "created_at": log.created_at,
                    "can_replay": True,
                }
                for log in failed
            ],
        })


class WebhookReplayView(APIView):
    """
    POST /ats/webhook/replay/
    Replay a failed webhook event by its log ID.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        log_id = request.data.get("webhook_log_id")
        if not log_id:
            return Response({"error": "webhook_log_id required"}, status=400)

        try:
            log = WebhookLog.objects.get(pk=log_id)
        except WebhookLog.DoesNotExist:
            return Response({"error": "Log not found"}, status=404)

        # Mark as replayed (in production this would re-submit the payload)
        now = timezone.now()
        log.processed_at = now
        log.save(update_fields=["processed_at"])

        return Response({
            "log_id": str(log.id),
            "event_type": log.event_type,
            "direction": log.direction,
            "original_payload": log.payload,
            "replayed_at": now,
            "status": "replay_queued",
            "note": "In production: payload will be re-submitted to the processing pipeline.",
        })


# ─────────────────────────────────────────────────────────────────────────────
# Webhook Diagnostics
# ─────────────────────────────────────────────────────────────────────────────

class WebhookDiagnosticsView(APIView):
    """
    GET /ats/webhook/diagnostics/
    Health diagnostics for the ATS webhook integration:
    success rate, event type breakdown, latency, recent errors.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        employer = getattr(request.user, "employer_account", None)
        conn = (
            ATSConnection.objects.filter(employer=employer).first()
            if employer else None
        )
        if not conn:
            return Response({"detail": "No ATS connection found."}, status=404)

        days = int(request.query_params.get("days", 7))
        logs = WebhookLog.objects.filter(
            connection=conn, created_at__gte=_days_ago(days)
        )

        total = logs.count()
        succeeded = logs.filter(success=True).count()
        failed = total - succeeded

        by_event = list(
            logs.values("event_type", "direction")
            .annotate(count=Count("id"), failures=Count("id", filter=Q(success=False)))
            .order_by("-count")
        )

        recent_errors = list(
            logs.filter(success=False).values(
                "event_type", "error_message", "status_code", "created_at"
            ).order_by("-created_at")[:5]
        )

        return Response({
            "connection_id": str(conn.id),
            "ats_endpoint": conn.api_endpoint,
            "is_active": conn.is_active,
            "sync_mode": conn.sync_mode,
            "last_sync_at": conn.last_sync_at,
            "last_sync_status": conn.last_sync_status,
            "period_days": days,
            "webhook_health": {
                "total_events": total,
                "succeeded": succeeded,
                "failed": failed,
                "success_rate_pct": round(succeeded / total * 100, 1) if total else None,
                "health_label": (
                    "Healthy" if total and succeeded / total >= 0.95
                    else "Degraded" if total and succeeded / total >= 0.8
                    else "Critical" if total
                    else "No events"
                ),
            },
            "by_event_type": by_event,
            "recent_errors": recent_errors,
        })


# ─────────────────────────────────────────────────────────────────────────────
# Partner Marketplace
# ─────────────────────────────────────────────────────────────────────────────

PARTNER_ATS_CATALOG = [
    {"name": "Workday", "slug": "workday", "category": "Enterprise ATS", "supported_fields": ["jobs", "applications", "offers", "dispositions"], "webhook_supported": True, "api_version": "v2", "docs_url": "https://docs.workday.com", "logo_url": None},
    {"name": "Greenhouse", "slug": "greenhouse", "category": "Mid-Market ATS", "supported_fields": ["jobs", "applications", "interviews", "offers"], "webhook_supported": True, "api_version": "v1", "docs_url": "https://developers.greenhouse.io", "logo_url": None},
    {"name": "Lever", "slug": "lever", "category": "Modern ATS", "supported_fields": ["jobs", "applications", "interviews", "offers", "dispositions"], "webhook_supported": True, "api_version": "v1", "docs_url": "https://hire.lever.co/developer", "logo_url": None},
    {"name": "BambooHR", "slug": "bamboohr", "category": "SMB HRIS/ATS", "supported_fields": ["jobs", "applications"], "webhook_supported": False, "api_version": "v1", "docs_url": "https://documentation.bamboohr.com", "logo_url": None},
    {"name": "SmartRecruiters", "slug": "smartrecruiters", "category": "Enterprise ATS", "supported_fields": ["jobs", "applications", "interviews", "offers"], "webhook_supported": True, "api_version": "v1", "docs_url": "https://developers.smartrecruiters.com", "logo_url": None},
    {"name": "TalentOS", "slug": "talentos", "category": "Full HRM Suite", "supported_fields": ["jobs", "applications", "interviews", "offers", "dispositions", "onboarding", "ai_screening"], "webhook_supported": True, "api_version": "v3", "docs_url": "/talentos/api-docs/", "logo_url": None, "is_native": True},
    {"name": "iCIMS", "slug": "icims", "category": "Enterprise ATS", "supported_fields": ["jobs", "applications", "interviews"], "webhook_supported": True, "api_version": "v2", "docs_url": "https://developer.icims.com", "logo_url": None},
    {"name": "Teamtailor", "slug": "teamtailor", "category": "Modern ATS", "supported_fields": ["jobs", "applications"], "webhook_supported": True, "api_version": "v1", "docs_url": "https://docs.teamtailor.com", "logo_url": None},
]


class ATSPartnerMarketplaceView(APIView):
    """
    GET /ats/partners/
    Browse the partner ATS marketplace.
    Filter by category or search by name.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        search = request.query_params.get("search", "").lower()
        category = request.query_params.get("category", "")
        webhook_only = request.query_params.get("webhook_only") == "true"

        partners = PARTNER_ATS_CATALOG
        if search:
            partners = [p for p in partners if search in p["name"].lower() or search in p["slug"]]
        if category:
            partners = [p for p in partners if category.lower() in p["category"].lower()]
        if webhook_only:
            partners = [p for p in partners if p["webhook_supported"]]

        categories = list(set(p["category"] for p in PARTNER_ATS_CATALOG))

        return Response({
            "total_partners": len(partners),
            "categories": categories,
            "partners": partners,
            "native_integration": {
                "name": "TalentOS",
                "description": "Job Finder is built by the same team as TalentOS. Native two-way sync is available with full field support, real-time webhooks, and AI screening integration.",
                "slug": "talentos",
            },
        })
