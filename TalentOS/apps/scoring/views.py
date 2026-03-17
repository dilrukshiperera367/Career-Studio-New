"""Views for the scoring app — Company batch scoring + Candidate personal scoring."""

import io
import csv
import zipfile
import logging
from django.http import HttpResponse
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.accounts.permissions import IsInterviewer, IsRecruiter

from apps.scoring.models import (
    JobScoreBatch, BatchItem, BatchItemScore,
    CandidateProfile, CandidateResumeVersion, CandidateScoreRun,
)
from apps.scoring.serializers import (
    JobScoreBatchListSerializer, JobScoreBatchDetailSerializer,
    CreateBatchSerializer, BatchItemSerializer,
    CandidateProfileSerializer, CandidateResumeVersionSerializer,
    CandidateScoreRunListSerializer, CandidateScoreRunDetailSerializer,
)
from apps.scoring.jd_parser import parse_jd, build_taxonomy_lookup
from apps.scoring.scorer import compute_score

logger = logging.getLogger(__name__)


# ===========================================================================
# Permission helpers
# ===========================================================================

class IsCompanyUser(permissions.BasePermission):
    """Only company users (admin, recruiter, hiring_manager)."""
    def has_permission(self, request, view):
        return request.user.user_type in ("company_admin", "recruiter", "hiring_manager")


class IsCandidateUser(permissions.BasePermission):
    """Only candidate users."""
    def has_permission(self, request, view):
        return request.user.user_type == "candidate"


# ===========================================================================
# COMPANY — Batch Scoring
# ===========================================================================

