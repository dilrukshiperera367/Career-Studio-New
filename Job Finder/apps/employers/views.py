"""Employers views — Company CRUD, team management, branding."""
from django.utils.text import slugify
from django.db.models import Avg
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.shared.permissions import IsEmployer
from .models import EmployerAccount, EmployerTeamMember, EmployerBranding, EmployerFollow, SalaryReport
from .serializers import (
    EmployerAccountSerializer, EmployerAccountCreateSerializer,
    EmployerListSerializer, EmployerTeamMemberSerializer,
    TeamMemberInviteSerializer, EmployerBrandingSerializer,
    EmployerFollowSerializer, SalaryReportSerializer,
)


class EmployerListView(generics.ListAPIView):
    """Public list of all employers (company directory)."""
    serializer_class = EmployerListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = EmployerAccount.objects.all()
        industry = self.request.query_params.get("industry")
        if industry:
            qs = qs.filter(industry_id=industry)
        district = self.request.query_params.get("district")
        if district:
            qs = qs.filter(headquarters_id=district)
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(company_name__icontains=search)
        return qs.order_by("-created_at")


class EmployerDetailView(generics.RetrieveAPIView):
    """Public company profile page."""
    serializer_class = EmployerAccountSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"
    queryset = EmployerAccount.objects.select_related("branding", "industry", "headquarters")


class EmployerCreateView(generics.CreateAPIView):
    """Create employer account (authenticated employer users)."""
    serializer_class = EmployerAccountCreateSerializer
    permission_classes = [permissions.IsAuthenticated, IsEmployer]

    def perform_create(self, serializer):
        name = serializer.validated_data["company_name"]
        slug = slugify(name)
        base_slug = slug
        counter = 1
        while EmployerAccount.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        employer = serializer.save(slug=slug)
        EmployerTeamMember.objects.create(
            employer=employer, user=self.request.user, role="owner",
        )
        EmployerBranding.objects.create(employer=employer)


class EmployerUpdateView(generics.UpdateAPIView):
    """Update own employer profile."""
    serializer_class = EmployerAccountSerializer
    permission_classes = [permissions.IsAuthenticated, IsEmployer]

    def get_object(self):
        membership = EmployerTeamMember.objects.filter(
            user=self.request.user, role__in=["owner", "admin"],
        ).first()
        if not membership:
            self.permission_denied(self.request)
        return membership.employer


# ── Team Management ───────────────────────────────────────────────────────

class TeamListView(generics.ListAPIView):
    serializer_class = EmployerTeamMemberSerializer
    permission_classes = [permissions.IsAuthenticated, IsEmployer]

    def get_queryset(self):
        membership = EmployerTeamMember.objects.filter(user=self.request.user).first()
        if membership:
            return EmployerTeamMember.objects.filter(employer=membership.employer).select_related("user")
        return EmployerTeamMember.objects.none()


class TeamInviteView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsEmployer]

    def post(self, request):
        serializer = TeamMemberInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = EmployerTeamMember.objects.filter(
            user=request.user, role__in=["owner", "admin"],
        ).first()
        if not membership:
            return Response({"detail": "Only owners/admins can invite."}, status=status.HTTP_403_FORBIDDEN)
        # TODO: send invite email, create pending membership
        return Response({"detail": "Invitation sent."}, status=status.HTTP_201_CREATED)


class TeamMemberRemoveView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsEmployer]

    def delete(self, request, pk):
        membership = EmployerTeamMember.objects.filter(
            user=request.user, role__in=["owner", "admin"],
        ).first()
        if not membership:
            return Response({"detail": "Not authorized."}, status=status.HTTP_403_FORBIDDEN)
        deleted, _ = EmployerTeamMember.objects.filter(
            employer=membership.employer, pk=pk,
        ).exclude(role="owner").delete()
        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({"detail": "Not found or cannot remove owner."}, status=status.HTTP_404_NOT_FOUND)


# ── Branding ──────────────────────────────────────────────────────────────

class BrandingView(generics.RetrieveUpdateAPIView):
    serializer_class = EmployerBrandingSerializer
    permission_classes = [permissions.IsAuthenticated, IsEmployer]

    def get_object(self):
        membership = EmployerTeamMember.objects.filter(
            user=self.request.user, role__in=["owner", "admin"],
        ).first()
        if not membership:
            self.permission_denied(self.request)
        branding, _ = EmployerBranding.objects.get_or_create(employer=membership.employer)
        return branding


# ── Company Follow (#366-368) ──────────────────────────────────────────────

class CompanyFollowToggleView(APIView):
    """Toggle follow/unfollow a company."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, slug):
        try:
            employer = EmployerAccount.objects.get(slug=slug)
        except EmployerAccount.DoesNotExist:
            return Response({"detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

        follow, created = EmployerFollow.objects.get_or_create(employer=employer, user=request.user)
        if not created:
            follow.delete()
            following = False
            employer.follower_count = max(0, employer.follower_count - 1)
        else:
            following = True
            employer.follower_count += 1
        employer.save(update_fields=["follower_count"])
        return Response({"following": following, "follower_count": employer.follower_count})


class IsFollowingView(APIView):
    """Check if the current user follows a company."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, slug):
        following = EmployerFollow.objects.filter(
            employer__slug=slug, user=request.user,
        ).exists()
        return Response({"following": following})


class FollowedCompaniesView(generics.ListAPIView):
    """List all companies followed by the current user (#367)."""
    serializer_class = EmployerFollowSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            EmployerFollow.objects.filter(user=self.request.user)
            .select_related("employer", "employer__industry", "employer__headquarters")
            .order_by("-created_at")
        )


# ── Salary Reports (#388-390) ──────────────────────────────────────────────

class SalaryReportListView(generics.ListAPIView):
    """Aggregated salary data for a company (public)."""
    serializer_class = SalaryReportSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return SalaryReport.objects.filter(
            employer__slug=self.kwargs["slug"],
        ).order_by("job_title")


class SalaryReportCreateView(generics.CreateAPIView):
    """Submit an anonymous salary report."""
    serializer_class = SalaryReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        employer = EmployerAccount.objects.get(slug=self.kwargs["slug"])
        serializer.save(employer=employer, submitted_by=self.request.user)
