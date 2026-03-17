"""Salary Intelligence — views."""
from django.core.cache import cache
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SalaryEstimate, SalaryBenchmark, SalaryTrend, SalarySubmission, CostOfLivingIndex
from .serializers import (
    SalaryEstimateSerializer, SalaryBenchmarkSerializer,
    SalaryTrendSerializer, SalarySubmissionSerializer,
)


class SalaryEstimateView(APIView):
    """Get salary estimate for a title + optional location."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        title = request.query_params.get("title", "").strip()
        district_id = request.query_params.get("district")
        level = request.query_params.get("level", "")
        if not title:
            return Response({"detail": "title is required."}, status=status.HTTP_400_BAD_REQUEST)

        qs = SalaryEstimate.objects.filter(normalized_title__icontains=title)
        if district_id:
            qs = qs.filter(district_id=district_id)
        if level:
            qs = qs.filter(experience_level=level)

        estimate = qs.order_by("-sample_size").first()
        if not estimate:
            return Response({"detail": "No salary data found for this role."}, status=status.HTTP_404_NOT_FOUND)
        return Response(SalaryEstimateSerializer(estimate).data)


class SalaryBenchmarkView(APIView):
    """Compare a user's salary to market data."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        title = request.data.get("title", "").strip()
        district_id = request.data.get("district")
        user_salary = request.data.get("user_salary")
        if not title or not user_salary:
            return Response({"detail": "title and user_salary are required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user_salary = int(user_salary)
        except (ValueError, TypeError):
            return Response({"detail": "Invalid salary."}, status=status.HTTP_400_BAD_REQUEST)

        estimate = SalaryEstimate.objects.filter(normalized_title__icontains=title)
        if district_id:
            estimate = estimate.filter(district_id=district_id)
        estimate = estimate.order_by("-sample_size").first()

        market_median = estimate.salary_median_lkr if estimate else None
        percentile = None
        if market_median:
            # Simplified percentile approximation
            if user_salary >= (estimate.salary_p75_lkr or 0):
                percentile = 75
            elif user_salary >= market_median:
                percentile = 50
            elif user_salary >= (estimate.salary_p25_lkr or 0):
                percentile = 25
            else:
                percentile = 10

        benchmark = SalaryBenchmark(
            title=title, user_salary=user_salary, market_median=market_median,
            percentile_rank=percentile,
            below_market=bool(market_median and user_salary < market_median * 0.9),
            above_market=bool(market_median and user_salary > market_median * 1.1),
        )
        if request.user.is_authenticated:
            benchmark.user = request.user
        benchmark.save()
        return Response(SalaryBenchmarkSerializer(benchmark).data)


class SalaryTrendView(APIView):
    """Salary trend chart data for a title over the last 12 months."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        title = request.query_params.get("title", "").strip()
        district_id = request.query_params.get("district")
        if not title:
            return Response({"detail": "title is required."}, status=status.HTTP_400_BAD_REQUEST)
        qs = SalaryTrend.objects.filter(normalized_title__icontains=title)
        if district_id:
            qs = qs.filter(district_id=district_id)
        trends = qs.order_by("month")[:24]
        return Response(SalaryTrendSerializer(trends, many=True).data)


class SalarySubmissionView(APIView):
    """Submit an anonymous salary report."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ser = SalarySubmissionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        submission = ser.save(submitted_by=request.user)
        return Response(SalarySubmissionSerializer(submission).data, status=status.HTTP_201_CREATED)


class CompanySalaryView(APIView):
    """Salary data for a specific company."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        from apps.employers.models import EmployerAccount
        from apps.employers.models import SalaryReport
        try:
            employer = EmployerAccount.objects.get(slug=slug)
        except EmployerAccount.DoesNotExist:
            return Response({"detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)
        reports = SalaryReport.objects.filter(employer=employer, is_verified=True)[:20]
        # Aggregate by title
        from django.db.models import Avg, Count
        by_title = reports.values("job_title").annotate(
            avg_salary=Avg("base_salary"),
            count=Count("id"),
        ).order_by("-count")
        return Response({
            "company": employer.company_name,
            "salary_data": list(by_title),
            "total_reports": reports.count(),
        })


class CostOfLivingView(APIView):
    """Cost-of-living index for all districts."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        cache_key = "cost_of_living_all"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)
        cols = CostOfLivingIndex.objects.select_related("district").all()
        data = [
            {
                "district_id": col.district_id,
                "district_name": col.district.name if col.district else "",
                "index_value": col.index_value,
                "housing_index": col.housing_index,
                "transport_index": col.transport_index,
                "food_index": col.food_index,
            }
            for col in cols
        ]
        cache.set(cache_key, data, 3600)
        return Response(data)
