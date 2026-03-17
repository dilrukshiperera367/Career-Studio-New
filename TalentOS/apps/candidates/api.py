"""API for Candidates app — CRUD, resume upload, dedup."""

import csv
import io
import uuid
from django.http import HttpResponse
from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.candidates.models import (
    Candidate, ResumeDocument, CandidateSkill, CandidateExperience,
    CandidateNote, CandidateCertification,
)
from apps.accounts.permissions import IsRecruiter, HasTenantAccess, IsAdminUser


# ── Pagination ───────────────────────────────────────────────────────────────

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


# ── Serializers ──────────────────────────────────────────────────────────────

class CandidateSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateSkill
        fields = ["id", "canonical_name", "confidence", "years_used", "evidence"]


class CandidateExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateExperience
        fields = [
            "id", "company_name", "title", "normalized_title",
            "start_date", "end_date", "is_current", "description",
        ]


class ResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResumeDocument
        fields = [
            "id", "version", "file_url", "file_type",
            "parse_status", "parse_confidence", "parse_warnings",
            "created_at",
        ]
        read_only_fields = ["id", "version", "parse_status", "created_at"]


class CandidateNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.get_full_name", read_only=True, default="")
    replies_count = serializers.SerializerMethodField()

    class Meta:
        model = CandidateNote
        fields = ["id", "author", "author_name", "content", "is_internal",
                  "mentions", "parent_note", "replies_count", "created_at", "updated_at"]
        read_only_fields = ["id", "author", "created_at", "updated_at"]

    def get_replies_count(self, obj):
        return obj.replies.count() if hasattr(obj, 'replies') else 0


class CandidateCertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateCertification
        fields = ["id", "name", "issuer", "issue_date", "expiry_date", "credential_id", "created_at"]
        read_only_fields = ["id", "created_at"]


class CandidateSerializer(serializers.ModelSerializer):
    skills = CandidateSkillSerializer(many=True, read_only=True)
    experiences = CandidateExperienceSerializer(many=True, read_only=True)
    resumes = ResumeSerializer(many=True, read_only=True)
    certifications = CandidateCertificationSerializer(many=True, read_only=True)

    class Meta:
        model = Candidate
        fields = [
            "id", "full_name", "primary_email", "primary_phone",
            "headline", "location", "linkedin_url", "github_url", "portfolio_url",
            "total_experience_years", "most_recent_title", "most_recent_company",
            "recency_score", "highest_education", "resume_completeness",
            "source", "tags", "status",
            "pool_status", "talent_tier", "availability", "preferred_contact",
            "rating", "assigned_to",
            "consent_given_at", "consent_expires_at", "data_retention_until",
            "skills", "experiences", "resumes", "certifications",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "total_experience_years", "most_recent_title",
            "most_recent_company", "recency_score", "highest_education",
            "resume_completeness", "created_at", "updated_at",
        ]


class CandidateCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = [
            "full_name", "primary_email", "primary_phone",
            "headline", "location", "linkedin_url", "source",
            "talent_tier", "availability", "preferred_contact",
        ]


# ── ViewSets ─────────────────────────────────────────────────────────────────

class CandidateViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    pagination_class = StandardResultsSetPagination
    search_fields = ["full_name", "primary_email", "primary_phone", "headline", "most_recent_title"]
    ordering_fields = ["created_at", "full_name", "rating", "talent_tier"]
    filterset_fields = ["status", "source", "pool_status", "talent_tier", "availability"]

    def get_serializer_class(self):
        if self.action in ("create",):
            return CandidateCreateSerializer
        return CandidateSerializer

    def get_queryset(self):
        qs = Candidate.objects.filter(
            tenant_id=self.request.tenant_id,
            status="active",
        ).prefetch_related("skills", "experiences", "resumes", "certifications")
        # Filter by pool_status if specified
        pool_status = self.request.query_params.get('pool_status')
        if pool_status:
            qs = qs.filter(pool_status=pool_status)
        return qs

    def perform_create(self, serializer):
        # Run dedup before creating
        from apps.candidates.services import resolve_candidate

        data = serializer.validated_data
        result = resolve_candidate(
            tenant_id=str(self.request.tenant_id),
            full_name=data["full_name"],
            email=data.get("primary_email"),
            phone=data.get("primary_phone"),
            linkedin=data.get("linkedin_url"),
        )

        if result["action"] == "existing" or result["action"] == "auto_linked":
            # Return existing candidate (don't create duplicate)
            self.existing_candidate_id = result["candidate_id"]
            return

        serializer.save(tenant_id=self.request.tenant_id)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.existing_candidate_id = None
        self.perform_create(serializer)

        if self.existing_candidate_id:
            candidate = Candidate.objects.get(id=self.existing_candidate_id)
            return Response(
                CandidateSerializer(candidate).data,
                status=status.HTTP_200_OK,
            )

        return Response(
            CandidateSerializer(serializer.instance).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def upload_resume(self, request, pk=None):
        """Upload a resume for a candidate, triggers async parse."""
        candidate = self.get_object()
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate file type and size
        from django.conf import settings
        max_size = getattr(settings, "RESUME_MAX_SIZE_MB", 10) * 1024 * 1024
        allowed_types = getattr(settings, "RESUME_ALLOWED_TYPES", [])

        if file.size > max_size:
            return Response({"error": f"File too large (max {max_size // (1024*1024)}MB)"}, status=status.HTTP_400_BAD_REQUEST)

        if file.content_type not in allowed_types:
            return Response({"error": f"Unsupported file type: {file.content_type}"}, status=status.HTTP_400_BAD_REQUEST)

        # Determine version
        current_version = ResumeDocument.objects.filter(
            candidate=candidate, tenant_id=request.tenant_id
        ).count()

        # Save file to disk (local storage for dev; use S3 in production)
        import hashlib
        import os
        from django.conf import settings as django_settings

        file_content = file.read()

        # ClamAV virus scan before storing
        try:
            from apps.shared.clamav import scan_file
            import io as _io
            scan_result = scan_file(_io.BytesIO(file_content), filename=file.name)
            if not scan_result.is_clean:
                return Response(
                    {'error': f'File rejected: {scan_result.threat or scan_result.error or "scan error"}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as _scan_exc:
            # Only fail-open if CLAMAV_STRICT_MODE is False (DEBUG mode default)
            from django.conf import settings as _dj_settings
            import logging as _log
            strict = getattr(_dj_settings, 'CLAMAV_STRICT_MODE', not getattr(_dj_settings, 'DEBUG', False))
            if strict:
                _log.getLogger('ats.clamav').error('ClamAV scan error (rejecting): %s', _scan_exc)
                return Response({'error': 'Virus scan unavailable — upload rejected'}, status=503)
            _log.getLogger('ats.clamav').warning('ClamAV scan skipped (non-strict): %s', _scan_exc)

        file_hash = hashlib.sha256(file_content).hexdigest()
        relative_path = f"resumes/{request.tenant_id}/{candidate.id}/{file.name}"
        absolute_path = os.path.join(django_settings.MEDIA_ROOT, relative_path)

        # Ensure directory exists
        os.makedirs(os.path.dirname(absolute_path), exist_ok=True)

        # Write file to disk
        with open(absolute_path, "wb") as f:
            f.write(file_content)

        resume = ResumeDocument.objects.create(
            tenant_id=request.tenant_id,
            candidate=candidate,
            version=current_version + 1,
            file_url=relative_path,
            file_hash=file_hash,
            file_type=file.content_type,
            parse_status="pending_parse",
        )

        # Trigger parse (runs synchronously in dev via CELERY_TASK_ALWAYS_EAGER)
        try:
            from apps.parsing.tasks import parse_resume
            parse_resume.delay(str(resume.id))
        except Exception:
            pass  # task will be picked up later

        return Response(ResumeSerializer(resume).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"])
    def notes(self, request, pk=None):
        """List or add notes for a candidate."""
        candidate = self.get_object()
        if request.method == "GET":
            notes = CandidateNote.objects.filter(
                tenant_id=request.tenant_id, candidate=candidate, parent_note__isnull=True
            ).select_related("author").prefetch_related("replies")
            return Response(CandidateNoteSerializer(notes, many=True).data)
        serializer = CandidateNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant_id=request.tenant_id, candidate=candidate, author=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"])
    def certifications_list(self, request, pk=None):
        """List or add certifications for a candidate."""
        candidate = self.get_object()
        if request.method == "GET":
            certs = CandidateCertification.objects.filter(
                tenant_id=request.tenant_id, candidate=candidate
            )
            return Response(CandidateCertificationSerializer(certs, many=True).data)
        serializer = CandidateCertificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(tenant_id=request.tenant_id, candidate=candidate)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def timeline(self, request, pk=None):
        """Get chronological timeline of events for a candidate."""
        candidate = self.get_object()

        events = []

        # Applications
        try:
            from apps.applications.models import Application as _App
            for app in _App.objects.filter(
                candidate=candidate, tenant_id=request.tenant_id
            ).select_related('job', 'current_stage').order_by('created_at'):
                events.append({
                    'type': 'applied',
                    'timestamp': app.created_at.isoformat(),
                    'title': f'Applied to {app.job.title}',
                    'icon': 'document',
                })
        except Exception:
            pass

        # Stage changes
        try:
            from apps.applications.models import StageHistory as _SH
            for sh in _SH.objects.filter(
                application__candidate=candidate,
                tenant_id=request.tenant_id,
            ).select_related('to_stage', 'application__job').order_by('created_at'):
                events.append({
                    'type': 'stage_change',
                    'timestamp': sh.created_at.isoformat(),
                    'title': f'Moved to {sh.to_stage.name} ({sh.application.job.title})',
                    'icon': 'arrow',
                })
        except Exception:
            pass

        # Notes
        try:
            for note in CandidateNote.objects.filter(
                candidate=candidate, tenant_id=request.tenant_id
            ).select_related('author').order_by('created_at'):
                events.append({
                    'type': 'note',
                    'timestamp': note.created_at.isoformat(),
                    'title': f'Note added by {note.author.get_full_name() if note.author else "system"}',
                    'preview': (note.content or '')[:100],
                    'icon': 'chat',
                })
        except Exception:
            pass

        # Offers
        try:
            from apps.applications.models import Offer as _Offer
            for offer in _Offer.objects.filter(
                application__candidate=candidate,
                tenant_id=request.tenant_id,
            ).select_related('application__job').order_by('created_at'):
                events.append({
                    'type': 'offer',
                    'timestamp': offer.created_at.isoformat(),
                    'title': f'Offer {offer.status} — {offer.application.job.title}',
                    'icon': 'gift',
                })
        except Exception:
            pass

        # Sort chronologically
        events.sort(key=lambda x: x['timestamp'])

        return Response(events)

    @action(detail=False, methods=["get"], url_path="export")
    def export_csv(self, request):
        """Export all candidates in the tenant as CSV."""
        qs = self.get_queryset().prefetch_related("skills", "experiences")
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="candidates_export.csv"'
        writer = csv.writer(response)
        writer.writerow([
            "id", "full_name", "primary_email", "primary_phone",
            "most_recent_title", "location", "status", "source",
            "skills", "experience_years", "created_at",
        ])
        for candidate in qs:
            skills_str = "; ".join(s.canonical_name for s in candidate.skills.all()[:10])
            exp_oldest = candidate.experiences.order_by("start_date").first()
            exp_years = ""
            if exp_oldest and exp_oldest.start_date:
                from datetime import date
                delta = date.today() - exp_oldest.start_date
                exp_years = round(delta.days / 365, 1)
            writer.writerow([
                str(candidate.id),
                candidate.full_name,
                candidate.primary_email,
                candidate.primary_phone or "",
                candidate.most_recent_title or "",
                candidate.location or "",
                candidate.status,
                candidate.source or "",
                skills_str,
                exp_years,
                candidate.created_at.date().isoformat(),
            ])
        return response

    @action(detail=False, methods=["post"], url_path="bulk-import", parser_classes=[MultiPartParser])
    def bulk_import(self, request):
        """Import candidates from a CSV file.
        Expected columns: full_name, primary_email, primary_phone, most_recent_title, location, source
        """
        if "file" not in request.FILES:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)
        file_obj = request.FILES["file"]
        if not file_obj.name.endswith(".csv"):
            return Response({"error": "File must be a .csv"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            decoded = file_obj.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            return Response({"error": "Cannot decode file; ensure UTF-8 encoding"}, status=status.HTTP_400_BAD_REQUEST)

        reader = csv.DictReader(io.StringIO(decoded))
        if not reader.fieldnames or "primary_email" not in reader.fieldnames:
            return Response(
                {"error": "CSV must include at least: primary_email, full_name"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_count = 0
        skipped_count = 0
        errors = []

        for row_num, row in enumerate(reader, start=2):
            email = row.get("primary_email", "").strip().lower()
            full_name = row.get("full_name", "").strip()
            if not email or not full_name:
                errors.append(f"Row {row_num}: Missing primary_email or full_name — skipped")
                skipped_count += 1
                continue

            if Candidate.objects.filter(tenant_id=request.tenant_id, primary_email=email).exists():
                skipped_count += 1
                continue

            try:
                Candidate.objects.create(
                    tenant_id=request.tenant_id,
                    full_name=full_name,
                    primary_email=email,
                    primary_phone=row.get("primary_phone", "").strip() or "",
                    most_recent_title=row.get("most_recent_title", "").strip() or "",
                    location=row.get("location", "").strip() or "",
                    source=row.get("source", "import").strip() or "import",
                    status="active",
                )
                created_count += 1
            except Exception as exc:
                errors.append(f"Row {row_num}: {exc}")
                skipped_count += 1

        return Response({
            "created": created_count,
            "skipped": skipped_count,
            "errors": errors[:50],  # cap error list
        }, status=status.HTTP_201_CREATED if created_count else status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='gdpr-delete', permission_classes=[IsAdminUser])
    def gdpr_delete(self, request, pk=None):
        """Anonymize PII for GDPR data erasure request."""
        import uuid as _uuid
        candidate = self.get_object()
        anon_id = str(_uuid.uuid4())[:8]
        candidate.full_name = f'DELETED {anon_id}'
        candidate.primary_email = f'deleted-{anon_id}@gdpr.invalid'
        candidate.primary_phone = ''
        candidate.linkedin_url = ''
        candidate.github_url = ''
        candidate.portfolio_url = ''
        candidate.headline = ''
        candidate.location = ''
        candidate.status = 'deleted'
        candidate.pool_status = 'gdpr_deleted'
        candidate.save()
        return Response({'detail': 'Candidate data has been anonymized per GDPR request.'})

    @action(detail=True, methods=["post"])
    def merge(self, request, pk=None):
        """
        Merge another candidate (secondary) into this one (primary).
        POST /api/v1/candidates/{primary_id}/merge/ {secondary_id: <id>}
        """
        primary = self.get_object()
        secondary_id = request.data.get('secondary_id')

        if not secondary_id:
            return Response({'error': 'secondary_id required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            secondary = Candidate.objects.get(id=secondary_id, tenant=primary.tenant)
        except Candidate.DoesNotExist:
            return Response({'error': 'Secondary candidate not found'}, status=status.HTTP_404_NOT_FOUND)

        if str(primary.id) == str(secondary_id):
            return Response({'error': 'Cannot merge candidate with itself'}, status=status.HTTP_400_BAD_REQUEST)

        from django.db import transaction

        with transaction.atomic():
            # Reassign applications
            try:
                from apps.applications.models import Application
                Application.objects.filter(candidate=secondary).update(candidate=primary)
            except Exception:
                pass

            # Merge tags
            primary_tags = primary.tags or []
            secondary_tags = secondary.tags or []
            primary.tags = list(set(primary_tags + secondary_tags))

            # Copy notes
            try:
                CandidateNote.objects.filter(candidate=secondary).update(candidate=primary)
            except Exception:
                pass

            # Merge contact fields — fill primary gaps from secondary
            if not primary.primary_email and secondary.primary_email:
                primary.primary_email = secondary.primary_email
            if not primary.primary_phone and secondary.primary_phone:
                primary.primary_phone = secondary.primary_phone
            if not primary.linkedin_url and secondary.linkedin_url:
                primary.linkedin_url = secondary.linkedin_url
            if not primary.github_url and secondary.github_url:
                primary.github_url = secondary.github_url

            primary.save()

            # Log audit event
            try:
                from apps.shared.models import AuditLog
                AuditLog.objects.create(
                    tenant=primary.tenant,
                    user=request.user,
                    action=AuditLog.Action.UPDATE,
                    resource_type='candidate',
                    resource_id=str(primary.id),
                    changes={'merged_from': str(secondary.id)},
                )
            except Exception:
                pass

            # Soft-delete the secondary
            secondary.status = 'merged'
            secondary.redirect_to = primary
            secondary.save(update_fields=['status', 'redirect_to', 'updated_at'])

        return Response({'status': 'merged', 'primary_id': str(primary.id)})

    @action(detail=True, methods=["post"])
    def compare(self, request, pk=None):
        """Compare this candidate with others (pass candidate_ids in body)."""
        candidate = self.get_object()
        other_ids = request.data.get("candidate_ids", [])
        candidates = Candidate.objects.filter(
            id__in=[pk] + other_ids, tenant_id=request.tenant_id
        ).prefetch_related("skills", "experiences")
        return Response(CandidateSerializer(candidates, many=True).data)


# ── URLs ─────────────────────────────────────────────────────────────────────

router = DefaultRouter()
router.register("", CandidateViewSet, basename="candidates")

urlpatterns = [
    path("", include(router.urls)),
]
