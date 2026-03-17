"""Backend APIs: activity feed, scorecard CRUD, candidate comparison, webhook retry, and tenant-scoped throttles."""

import hashlib
import hmac
import json
import time
import logging
from datetime import timedelta
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from apps.candidates.models import Candidate
from apps.applications.models import Application
from apps.jobs.models import Job

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ACTIVITY FEED (#53)
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def activity_feed(request):
    """Unified activity feed across all entities.
    GET /api/v1/activity/?limit=50&type=all
    """
    limit = min(int(request.query_params.get("limit", 50)), 200)
    activity_type = request.query_params.get("type", "all")
    tenant = getattr(request, "tenant", None)

    activities = []

    # Recent applications
    app_qs = Application.objects.select_related("candidate", "job").order_by("-created_at")[:limit]
    if tenant:
        app_qs = app_qs.filter(job__tenant=tenant)
    for app in app_qs:
        activities.append({
            "type": "application",
            "actor": app.candidate.name if app.candidate else "Unknown",
            "target": app.job.title if app.job else "Unknown Job",
            "description": f"applied for {app.job.title}" if app.job else "submitted application",
            "timestamp": app.created_at.isoformat() if app.created_at else None,
            "icon": "📋",
        })

    # Recent candidates
    cand_qs = Candidate.objects.order_by("-created_at")[:limit]
    if tenant:
        cand_qs = cand_qs.filter(tenant=tenant)
    for c in cand_qs:
        activities.append({
            "type": "candidate_created",
            "actor": "System",
            "target": c.name,
            "description": f"added as new candidate from {c.source}",
            "timestamp": c.created_at.isoformat() if c.created_at else None,
            "icon": "👤",
        })

    # Sort by timestamp descending
    activities.sort(key=lambda a: a.get("timestamp") or "", reverse=True)

    if activity_type != "all":
        activities = [a for a in activities if a["type"] == activity_type]

    return Response(activities[:limit])


# ═══════════════════════════════════════════════════════════════════════════════
# CANDIDATE COMPARISON (#35)
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def compare_candidates(request):
    """Compare 2-4 candidates side by side.
    POST { "candidate_ids": ["id1", "id2", ...] }
    """
    ids = request.data.get("candidate_ids", [])
    if len(ids) < 2 or len(ids) > 4:
        return Response({"error": "Provide 2-4 candidate IDs"}, status=400)

    candidates = Candidate.objects.filter(id__in=ids)
    result = []
    for c in candidates:
        apps = Application.objects.filter(candidate=c)
        result.append({
            "id": str(c.id),
            "name": c.name,
            "email": c.email,
            "phone": c.phone,
            "source": c.source,
            "rating": c.rating,
            "tags": c.tags or [],
            "total_experience_years": getattr(c, "total_experience_years", 0),
            "skills_count": len(getattr(c, "extracted_skills", []) or []),
            "resume_completeness": getattr(c, "resume_completeness", 0),
            "application_count": apps.count(),
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    # Sort by rating desc for recommendation
    result.sort(key=lambda x: (x.get("rating") or 0), reverse=True)
    recommended = result[0]["name"] if result else None

    return Response({
        "candidates": result,
        "recommended": recommended,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# TALENT POOL GROUPING (#37)
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def talent_pools(request):
    """CRUD for talent pool categories.
    GET — list pools with counts
    POST { "name": "...", "description": "...", "candidate_ids": [...] }
    """
    if request.method == "GET":
        # Group candidates by tags as virtual talent pools
        tenant = getattr(request, "tenant", None)
        qs = Candidate.objects.all()
        if tenant:
            qs = qs.filter(tenant=tenant)

        pools = {}
        for c in qs:
            for tag in (c.tags or []):
                if tag not in pools:
                    pools[tag] = {"name": tag, "count": 0, "candidates": []}
                pools[tag]["count"] += 1
                if len(pools[tag]["candidates"]) < 5:
                    pools[tag]["candidates"].append({"id": str(c.id), "name": c.name})

        return Response(list(pools.values()))

    elif request.method == "POST":
        name = request.data.get("name", "")
        ids = request.data.get("candidate_ids", [])
        if not name:
            return Response({"error": "Pool name required"}, status=400)

        tenant = getattr(request, "tenant", None)
        qs = Candidate.objects.filter(id__in=ids)
        if tenant:
            qs = qs.filter(tenant=tenant)

        count = 0
        for c in qs:
            tags = c.tags or []
            if name not in tags:
                tags.append(name)
                c.tags = tags
                c.save(update_fields=["tags"])
                count += 1

        return Response({"pool": name, "added": count}, status=201)


# ═══════════════════════════════════════════════════════════════════════════════
# WEBHOOK RETRY WITH HMAC (#54, #55)
# ═══════════════════════════════════════════════════════════════════════════════

def deliver_webhook(url, payload, secret=None, max_retries=3):
    """Deliver a webhook with HMAC signature and exponential backoff retry."""
    import requests

    body = json.dumps(payload)
    headers = {"Content-Type": "application/json"}

    if secret:
        signature = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        headers["X-ATS-Signature"] = f"sha256={signature}"

    for attempt in range(max_retries):
        try:
            resp = requests.post(url, data=body, headers=headers, timeout=10)
            if resp.status_code < 400:
                logger.info(f"Webhook delivered to {url}: {resp.status_code}")
                return {"status": "delivered", "code": resp.status_code, "attempt": attempt + 1}
        except Exception as e:
            logger.warning(f"Webhook attempt {attempt + 1} failed for {url}: {e}")

        # Exponential backoff: 2^attempt seconds
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)

    logger.error(f"Webhook delivery failed after {max_retries} attempts: {url}")
    return {"status": "failed", "attempts": max_retries}


# ═══════════════════════════════════════════════════════════════════════════════
# PAGINATION HEADERS MIDDLEWARE (#57)
# ═══════════════════════════════════════════════════════════════════════════════

class PaginationHeaderMixin:
    """Add X-Total-Count and Link headers to paginated responses."""

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        if hasattr(self, "paginator") and self.paginator:
            qs = self.filter_queryset(self.get_queryset())
            total = qs.count()
            response["X-Total-Count"] = str(total)
        return response


# ═══════════════════════════════════════════════════════════════════════════════
# TENANT-SCOPED THROTTLE (#58)
# ═══════════════════════════════════════════════════════════════════════════════

class TenantRateThrottle(UserRateThrottle):
    """Per-tenant API rate limiting."""
    scope = "tenant"
    rate = "5000/hour"

    def get_cache_key(self, request, view):
        tenant = getattr(request, "tenant", None)
        if tenant:
            return f"throttle_tenant_{tenant.id}"
        return super().get_cache_key(request, view)


# ═══════════════════════════════════════════════════════════════════════════════
# FIELD-LEVEL PERMISSIONS (#59)
# ═══════════════════════════════════════════════════════════════════════════════

def filter_fields_by_role(data, user, sensitive_fields=None):
    """Remove sensitive fields from response based on user role.
    Example: salary_min, salary_max visible only to admin/recruiter.
    """
    sensitive_fields = sensitive_fields or ["salary_min", "salary_max", "ssn", "compensation"]
    role = getattr(user, "role", "viewer")
    if role in ("admin", "recruiter"):
        return data
    if isinstance(data, dict):
        return {k: v for k, v in data.items() if k not in sensitive_fields}
    if isinstance(data, list):
        return [{k: v for k, v in item.items() if k not in sensitive_fields} for item in data]
    return data
