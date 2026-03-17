"""Jobs views — CRUD for job listings, saved jobs, public browse, report, similar.
Features #86–135, #136–170.
"""
from django.core.cache import cache
from django.db.models import Q, F
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import generics, permissions, status, filters
from rest_framework.decorators import api_view, permission_classes as perm_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.shared.permissions import IsEmployer
from apps.employers.models import EmployerTeamMember
from .models import JobListing, SavedJob, JobView
from .serializers import (
    JobDetailSerializer, JobListingSerializer, JobListSerializer, JobCreateSerializer,
    SavedJobSerializer, ReportJobSerializer,
)


# ── Public Browse & Detail ────────────────────────────────────────────────

class JobListView(generics.ListAPIView):
    """Public job listing browse with filters."""
    serializer_class = JobListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = JobListing.objects.filter(
            status="active", published_at__isnull=False,
        ).select_related("employer", "district", "category")

        # Filters
        params = self.request.query_params
        if q := params.get("q"):
            qs = qs.filter(
                Q(title__icontains=q) | Q(title_si__icontains=q) |
                Q(title_ta__icontains=q) | Q(description__icontains=q)
            )
        if cat := params.get("category"):
            qs = qs.filter(category_id=cat)
        if district := params.get("district"):
            qs = qs.filter(district_id=district)
        if province := params.get("province"):
            qs = qs.filter(province_id=province)
        if jt := params.get("job_type"):
            qs = qs.filter(job_type=jt)
        if el := params.get("experience_level"):
            qs = qs.filter(experience_level=el)
        if wa := params.get("work_arrangement"):
            qs = qs.filter(work_arrangement=wa)
        if smin := params.get("salary_min"):
            qs = qs.filter(salary_max__gte=smin)
        if smax := params.get("salary_max"):
            qs = qs.filter(salary_min__lte=smax)
        if employer := params.get("employer"):
            qs = qs.filter(employer_id=employer)

        # Sort
        sort = params.get("sort", "date")
        if sort == "salary_desc":
            qs = qs.order_by("-salary_max")
        elif sort == "salary_asc":
            qs = qs.order_by("salary_min")
        else:
            qs = qs.order_by("-is_featured", "-is_boosted", "-published_at")

        return qs


class JobDetailView(generics.RetrieveAPIView):
    """Public job detail by slug — returns full JobDetailSerializer payload."""
    serializer_class = JobDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"

    def get_queryset(self):
        return JobListing.objects.select_related(
            "employer", "employer__industry", "employer__headquarters",
            "district", "province", "category", "subcategory",
            "industry", "min_education", "posted_by",
        ).prefetch_related("required_skills", "preferred_skills")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        # Track view
        JobView.objects.create(
            job=instance,
            user=request.user if request.user.is_authenticated else None,
            ip_address=request.META.get("REMOTE_ADDR"),
            referrer=request.META.get("HTTP_REFERER", "")[:500],
        )
        JobListing.objects.filter(pk=instance.pk).update(view_count=F("view_count") + 1)
        instance.refresh_from_db()

        # Build match context from seeker profile
        match_context = {
            "match_score": None,
            "matching_skills": [],
            "missing_skills": [],
        }
        already_applied = False
        is_saved = False

        if request.user.is_authenticated:
            from apps.applications.models import Application
            from apps.candidates.models import SeekerProfile

            # Applied / saved checks
            try:
                profile = SeekerProfile.objects.get(user=request.user)
                seeker_obj = profile
                already_applied = Application.objects.filter(
                    job=instance, seeker=seeker_obj
                ).exists()

                # Skill match
                profile_skills = set(
                    s.name_en for s in getattr(profile, "skills", []) or []
                )
                # Fallback: try getting skills via related manager
                try:
                    from apps.taxonomy.models import Skill
                    profile_skills = set(
                        s.name_en for s in profile.skills.all()
                    )
                except Exception:
                    pass

                job_skills = set(s.name_en for s in instance.required_skills.all())
                matching = list(profile_skills & job_skills)
                missing = list(job_skills - profile_skills)
                match_score = round(len(matching) / max(len(job_skills), 1) * 100) if job_skills else None

                match_context = {
                    "match_score": match_score,
                    "matching_skills": matching,
                    "missing_skills": missing[:8],
                }
            except SeekerProfile.DoesNotExist:
                pass

            is_saved = SavedJob.objects.filter(user=request.user, job=instance).exists()

        serializer = JobDetailSerializer(
            instance,
            context={"request": request, **match_context},
        )
        data = serializer.data
        data["already_applied"] = already_applied
        data["is_saved"] = is_saved
        return Response(data)


class FeaturedJobsView(generics.ListAPIView):
    """Featured / promoted jobs for homepage."""
    serializer_class = JobListSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        return JobListing.objects.filter(
            status="active", is_featured=True, featured_until__gte=timezone.now(),
        ).select_related("employer", "district", "category").order_by("-boost_factor", "-published_at")[:12]


class LatestJobsView(generics.ListAPIView):
    """Latest published jobs for homepage."""
    serializer_class = JobListSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        return JobListing.objects.filter(
            status="active",
        ).select_related("employer", "district", "category").order_by("-published_at")[:20]


