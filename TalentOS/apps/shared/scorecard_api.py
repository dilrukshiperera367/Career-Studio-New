"""Scorecard CRUD API — DB-backed interview scorecards and templates.

Previously used in-memory Python dicts; replaced with proper DB persistence
via apps.scoring.models.ScorecardTemplate and apps.scoring.models.Scorecard.
"""

import logging
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.scoring.models import ScorecardTemplate, Scorecard

logger = logging.getLogger(__name__)


# ── Pagination ────────────────────────────────────────────────────────────────

class ScorecardPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


# ── Serializers ───────────────────────────────────────────────────────────────

class ScorecardTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScorecardTemplate
        fields = ["id", "name", "criteria", "created_by", "created_at", "updated_at"]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class ScorecardSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for Scorecard — both create and read."""
    interviewer_email = serializers.EmailField(
        source="interviewer.email", read_only=True, default=None
    )
    application_id = serializers.UUIDField(source="application.id", read_only=True)
    candidate_id = serializers.UUIDField(
        source="application.candidate_id", read_only=True
    )

    class Meta:
        model = Scorecard
        fields = [
            "id",
            "application",
            "application_id",
            "candidate_id",
            "interviewer",
            "interviewer_email",
            "template",
            "interview_date",
            "overall_score",
            "technical_score",
            "communication_score",
            "culture_fit_score",
            "notes",
            "recommendation",
            "extra_scores",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "application_id",
            "candidate_id",
            "interviewer_email",
            "created_at",
            "updated_at",
        ]



# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATE CRUD
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def scorecard_template_list(request):
    """List or create scorecard templates (tenant-scoped)."""
    tenant_id = getattr(request.user, "tenant_id", None)

    if request.method == "GET":
        qs = ScorecardTemplate.objects.all()
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        paginator = ScorecardPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = ScorecardTemplateSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    # POST — create
    serializer = ScorecardTemplateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    template = serializer.save(
        created_by=request.user,
        tenant_id=tenant_id,
    )
    return Response(ScorecardTemplateSerializer(template).data, status=201)


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def scorecard_template_detail(request, template_id):
    """Retrieve, update, or delete a scorecard template."""
    tenant_id = getattr(request.user, "tenant_id", None)
    try:
        qs = ScorecardTemplate.objects.all()
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        template = qs.get(pk=template_id)
    except (ScorecardTemplate.DoesNotExist, Exception):
        return Response({"error": "Template not found"}, status=404)

    if request.method == "GET":
        return Response(ScorecardTemplateSerializer(template).data)

    if request.method == "PUT":
        serializer = ScorecardTemplateSerializer(template, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    # DELETE
    template.delete()
    return Response(status=204)


# ═══════════════════════════════════════════════════════════════════════════════
# SCORECARD SUBMISSION
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def scorecard_submission_list(request):
    """List (with optional candidate filter) or submit a scorecard evaluation."""
    tenant_id = getattr(request.user, "tenant_id", None)

    if request.method == "GET":
        qs = Scorecard.objects.select_related(
            "application", "application__candidate", "interviewer", "template"
        )
        candidate_id = request.query_params.get("candidate_id")
        if candidate_id:
            qs = qs.filter(application__candidate_id=candidate_id)
        if tenant_id:
            qs = qs.filter(application__tenant_id=tenant_id)
        paginator = ScorecardPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = ScorecardSubmissionSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    # POST — submit a scorecard
    serializer = ScorecardSubmissionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    application = serializer.validated_data.get("application")
    if tenant_id and str(getattr(application, "tenant_id", "")) != str(tenant_id):
        return Response({"error": "Application not found in your tenant"}, status=403)

    # Default interviewer to requesting user if not supplied
    if "interviewer" not in serializer.validated_data:
        serializer.validated_data["interviewer"] = request.user

    try:
        scorecard = serializer.save()
    except Exception as exc:
        logger.exception("Scorecard save failed")
        return Response({"error": str(exc)}, status=400)

    return Response(ScorecardSubmissionSerializer(scorecard).data, status=201)


# ═══════════════════════════════════════════════════════════════════════════════
# AGGREGATION
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def scorecard_aggregate(request, candidate_id):
    """Aggregate all scorecards for a candidate across all their applications."""
    tenant_id = getattr(request.user, "tenant_id", None)

    qs = Scorecard.objects.filter(
        application__candidate_id=candidate_id,
    ).select_related("application")
    if tenant_id:
        qs = qs.filter(application__tenant_id=tenant_id)

    scorecards = list(qs)

    if not scorecards:
        return Response({
            "candidate_id": str(candidate_id),
            "total_reviews": 0,
            "overall_score": None,
            "avg_scores": {},
            "recommendations": {},
            "submissions": [],
        })

    score_fields = ["overall_score", "technical_score", "communication_score", "culture_fit_score"]
    agg: dict = {f: [] for f in score_fields}
    recommendations: dict = {}

    for sc in scorecards:
        for field in score_fields:
            val = getattr(sc, field)
            if val is not None:
                agg[field].append(val)
        rec = sc.recommendation
        recommendations[rec] = recommendations.get(rec, 0) + 1

    avg_scores = {k: round(sum(v) / len(v), 2) for k, v in agg.items() if v}
    overall = avg_scores.get("overall_score")

    return Response({
        "candidate_id": str(candidate_id),
        "total_reviews": len(scorecards),
        "overall_score": overall,
        "avg_scores": avg_scores,
        "recommendations": recommendations,
        "submissions": ScorecardSubmissionSerializer(scorecards, many=True).data,
    })
