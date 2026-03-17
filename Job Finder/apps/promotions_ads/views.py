"""Promotions Ads — views."""
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.jobs.models import JobListing
from apps.jobs.serializers import JobListSerializer
from .models import PromotedJobCampaign, PromotedJob, AdClick, SponsoredCompanyPage
from .serializers import PromotedJobCampaignSerializer, PromotedJobSerializer, SponsoredCompanyPageSerializer


def _get_employer(request):
    m = request.user.employer_memberships.filter(role__in=["owner", "admin"]).select_related("employer").first()
    return m.employer if m else None


class PromotedJobCampaignListCreateView(APIView):
    """List and create promoted job campaigns for the authenticated employer."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        employer = _get_employer(request)
        if not employer:
            return Response({"detail": "No employer account."}, status=status.HTTP_404_NOT_FOUND)
        campaigns = PromotedJobCampaign.objects.filter(employer=employer).prefetch_related("promoted_jobs__job")
        return Response(PromotedJobCampaignSerializer(campaigns, many=True).data)

    def post(self, request):
        employer = _get_employer(request)
        if not employer:
            return Response({"detail": "No employer account."}, status=status.HTTP_400_BAD_REQUEST)
        data = request.data.copy()
        ser = PromotedJobCampaignSerializer(data=data)
        ser.is_valid(raise_exception=True)
        campaign = ser.save(employer=employer)
        return Response(PromotedJobCampaignSerializer(campaign).data, status=status.HTTP_201_CREATED)


class PromotedJobCampaignDetailView(APIView):
    """Retrieve, update, or delete a specific campaign."""
    permission_classes = [permissions.IsAuthenticated]

    def _get_campaign(self, request, campaign_id):
        employer = _get_employer(request)
        if not employer:
            return None
        try:
            return PromotedJobCampaign.objects.get(pk=campaign_id, employer=employer)
        except PromotedJobCampaign.DoesNotExist:
            return None

    def get(self, request, campaign_id):
        campaign = self._get_campaign(request, campaign_id)
        if not campaign:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(PromotedJobCampaignSerializer(campaign).data)

    def patch(self, request, campaign_id):
        campaign = self._get_campaign(request, campaign_id)
        if not campaign:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        ser = PromotedJobCampaignSerializer(campaign, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)

    def delete(self, request, campaign_id):
        campaign = self._get_campaign(request, campaign_id)
        if not campaign:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        campaign.status = "cancelled"
        campaign.save(update_fields=["status"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class PromoteJobView(APIView):
    """Add a job to a promotion campaign."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, campaign_id):
        employer = _get_employer(request)
        if not employer:
            return Response({"detail": "No employer account."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            campaign = PromotedJobCampaign.objects.get(pk=campaign_id, employer=employer)
        except PromotedJobCampaign.DoesNotExist:
            return Response({"detail": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND)
        job_id = request.data.get("job_id")
        try:
            job = JobListing.objects.get(pk=job_id, employer=employer)
        except JobListing.DoesNotExist:
            return Response({"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND)
        promo, created = PromotedJob.objects.get_or_create(
            campaign=campaign, job=job,
            defaults={"boost_factor": 2.5, "is_active": True},
        )
        # Update job boost factor
        job.is_boosted = True
        job.boost_factor = promo.boost_factor
        job.save(update_fields=["is_boosted", "boost_factor"])
        return Response(PromotedJobSerializer(promo).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class AdClickTrackView(APIView):
    """Track a click on a promoted job ad."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        promoted_job_id = request.data.get("promoted_job_id")
        try:
            promo = PromotedJob.objects.select_related("campaign").get(pk=promoted_job_id, is_active=True)
        except PromotedJob.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        AdClick.objects.create(
            promoted_job=promo,
            user=request.user if request.user.is_authenticated else None,
            ip_address=request.META.get("REMOTE_ADDR"),
            cost_lkr=promo.campaign.bid_amount_lkr,
        )
        promo.clicks += 1
        promo.save(update_fields=["clicks"])
        return Response({"tracked": True})


class PromotedJobFeedView(APIView):
    """Return promoted jobs to inject into search results."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        active_promos = PromotedJob.objects.filter(
            is_active=True,
            campaign__status="active",
        ).select_related("job", "job__employer", "job__district")[:5]
        jobs = [p.job for p in active_promos]
        return Response(JobListSerializer(jobs, many=True, context={"request": request}).data)
