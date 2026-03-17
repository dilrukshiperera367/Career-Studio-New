"""Reviews views — Company reviews CRUD."""
from django.db.models import Avg, Count
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.shared.permissions import IsEmployer
from apps.employers.models import EmployerTeamMember
from .models import CompanyReview, ReviewHelpful, EmployerReviewResponse
from .serializers import CompanyReviewSerializer, CompanyReviewCreateSerializer, EmployerResponseSerializer


class CompanyReviewListView(generics.ListAPIView):
    """Public reviews for a specific employer with filter support."""
    serializer_class = CompanyReviewSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = CompanyReview.objects.filter(
            employer_id=self.kwargs["employer_id"], status="approved",
        ).select_related("reviewer", "employer_response")

        relationship = self.request.query_params.get("relationship")
        if relationship:
            qs = qs.filter(relationship=relationship)

        sort = self.request.query_params.get("sort", "recent")
        if sort == "helpful":
            qs = qs.order_by("-helpful_count")
        elif sort == "rating_high":
            qs = qs.order_by("-overall_rating")
        elif sort == "rating_low":
            qs = qs.order_by("overall_rating")
        else:
            qs = qs.order_by("-created_at")

        return qs

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx


class CompanyReviewStatsView(APIView):
    """Aggregated rating stats for a company. #311"""
    permission_classes = [permissions.AllowAny]

    def get(self, request, employer_id):
        qs = CompanyReview.objects.filter(employer_id=employer_id, status="approved")
        stats = qs.aggregate(
            avg_overall=Avg("overall_rating"),
            avg_work_life=Avg("work_life_balance"),
            avg_career=Avg("career_growth"),
            avg_compensation=Avg("compensation"),
            avg_management=Avg("management"),
            avg_culture=Avg("culture"),
            total=Count("id"),
        )
        # Rating distribution (1-5)
        distribution = {}
        for r in range(1, 6):
            distribution[str(r)] = qs.filter(overall_rating=r).count()

        # Relationship breakdown
        by_relationship = list(qs.values("relationship").annotate(count=Count("id")).order_by("-count"))

        return Response({
            **stats,
            "rating_distribution": distribution,
            "by_relationship": by_relationship,
        })


class CompanyReviewCreateView(generics.CreateAPIView):
    serializer_class = CompanyReviewCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(reviewer=self.request.user)


class ReviewHelpfulToggleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        helpful, created = ReviewHelpful.objects.get_or_create(review_id=pk, user=request.user)
        review = CompanyReview.objects.get(pk=pk)
        if not created:
            helpful.delete()
            review.helpful_count = max(0, review.helpful_count - 1)
            review.save(update_fields=["helpful_count"])
            return Response({"helpful": False})
        review.helpful_count += 1
        review.save(update_fields=["helpful_count"])
        return Response({"helpful": True})


class EmployerReviewResponseView(APIView):
    """Employer responds to a review. #316"""
    permission_classes = [permissions.IsAuthenticated, IsEmployer]

    def post(self, request, pk):
        membership = EmployerTeamMember.objects.filter(user=request.user).first()
        if not membership:
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            review = CompanyReview.objects.get(pk=pk, employer=membership.employer)
        except CompanyReview.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Update or create response
        resp, _ = EmployerReviewResponse.objects.get_or_create(review=review, defaults={"responder": request.user})
        serializer = EmployerResponseSerializer(resp, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(responder=request.user)
        return Response(serializer.data)


class MyReviewView(generics.RetrieveUpdateDestroyAPIView):
    """Seeker's own review — retrieve, edit, or delete."""
    serializer_class = CompanyReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CompanyReview.objects.filter(reviewer=self.request.user)