class BatchListCreateView(generics.ListCreateAPIView):
    """List all batches or create a new one."""
    permission_classes = [IsAuthenticated, IsRecruiter]
    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CreateBatchSerializer
        return JobScoreBatchListSerializer

    def get_queryset(self):
        return JobScoreBatch.objects.filter(tenant_id=self.request.user.tenant_id)

    def create(self, request, *args, **kwargs):
        jd_text = request.data.get("jd_text", "")
        job_title = request.data.get("job_title", "")
        scoring_weights = {}

        # If JD is uploaded as file
        jd_file = request.FILES.get("jd_file")
        if jd_file and not jd_text:
            jd_text = self._extract_jd_text(jd_file)

        if not jd_text:
            return Response(
                {"error": "Job description text is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Parse JD
        taxonomy = build_taxonomy_lookup()
        jd_requirements = parse_jd(jd_text, taxonomy)

        # Create batch
        batch = JobScoreBatch.objects.create(
            tenant_id=request.user.tenant_id,
            job_title=job_title,
            jd_text=jd_text,
            jd_requirements_json=jd_requirements,
            scoring_weights=scoring_weights,
            created_by=request.user,
            status="created",
        )

        # Handle CV uploads
        files = request.FILES.getlist("files")
        items_created = 0

        for f in files:
            file_name = f.name
            file_type = "docx" if file_name.endswith(".docx") else "pdf"

            # Handle ZIP files
            if file_name.endswith(".zip"):
                items_created += self._process_zip(batch, f)
                continue

            from django.core.files.base import ContentFile
            content = f.read()
            item = BatchItem(
                batch=batch,
                tenant_id=request.user.tenant_id,
                file_name=file_name,
                file_type=file_type,
            )
            item.file.save(file_name, ContentFile(content), save=False)
            item.file_hash = __import__('hashlib').sha256(content).hexdigest()
            item.save()
            items_created += 1

        batch.total_items = items_created
        batch.save(update_fields=["total_items"])

        # Dedup within batch
        self._dedup_batch(batch)

        # Process: use sync for local dev, async for production
        self._start_processing(batch)

        return Response(
            JobScoreBatchDetailSerializer(batch).data,
            status=status.HTTP_201_CREATED,
        )

    def _extract_jd_text(self, jd_file):
        """Extract text from a JD file."""
        try:
            from apps.parsing.services import extract_text
            content = jd_file.read()
            file_type = "docx" if jd_file.name.endswith(".docx") else "pdf"
            text = extract_text(content, file_type)
            return text
        except Exception as exc:
            logger.error(f"Failed to extract JD text: {exc}")
            return ""

    def _process_zip(self, batch, zip_file):
        """Extract and create items from a ZIP file."""
        count = 0
        try:
            with zipfile.ZipFile(io.BytesIO(zip_file.read())) as zf:
                for name in zf.namelist():
                    if name.startswith("__") or name.startswith("."):
                        continue
                    if not (name.endswith(".pdf") or name.endswith(".docx")):
                        continue
                    content = zf.read(name)
                    file_type = "docx" if name.endswith(".docx") else "pdf"
                    from django.core.files.base import ContentFile
                    item = BatchItem(
                        batch=batch,
                        tenant_id=batch.tenant_id,
                        file_name=name.split("/")[-1],
                        file_type=file_type,
                    )
                    item.file.save(name.split("/")[-1], ContentFile(content), save=False)
                    item.file_hash = __import__('hashlib').sha256(content).hexdigest()
                    item.save()
                    count += 1
        except Exception as exc:
            logger.error(f"Failed to process ZIP: {exc}")
        return count

    def _dedup_batch(self, batch):
        """Mark duplicate files within a batch."""
        seen_hashes = set()
        for item in batch.items.order_by("created_at"):
            if item.file_hash and item.file_hash in seen_hashes:
                item.status = "duplicate"
                item.error_message = "Duplicate file detected"
                item.save(update_fields=["status", "error_message"])
            elif item.file_hash:
                seen_hashes.add(item.file_hash)

    def _start_processing(self, batch):
        """Start batch processing — sync or async."""
        from django.conf import settings
        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            # Sync mode
            from apps.scoring.tasks import process_batch_sync
            process_batch_sync(str(batch.id))
        else:
            try:
                from apps.scoring.tasks import process_batch
                process_batch.delay(str(batch.id))
            except Exception:
                # Fallback to sync
                from apps.scoring.tasks import process_batch_sync
                process_batch_sync(str(batch.id))


class BatchDetailView(generics.RetrieveAPIView):
    """Get batch detail with all items."""
    permission_classes = [IsAuthenticated, IsInterviewer]
    serializer_class = JobScoreBatchDetailSerializer

    def get_queryset(self):
        return JobScoreBatch.objects.filter(tenant_id=self.request.user.tenant_id)


class BatchResultsView(generics.ListAPIView):
    """Get ranked results for a batch."""
    permission_classes = [IsAuthenticated, IsInterviewer]
    serializer_class = BatchItemSerializer

    def get_queryset(self):
        batch_id = self.kwargs["pk"]
        return (
            BatchItem.objects
            .filter(batch_id=batch_id, batch__tenant_id=self.request.user.tenant_id)
            .exclude(status__in=["duplicate", "failed"])
            .select_related("score")
            .order_by("-score__score_total")
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsRecruiter])
def batch_export_csv(request, pk):
    """Export batch results as CSV."""
    batch = JobScoreBatch.objects.filter(
        id=pk, tenant_id=request.user.tenant_id,
    ).first()
    if not batch:
        return Response({"error": "Batch not found"}, status=404)

    items = (
        BatchItem.objects
        .filter(batch=batch)
        .exclude(status__in=["duplicate"])
        .select_related("score")
        .order_by("-score__score_total")
    )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="batch_{pk}_results.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "Rank", "File Name", "Candidate Name", "Email",
        "ATS Score", "Content", "Title", "Experience", "Recency", "Format",
        "Status", "Matched Skills", "Missing Skills",
    ])

    for rank, item in enumerate(items, 1):
        score = getattr(item, "score", None)
        breakdown = score.breakdown_json if score else {}
        matched = ", ".join(s.get("name", "") for s in breakdown.get("matched_required", []))
        missing = ", ".join(s.get("name", "") for s in breakdown.get("missing_required", []))

        writer.writerow([
            rank,
            item.file_name,
            item.candidate_name,
            item.candidate_email,
            score.score_total if score else "N/A",
            f"{score.content_score:.2f}" if score else "",
            f"{score.title_score:.2f}" if score else "",
            f"{score.experience_score:.2f}" if score else "",
            f"{score.recency_score:.2f}" if score else "",
            f"{score.format_score:.2f}" if score else "",
            item.status,
            matched,
            missing,
        ])

    return response


# ===========================================================================
# CANDIDATE — Personal Scoring
# ===========================================================================

