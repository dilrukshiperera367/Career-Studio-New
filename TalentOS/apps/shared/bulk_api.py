"""Bulk action, export, import, clone, and merge API views."""

import csv
import io
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.candidates.models import Candidate
from apps.applications.models import Application
from apps.jobs.models import Job


# ─── Bulk Stage Transition ────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bulk_stage_transition(request):
    """Move multiple applications to a new stage.
    POST { "application_ids": [...], "stage": "interview" }
    """
    app_ids = request.data.get("application_ids", [])
    new_stage = request.data.get("stage", "")
    if not app_ids or not new_stage:
        return Response({"error": "application_ids and stage required"}, status=400)

    tenant = getattr(request, "tenant", None)
    qs = Application.objects.filter(id__in=app_ids)
    if tenant:
        qs = qs.filter(job__tenant=tenant)

    count = qs.update(current_stage_name=new_stage)
    return Response({"updated": count, "stage": new_stage})


# ─── Bulk Reject ──────────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bulk_reject(request):
    """Reject multiple applications.
    POST { "application_ids": [...], "reason": "optional" }
    """
    app_ids = request.data.get("application_ids", [])
    reason = request.data.get("reason", "Not a fit at this time.")
    if not app_ids:
        return Response({"error": "application_ids required"}, status=400)

    tenant = getattr(request, "tenant", None)
    qs = Application.objects.filter(id__in=app_ids)
    if tenant:
        qs = qs.filter(job__tenant=tenant)

    count = qs.update(status="rejected", rejection_reason=reason)
    return Response({"rejected": count, "reason": reason})


# ─── Bulk Tag ─────────────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bulk_tag(request):
    """Add tag to multiple candidates.
    POST { "candidate_ids": [...], "tag": "senior" }
    """
    cand_ids = request.data.get("candidate_ids", [])
    tag = request.data.get("tag", "")
    if not cand_ids or not tag:
        return Response({"error": "candidate_ids and tag required"}, status=400)

    tenant = getattr(request, "tenant", None)
    qs = Candidate.objects.filter(id__in=cand_ids)
    if tenant:
        qs = qs.filter(tenant=tenant)

    count = 0
    for candidate in qs:
        tags = candidate.tags or []
        if tag not in tags:
            tags.append(tag)
            candidate.tags = tags
            candidate.save(update_fields=["tags"])
            count += 1
    return Response({"tagged": count, "tag": tag})


# ─── Export Candidates CSV ────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export_candidates_csv(request):
    """Export all candidates as CSV."""
    tenant = getattr(request, "tenant", None)
    qs = Candidate.objects.all()
    if tenant:
        qs = qs.filter(tenant=tenant)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="candidates.csv"'
    writer = csv.writer(response)
    writer.writerow(["Name", "Email", "Phone", "Source", "Status", "Rating", "Tags", "Created"])
    for c in qs.order_by("-created_at")[:5000]:
        writer.writerow([
            c.name, c.email, c.phone, c.source,
            c.status if hasattr(c, 'status') else "",
            c.rating, ",".join(c.tags or []),
            c.created_at.isoformat() if c.created_at else "",
        ])
    return response


# ─── Export Jobs CSV ──────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export_jobs_csv(request):
    """Export all jobs as CSV."""
    tenant = getattr(request, "tenant", None)
    qs = Job.objects.all()
    if tenant:
        qs = qs.filter(tenant=tenant)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="jobs.csv"'
    writer = csv.writer(response)
    writer.writerow(["Title", "Department", "Location", "Type", "Status", "Created"])
    for j in qs.order_by("-created_at")[:5000]:
        writer.writerow([
            j.title, j.department, j.location,
            j.employment_type, j.status,
            j.created_at.isoformat() if j.created_at else "",
        ])
    return response


# ─── Import Candidates CSV ───────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def import_candidates_csv(request):
    """Import candidates from CSV file.
    POST multipart form with 'file' field.
    Expected headers: name,email,phone,source
    """
    csv_file = request.FILES.get("file")
    if not csv_file:
        return Response({"error": "No file uploaded"}, status=400)

    if not csv_file.name.endswith(".csv"):
        return Response({"error": "File must be .csv"}, status=400)

    tenant = getattr(request, "tenant", None)
    decoded = csv_file.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(decoded))
    created = 0
    skipped = 0
    errors = []

    for i, row in enumerate(reader, start=2):
        name = row.get("name", "").strip()
        email = row.get("email", "").strip()
        if not name or not email:
            errors.append(f"Row {i}: missing name or email")
            skipped += 1
            continue

        if Candidate.objects.filter(email=email, tenant=tenant).exists():
            skipped += 1
            continue

        try:
            Candidate.objects.create(
                name=name,
                email=email,
                phone=row.get("phone", "").strip(),
                source=row.get("source", "csv_import").strip(),
                tenant=tenant,
            )
            created += 1
        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")
            skipped += 1

    return Response({
        "created": created,
        "skipped": skipped,
        "errors": errors[:20],
    })


# ─── Job Clone ────────────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def clone_job(request, job_id):
    """Clone a job with all its settings. POST /api/v1/jobs/{id}/clone/"""
    try:
        original = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        return Response({"error": "Job not found"}, status=404)

    original.pk = None
    original.title = f"{original.title} (Copy)"
    original.status = "draft"
    original.save()
    return Response({"id": str(original.id), "title": original.title, "status": "draft"}, status=201)


# ─── Candidate Merge ─────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def merge_candidates(request):
    """Merge duplicate candidates.
    POST { "primary_id": "...", "secondary_ids": ["...", "..."] }
    """
    primary_id = request.data.get("primary_id")
    secondary_ids = request.data.get("secondary_ids", [])
    if not primary_id or not secondary_ids:
        return Response({"error": "primary_id and secondary_ids required"}, status=400)

    try:
        primary = Candidate.objects.get(id=primary_id)
    except Candidate.DoesNotExist:
        return Response({"error": "Primary candidate not found"}, status=404)

    merged_count = 0
    for sec_id in secondary_ids:
        try:
            secondary = Candidate.objects.get(id=sec_id)
        except Candidate.DoesNotExist:
            continue

        # Merge tags
        primary_tags = set(primary.tags or [])
        primary_tags.update(secondary.tags or [])
        primary.tags = list(primary_tags)

        # Transfer applications
        Application.objects.filter(candidate=secondary).update(candidate=primary)

        # Fill missing fields
        if not primary.phone and secondary.phone:
            primary.phone = secondary.phone
        if not primary.linkedin_url and getattr(secondary, "linkedin_url", None):
            primary.linkedin_url = secondary.linkedin_url

        # Delete secondary
        secondary.delete()
        merged_count += 1

    primary.save()
    return Response({
        "primary_id": str(primary.id),
        "merged": merged_count,
        "total_tags": len(primary.tags or []),
    })