# ── Employer Job Management ──────────────────────────────────────────────

class EmployerJobListView(generics.ListCreateAPIView):
    """List/create jobs for the authenticated employer."""
    permission_classes = [permissions.IsAuthenticated, IsEmployer]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return JobCreateSerializer
        return JobListSerializer

    def get_queryset(self):
        membership = EmployerTeamMember.objects.filter(user=self.request.user).first()
        if membership:
            return JobListing.objects.filter(employer=membership.employer).order_by("-created_at")
        return JobListing.objects.none()

    def perform_create(self, serializer):
        membership = EmployerTeamMember.objects.filter(user=self.request.user).first()
        title = serializer.validated_data["title"]
        slug = slugify(title)
        base_slug = slug
        counter = 1
        while JobListing.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        serializer.save(
            employer=membership.employer,
            posted_by=self.request.user,
            slug=slug,
        )


class EmployerJobDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Employer manage a specific job."""
    serializer_class = JobListingSerializer
    permission_classes = [permissions.IsAuthenticated, IsEmployer]

    def get_queryset(self):
        membership = EmployerTeamMember.objects.filter(user=self.request.user).first()
        if membership:
            return JobListing.objects.filter(employer=membership.employer)
        return JobListing.objects.none()


class JobPublishView(APIView):
    """Publish a draft job."""
    permission_classes = [permissions.IsAuthenticated, IsEmployer]

    def post(self, request, pk):
        membership = EmployerTeamMember.objects.filter(user=request.user).first()
        if not membership:
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            job = JobListing.objects.get(pk=pk, employer=membership.employer)
        except JobListing.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        job.status = "active"
        job.published_at = timezone.now()
        if not job.expires_at:
            job.expires_at = timezone.now() + timezone.timedelta(days=30)
        job.save(update_fields=["status", "published_at", "expires_at"])
        membership.employer.active_job_count = JobListing.objects.filter(
            employer=membership.employer, status="active",
        ).count()
        membership.employer.save(update_fields=["active_job_count"])
        return Response({"detail": "Job published."})


class JobCloseView(APIView):
    """Close an active job."""
    permission_classes = [permissions.IsAuthenticated, IsEmployer]

    def post(self, request, pk):
        membership = EmployerTeamMember.objects.filter(user=request.user).first()
        if not membership:
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            job = JobListing.objects.get(pk=pk, employer=membership.employer)
        except JobListing.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        job.status = "closed"
        job.closed_at = timezone.now()
        job.save(update_fields=["status", "closed_at"])
        return Response({"detail": "Job closed."})


# ── Saved Jobs ────────────────────────────────────────────────────────────

class SavedJobListView(generics.ListAPIView):
    serializer_class = SavedJobSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SavedJob.objects.filter(user=self.request.user).select_related("job__employer")


class SavedJobToggleView(APIView):
    """Toggle save/unsave a job."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        saved, created = SavedJob.objects.get_or_create(user=request.user, job_id=pk)
        if not created:
            saved.delete()
            return Response({"saved": False})
        return Response({"saved": True}, status=status.HTTP_201_CREATED)


# ── Similar Jobs ──────────────────────────────────────────────────────────

class SimilarJobsView(generics.ListAPIView):
    """Jobs similar to a given job — same category, district, or skills (#130, #162)."""
    serializer_class = JobListSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        try:
            job = JobListing.objects.get(pk=self.kwargs["pk"])
        except JobListing.DoesNotExist:
            return JobListing.objects.none()
        skill_ids = job.required_skills.values_list("id", flat=True)
        return JobListing.objects.filter(
            status="active",
        ).filter(
            Q(category=job.category) | Q(district=job.district) | Q(required_skills__id__in=skill_ids)
        ).exclude(pk=job.pk).distinct().order_by("-published_at")[:6]


class OtherCompanyJobsView(generics.ListAPIView):
    """Other active jobs from the same company (#161)."""
    serializer_class = JobListSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        try:
            job = JobListing.objects.get(pk=self.kwargs["pk"])
        except JobListing.DoesNotExist:
            return JobListing.objects.none()
        return JobListing.objects.filter(
            status="active", employer=job.employer,
        ).exclude(pk=job.pk).order_by("-published_at")[:5]


class ReportJobView(APIView):
    """Report a job listing (#159)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        serializer = ReportJobSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from apps.moderation.models import Report
        Report.objects.create(
            reporter=request.user,
            content_type="job_listing",
            content_id=str(pk),
            reason=serializer.validated_data["reason"],
            description=serializer.validated_data.get("description", ""),
        )
        return Response({"detail": "Report submitted. Thank you."}, status=status.HTTP_201_CREATED)


class JobStatsView(APIView):
    """Public platform statistics (#67)."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        cache_key = "platform_job_stats"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        from apps.employers.models import EmployerAccount
        from apps.accounts.models import User
        stats = {
            "active_jobs": JobListing.objects.filter(status="active").count(),
            "total_companies": EmployerAccount.objects.count(),
            "total_seekers": User.objects.filter(user_type="seeker").count(),
        }
        cache.set(cache_key, stats, 300)
        return Response(stats)
