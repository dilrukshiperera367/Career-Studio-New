"""
Feature 9 & 10 — Promoted Job Campaign Dashboard, Career Site Builder, Source Attribution,
Social Sharing Kit, Talent Community, Referral Campaigns.
"""
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView

from .models import PromotedJobCampaign, PromotedJob, AdClick
from .models_extra import TalentCommunityMember, SocialShareKit, CampaignSourceAttribution


def _get_employer(request):
    from apps.employers.models import EmployerAccount
    return EmployerAccount.objects.filter(team_members__user=request.user).first()


# ── Campaign Performance Dashboard ───────────────────────────────────────────

class CampaignPerformanceDashboardView(APIView):
    """
    GET /promotions-ads/dashboard/
    Full campaign performance overview for the logged-in employer.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        employer = _get_employer(request)
        if not employer:
            return Response({"detail": "Employer account not found."}, status=403)

        campaigns = PromotedJobCampaign.objects.filter(employer=employer)
        active_campaigns = campaigns.filter(status="active")

        total_stats = campaigns.aggregate(
            total_impressions=Sum("impressions"),
            total_clicks=Sum("clicks"),
            total_applications=Sum("applications"),
            total_spent=Sum("spent_lkr"),
        )

        # Per-campaign breakdown
        campaign_data = []
        for c in campaigns.order_by("-created_at")[:10]:
            ctr = round(c.clicks / c.impressions * 100, 2) if c.impressions else 0
            cpa = round(float(c.spent_lkr) / c.applications, 0) if c.applications else 0
            campaign_data.append({
                "id": str(c.id),
                "name": c.name,
                "status": c.status,
                "bid_model": c.bid_model,
                "budget_lkr": float(c.total_budget_lkr or c.daily_budget_lkr or 0),
                "spent_lkr": float(c.spent_lkr),
                "impressions": c.impressions,
                "clicks": c.clicks,
                "applications": c.applications,
                "ctr_pct": ctr,
                "cpa_lkr": cpa,
                "start_date": c.start_date,
                "end_date": c.end_date,
            })

        return Response({
            "active_campaigns": active_campaigns.count(),
            "total_campaigns": campaigns.count(),
            "total_impressions": total_stats["total_impressions"] or 0,
            "total_clicks": total_stats["total_clicks"] or 0,
            "total_applications": total_stats["total_applications"] or 0,
            "total_spent_lkr": float(total_stats["total_spent"] or 0),
            "overall_ctr_pct": round(
                (total_stats["total_clicks"] or 0) / (total_stats["total_impressions"] or 1) * 100, 2
            ),
            "campaigns": campaign_data,
        })


# ── Career Site Builder CRUD ──────────────────────────────────────────────────

class CareerPageListCreateView(ListCreateAPIView):
    """GET/POST /promotions-ads/career-pages/"""
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        employer = _get_employer(self.request)
        return CareerSitePage.objects.filter(employer=employer) if employer else CareerSitePage.objects.none()

    def perform_create(self, serializer):
        employer = _get_employer(self.request)
        serializer.save(employer=employer)

    def get_serializer_class(self):
        from rest_framework import serializers as s
        class PageSerializer(s.ModelSerializer):
            class Meta:
                model = CareerSitePage
                fields = [
                    "id", "page_type", "title", "slug", "tagline",
                    "body_content", "cta_label", "cta_url",
                    "is_published", "views_count", "created_at", "updated_at",
                ]
                read_only_fields = ["views_count", "created_at", "updated_at"]
        return PageSerializer


class CareerPageDetailView(RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /promotions-ads/career-pages/<uuid>/"""
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        employer = _get_employer(self.request)
        return CareerSitePage.objects.filter(employer=employer) if employer else CareerSitePage.objects.none()

    def get_serializer_class(self):
        from rest_framework import serializers as s
        class PageSerializer(s.ModelSerializer):
            class Meta:
                model = CareerSitePage
                fields = [
                    "id", "page_type", "title", "slug", "tagline",
                    "body_content", "cta_label", "cta_url",
                    "is_published", "views_count", "created_at", "updated_at",
                ]
                read_only_fields = ["views_count", "created_at", "updated_at"]
        return PageSerializer


