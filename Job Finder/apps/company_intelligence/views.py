"""Company Intelligence — views."""
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.employers.models import EmployerAccount
from .models import (
    CompanyOfficeLocation, CompanyBenefit, CompanyQnA,
    HiringActivityIndicator, EmployerComparison,
)
from .serializers import (
    CompanyOfficeLocationSerializer, CompanyBenefitSerializer,
    CompanyQnASerializer, CompanyQnACreateSerializer, HiringActivitySerializer,
)


def _get_employer_or_404(slug):
    try:
        return EmployerAccount.objects.get(slug=slug)
    except EmployerAccount.DoesNotExist:
        return None


class CompanyOfficeLocationsView(APIView):
    """List office locations for a company."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        employer = _get_employer_or_404(slug)
        if not employer:
            return Response({"detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)
        offices = CompanyOfficeLocation.objects.filter(employer=employer).select_related("district")
        return Response(CompanyOfficeLocationSerializer(offices, many=True, context={"request": request}).data)


class CompanyBenefitsView(APIView):
    """List structured benefits for a company."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        employer = _get_employer_or_404(slug)
        if not employer:
            return Response({"detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)
        benefits = CompanyBenefit.objects.filter(employer=employer)
        return Response(CompanyBenefitSerializer(benefits, many=True).data)


class CompanyQnAView(APIView):
    """Get and post community Q&A for a company."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        employer = _get_employer_or_404(slug)
        if not employer:
            return Response({"detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)
        qna = CompanyQnA.objects.filter(employer=employer, status="approved")
        return Response(CompanyQnASerializer(qna, many=True).data)

    def post(self, request, slug):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)
        employer = _get_employer_or_404(slug)
        if not employer:
            return Response({"detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)
        ser = CompanyQnACreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        qna = CompanyQnA.objects.create(
            employer=employer,
            asked_by=request.user,
            question=ser.validated_data["question"],
            status="pending",
        )
        return Response(CompanyQnASerializer(qna).data, status=status.HTTP_201_CREATED)


class HiringActivityView(APIView):
    """Hiring activity signals for a company (last 8 weeks)."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        employer = _get_employer_or_404(slug)
        if not employer:
            return Response({"detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)
        activity = HiringActivityIndicator.objects.filter(employer=employer)[:8]
        return Response(HiringActivitySerializer(activity, many=True).data)


class SimilarCompaniesView(APIView):
    """Similar companies for a given company slug."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        employer = _get_employer_or_404(slug)
        if not employer:
            return Response({"detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)
        # Similarity by industry + size
        similar = EmployerAccount.objects.filter(
            industry=employer.industry, company_size=employer.company_size,
        ).exclude(id=employer.id).order_by("-avg_rating")[:6]
        from apps.employers.serializers import EmployerListSerializer
        return Response(EmployerListSerializer(similar, many=True, context={"request": request}).data)


class CompanyCompareView(APIView):
    """Compare two companies side by side."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        compare_slug = request.query_params.get("vs")
        employer_a = _get_employer_or_404(slug)
        employer_b = _get_employer_or_404(compare_slug) if compare_slug else None
        if not employer_a or not employer_b:
            return Response({"detail": "One or both companies not found."}, status=status.HTTP_404_NOT_FOUND)

        from apps.employers.serializers import EmployerDetailSerializer
        return Response({
            "company_a": EmployerDetailSerializer(employer_a, context={"request": request}).data,
            "company_b": EmployerDetailSerializer(employer_b, context={"request": request}).data,
            "comparison_fields": ["avg_rating", "review_count", "active_job_count",
                                   "company_size", "founded_year", "is_verified"],
        })
