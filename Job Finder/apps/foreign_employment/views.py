"""Foreign Employment views — SLBFE agencies, overseas jobs, pre-departure checklists."""
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ForeignEmploymentAgency, OverseasJob, PreDepartureChecklist
from .serializers import (
    ForeignEmploymentAgencySerializer,
    OverseasJobSerializer,
    PreDepartureChecklistSerializer,
)


class AgencyListView(generics.ListAPIView):
    """List SLBFE-registered foreign employment agencies."""
    serializer_class = ForeignEmploymentAgencySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = ForeignEmploymentAgency.objects.all()
        country = self.request.query_params.get("country")
        if country:
            qs = qs.filter(countries_served__contains=[country])
        verified = self.request.query_params.get("verified")
        if verified == "true":
            qs = qs.filter(is_verified=True)
        slbfe = self.request.query_params.get("slbfe")
        if slbfe == "true":
            qs = qs.filter(is_slbfe_registered=True)
        return qs.order_by("-rating", "name")


class AgencyDetailView(generics.RetrieveAPIView):
    """Retrieve a single agency with full details."""
    serializer_class = ForeignEmploymentAgencySerializer
    permission_classes = [permissions.AllowAny]
    queryset = ForeignEmploymentAgency.objects.all()
    lookup_field = "slug"


class OverseasJobListView(generics.ListAPIView):
    """List/search overseas job listings."""
    serializer_class = OverseasJobSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = OverseasJob.objects.filter(status="active").select_related("agency")
        country = self.request.query_params.get("country")
        if country:
            qs = qs.filter(country__icontains=country)
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(title__icontains=q)
        agency = self.request.query_params.get("agency")
        if agency:
            qs = qs.filter(agency__slug=agency)
        verified = self.request.query_params.get("verified")
        if verified == "true":
            qs = qs.filter(agency__is_verified=True)
        return qs.order_by("-created_at")


class OverseasJobDetailView(generics.RetrieveAPIView):
    """Retrieve a single overseas job."""
    serializer_class = OverseasJobSerializer
    permission_classes = [permissions.AllowAny]
    queryset = OverseasJob.objects.filter(status="active").select_related("agency")


class AgencyJobsView(generics.ListAPIView):
    """List jobs for a specific agency."""
    serializer_class = OverseasJobSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return OverseasJob.objects.filter(
            agency__slug=self.kwargs["slug"], status="active",
        ).select_related("agency")


class CountryListView(APIView):
    """Return list of countries with active job counts."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from django.db.models import Count
        countries = (
            OverseasJob.objects.filter(status="active")
            .values("country")
            .annotate(job_count=Count("id"))
            .order_by("-job_count")
        )
        return Response(list(countries))


class PreDepartureChecklistView(generics.ListAPIView):
    """Pre-departure checklist items for a specific destination country."""
    serializer_class = PreDepartureChecklistSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        country = self.kwargs.get("country") or self.request.query_params.get("country", "")
        qs = PreDepartureChecklist.objects.all()
        if country:
            qs = qs.filter(country__iexact=country)
        return qs.order_by("sort_order")