class PublicCareerPageView(APIView):
    """GET /promotions-ads/career-pages/<slug>/public/ — public view of a career page."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        try:
            page = CareerSitePage.objects.select_related("employer").get(slug=slug, is_published=True)
        except CareerSitePage.DoesNotExist:
            return Response(status=404)

        page.views_count += 1
        page.save(update_fields=["views_count"])

        # Track attribution
        source = request.query_params.get("utm_source", "")
        medium = request.query_params.get("utm_medium", "")
        campaign = request.query_params.get("utm_campaign", "")
        if source or medium or campaign:
            CampaignSourceAttribution.objects.create(
                employer=page.employer,
                event_type="page_view",
                source=source, medium=medium, campaign=campaign,
                page=page,
            )

        return Response({
            "id": str(page.id),
            "employer": {
                "slug": page.employer.slug,
                "name": page.employer.company_name,
                "logo": page.employer.logo.url if page.employer.logo else None,
            },
            "page_type": page.page_type,
            "title": page.title,
            "tagline": page.tagline,
            "body_content": page.body_content,
            "cta_label": page.cta_label,
            "cta_url": page.cta_url,
            "views_count": page.views_count,
        })


# ── Talent Community Sign-Up ──────────────────────────────────────────────────

class TalentCommunitySignUpView(APIView):
    """POST /promotions-ads/talent-community/<employer_slug>/join/"""
    permission_classes = [permissions.AllowAny]

    def post(self, request, employer_slug):
        from apps.employers.models import EmployerAccount
        try:
            employer = EmployerAccount.objects.get(slug=employer_slug)
        except EmployerAccount.DoesNotExist:
            return Response(status=404)

        d = request.data
        email = d.get("email", "").strip().lower()
        if not email:
            return Response({"detail": "Email required."}, status=400)

        member, created = TalentCommunityMember.objects.get_or_create(
            employer=employer,
            email=email,
            defaults={
                "name": d.get("name", ""),
                "phone": d.get("phone", ""),
                "interested_roles": d.get("interested_roles", ""),
                "source": d.get("utm_source", request.query_params.get("utm_source", "")),
                "user": request.user if request.user.is_authenticated else None,
                "is_existing_user": request.user.is_authenticated,
            }
        )

        # Track attribution
        CampaignSourceAttribution.objects.create(
            employer=employer,
            event_type="talent_signup",
            source=d.get("utm_source", ""),
            medium=d.get("utm_medium", ""),
            campaign=d.get("utm_campaign", ""),
        )

        return Response({
            "joined": created,
            "message": "You've joined the talent community! We'll notify you of relevant opportunities." if created else "You're already in this talent community.",
        }, status=201 if created else 200)


class TalentCommunityListView(APIView):
    """GET /promotions-ads/talent-community/list/ — employer view of their talent community."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        employer = _get_employer(request)
        if not employer:
            return Response(status=403)
        members = TalentCommunityMember.objects.filter(employer=employer).order_by("-joined_at")[:100]
        return Response({
            "total": TalentCommunityMember.objects.filter(employer=employer).count(),
            "members": [{
                "id": str(m.id),
                "name": m.name,
                "email": m.email,
                "interested_roles": m.interested_roles,
                "source": m.source,
                "is_existing_user": m.is_existing_user,
                "joined_at": m.joined_at,
            } for m in members],
        })


# ── Social Sharing Kit ────────────────────────────────────────────────────────

class SocialShareKitView(APIView):
    """
    GET /promotions-ads/social-kit/<job_id>/
    Returns pre-filled social sharing texts for a job listing.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, job_id):
        from apps.jobs.models import JobListing
        try:
            job = JobListing.objects.select_related("employer").get(pk=job_id, status="active")
        except JobListing.DoesNotExist:
            return Response(status=404)

        base_url = f"{request.scheme}://{request.get_host()}"
        job_url = f"{base_url}/en/jobs/{job.slug or job.id}"

        title = job.title
        company = job.employer.company_name if job.employer else "us"

        kit = SocialShareKit.objects.filter(job=job).first()
        if kit:
            return Response({
                "linkedin_text": kit.linkedin_text,
                "twitter_text": kit.twitter_text,
                "whatsapp_text": kit.whatsapp_text,
                "facebook_text": kit.facebook_text,
                "share_url": kit.share_url or job_url,
                "share_image": kit.share_image.url if kit.share_image else None,
            })

        # Generate on-the-fly
        linkedin = f"🚀 We're hiring a {title} at {company}!\n\nJoin our team and make an impact.\n\n👉 Apply here: {job_url}\n\n#Hiring #JobAlert #CareerOpportunity"
        twitter = f"We're looking for a {title} to join @{company.replace(' ', '')}! 🎉\n\nApply: {job_url} #Hiring #Jobs"
        whatsapp = f"Hi! We're looking for a *{title}* at *{company}*. If you're interested, apply here:\n{job_url}"
        facebook = f"📢 Job Opportunity: {title} at {company}\n\nWe're growing our team! Apply now 👉 {job_url}"

        return Response({
            "linkedin_text": linkedin,
            "twitter_text": twitter,
            "whatsapp_text": whatsapp,
            "facebook_text": facebook,
            "share_url": job_url,
            "share_image": None,
        })


# ── Source Attribution Analytics ──────────────────────────────────────────────

class SourceAttributionAnalyticsView(APIView):
    """GET /promotions-ads/attribution/ — where applies and sign-ups are coming from."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        employer = _get_employer(request)
        if not employer:
            return Response(status=403)

        # Aggregate by source × event_type
        attributions = (
            CampaignSourceAttribution.objects
            .filter(employer=employer)
            .values("event_type", "source", "medium", "campaign")
            .annotate(count=Count("id"))
            .order_by("-count")[:50]
        )

        # Top sources for applies
        top_apply_sources = (
            CampaignSourceAttribution.objects
            .filter(employer=employer, event_type="apply")
            .values("source")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        return Response({
            "top_apply_sources": list(top_apply_sources),
            "attribution_breakdown": list(attributions),
        })