class CandidateScoreView(generics.CreateAPIView):
    """Upload CV + JD → compute score."""
    permission_classes = [IsAuthenticated, IsCandidateUser]
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request, *args, **kwargs):
        jd_text = request.data.get("jd_text", "")
        jd_title = request.data.get("jd_title", "")
        cv_file = request.FILES.get("cv_file")
        resume_version_id = request.data.get("resume_version_id")

        # Get JD text from file if needed
        jd_file = request.FILES.get("jd_file")
        if jd_file and not jd_text:
            try:
                from apps.parsing.services import extract_text
                content = jd_file.read()
                ftype = "docx" if jd_file.name.endswith(".docx") else "pdf"
                jd_text = extract_text(content, ftype)
            except Exception:
                pass

        if not jd_text:
            return Response(
                {"error": "Job description text is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get or parse CV
        taxonomy = build_taxonomy_lookup()
        resume_version = None

        if cv_file:
            file_content = cv_file.read()
            file_type = "docx" if cv_file.name.endswith(".docx") else "pdf"

            # Parse CV
            from apps.parsing.services import parse_resume_full
            parsed = parse_resume_full(file_content, file_type, taxonomy)
            raw_text = parsed.get("raw_text", "")

            # Save as resume version
            resume_version = CandidateResumeVersion.objects.create(
                user=request.user,
                file_name=cv_file.name,
                file_content=file_content,
                file_type=file_type,
                raw_text=raw_text,
                parsed_json=parsed,
            )
        elif resume_version_id:
            try:
                resume_version = CandidateResumeVersion.objects.get(
                    id=resume_version_id, user=request.user,
                )
                parsed = resume_version.parsed_json
                raw_text = resume_version.raw_text
                file_type = resume_version.file_type
            except CandidateResumeVersion.DoesNotExist:
                return Response(
                    {"error": "Resume version not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            return Response(
                {"error": "Either cv_file or resume_version_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Parse JD
        jd_requirements = parse_jd(jd_text, taxonomy)

        # Extract inner parsed_json for scorer (parser returns {raw_text, clean_text, parsed_json})
        cv_signals = parsed.get("parsed_json", parsed)

        # Compute score
        result = compute_score(
            cv_parsed=cv_signals,
            jd_requirements=jd_requirements,
            file_type=file_type,
            raw_text=raw_text,
            jd_target_title=jd_title,
        )

        # Save score run
        score_run = CandidateScoreRun.objects.create(
            user=request.user,
            resume_version=resume_version,
            jd_text=jd_text,
            jd_title=jd_title,
            jd_requirements_json=jd_requirements,
            score_total=result["score_total"],
            content_score=result["content_score"],
            title_score=result["title_score"],
            experience_score=result["experience_score"],
            recency_score=result["recency_score"],
            format_score=result["format_score"],
            breakdown_json=result["breakdown"],
        )

        return Response(
            CandidateScoreRunDetailSerializer(score_run).data,
            status=status.HTTP_201_CREATED,
        )


class CandidateScoreListView(generics.ListAPIView):
    """List past score runs."""
    permission_classes = [IsAuthenticated, IsCandidateUser]
    serializer_class = CandidateScoreRunListSerializer

    def get_queryset(self):
        return CandidateScoreRun.objects.filter(user=self.request.user)


class CandidateScoreDetailView(generics.RetrieveAPIView):
    """Get a specific score run detail."""
    permission_classes = [IsAuthenticated, IsCandidateUser]
    serializer_class = CandidateScoreRunDetailSerializer

    def get_queryset(self):
        return CandidateScoreRun.objects.filter(user=self.request.user)


class CandidateResumeListCreateView(generics.ListCreateAPIView):
    """List or upload resume versions."""
    permission_classes = [IsAuthenticated, IsCandidateUser]
    serializer_class = CandidateResumeVersionSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return CandidateResumeVersion.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        cv_file = request.FILES.get("cv_file")
        if not cv_file:
            return Response(
                {"error": "cv_file is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file_content = cv_file.read()
        file_type = "docx" if cv_file.name.endswith(".docx") else "pdf"

        # Parse
        taxonomy = build_taxonomy_lookup()
        from apps.parsing.services import parse_resume_full
        parsed = parse_resume_full(file_content, file_type, taxonomy)

        version = CandidateResumeVersion.objects.create(
            user=request.user,
            file_name=cv_file.name,
            file_content=file_content,
            file_type=file_type,
            raw_text=parsed.get("raw_text", ""),
            parsed_json=parsed,
            version_label=request.data.get("version_label", ""),
        )

        return Response(
            CandidateResumeVersionSerializer(version).data,
            status=status.HTTP_201_CREATED,
        )
