"""API for Recruitment Marketing — career sites, brand assets, job ads, UTM, social, events."""

from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.recruitment_marketing.models import (
    CareerSite, CareerSitePage, CampaignLanding, BrandAsset,
    JobAdVariant, UTMTracking, SocialPost, TalentCommunitySignup,
    FAQItem, RecruitingCalendarEvent,
    EVPBlock, EmployeeTestimonial, RecruiterProfile, DepartmentPage,
    OfficePage, JobDistributionChannel, JobDistributionPost,
    MarketingCalendarEntry, BrandAnalyticsSnapshot, ChatbotFAQFlow,
    DayInLifeSection,
)
from apps.accounts.permissions import IsRecruiter, HasTenantAccess


# ── Serializers ───────────────────────────────────────────────────────────────

class CareerSiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareerSite
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "published_at"]


class CareerSitePageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareerSitePage
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class CampaignLandingSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignLanding
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "view_count", "conversion_count"]


class BrandAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrandAsset
        fields = "__all__"
        read_only_fields = ["id", "created_at", "uploaded_by"]


class JobAdVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobAdVariant
        fields = "__all__"
        read_only_fields = [
            "id", "created_at", "updated_at",
            "impressions", "clicks", "applications",
        ]


class UTMTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = UTMTracking
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class SocialPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialPost
        fields = "__all__"
        read_only_fields = [
            "id", "created_at", "updated_at", "published_at",
            "impressions", "likes", "shares", "clicks", "created_by",
        ]


class TalentCommunitySignupSerializer(serializers.ModelSerializer):
    class Meta:
        model = TalentCommunitySignup
        fields = "__all__"
        read_only_fields = ["id", "opted_in_at"]


class FAQItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQItem
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class RecruitingCalendarEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecruitingCalendarEvent
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "created_by"]


# ── ViewSets ──────────────────────────────────────────────────────────────────

class CareerSiteViewSet(viewsets.ModelViewSet):
    serializer_class = CareerSiteSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["status"]
    search_fields = ["name", "subdomain", "custom_domain"]

    def get_queryset(self):
        return CareerSite.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        """Publish a career site."""
        from django.utils import timezone
        site = self.get_object()
        site.status = "live"
        site.published_at = timezone.now()
        site.save(update_fields=["status", "published_at", "updated_at"])
        return Response(CareerSiteSerializer(site).data)


class CareerSitePageViewSet(viewsets.ModelViewSet):
    serializer_class = CareerSitePageSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["site", "page_type", "is_published"]

    def get_queryset(self):
        return CareerSitePage.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class CampaignLandingViewSet(viewsets.ModelViewSet):
    serializer_class = CampaignLandingSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["site", "is_active"]

    def get_queryset(self):
        return CampaignLanding.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["post"], permission_classes=[AllowAny])
    def track_view(self, request, pk=None):
        """Increment view_count — called from public career site."""
        from django.db.models import F
        CampaignLanding.objects.filter(pk=pk).update(view_count=F("view_count") + 1)
        return Response({"status": "ok"})

    @action(detail=True, methods=["post"], permission_classes=[AllowAny])
    def track_conversion(self, request, pk=None):
        """Increment conversion_count — called when candidate applies via landing page."""
        from django.db.models import F
        CampaignLanding.objects.filter(pk=pk).update(conversion_count=F("conversion_count") + 1)
        return Response({"status": "ok"})


class BrandAssetViewSet(viewsets.ModelViewSet):
    serializer_class = BrandAssetSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["asset_type"]
    search_fields = ["name", "alt_text"]

    def get_queryset(self):
        return BrandAsset.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            uploaded_by=self.request.user,
        )


class JobAdVariantViewSet(viewsets.ModelViewSet):
    serializer_class = JobAdVariantSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["job", "channel", "status"]

    def get_queryset(self):
        return JobAdVariant.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def ab_winner(self, request, pk=None):
        """Mark this variant as the A/B test winner and end all other variants for the same job."""
        variant = self.get_object()
        # End all other variants for the same job
        JobAdVariant.objects.filter(
            tenant_id=self.request.tenant_id,
            job=variant.job,
        ).exclude(pk=pk).update(status="ended")
        variant.status = "active"
        variant.save(update_fields=["status", "updated_at"])
        return Response(JobAdVariantSerializer(variant).data)


class UTMTrackingViewSet(viewsets.ReadOnlyModelViewSet):
    """UTM records are created by the portal/landing page, read-only here."""
    serializer_class = UTMTrackingSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["utm_source", "utm_medium", "utm_campaign"]

    def get_queryset(self):
        return UTMTracking.objects.filter(tenant_id=self.request.tenant_id)

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def utm_ingest(self, request):
        """Public endpoint — capture UTM parameters from career site page load."""
        import hashlib
        tenant_id = request.data.get("tenant_id")
        if not tenant_id:
            return Response({"error": "tenant_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", ""))
        ip_hash = hashlib.sha256(ip.encode()).hexdigest() if ip else ""

        record = UTMTracking.objects.create(
            tenant_id=tenant_id,
            utm_source=request.data.get("utm_source", ""),
            utm_medium=request.data.get("utm_medium", ""),
            utm_campaign=request.data.get("utm_campaign", ""),
            utm_term=request.data.get("utm_term", ""),
            utm_content=request.data.get("utm_content", ""),
            referrer_url=request.data.get("referrer_url", ""),
            ip_hash=ip_hash,
        )
        return Response(UTMTrackingSerializer(record).data, status=status.HTTP_201_CREATED)


class SocialPostViewSet(viewsets.ModelViewSet):
    serializer_class = SocialPostSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["channel", "status", "job"]
    ordering_fields = ["created_at", "scheduled_at"]

    def get_queryset(self):
        return SocialPost.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            created_by=self.request.user,
        )

    @action(detail=True, methods=["post"])
    def schedule(self, request, pk=None):
        """Schedule a draft social post."""
        from django.utils import timezone
        post = self.get_object()
        scheduled_at = request.data.get("scheduled_at")
        if not scheduled_at:
            return Response(
                {"error": "scheduled_at is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        post.status = "scheduled"
        post.scheduled_at = scheduled_at
        post.save(update_fields=["status", "scheduled_at", "updated_at"])
        return Response(SocialPostSerializer(post).data)


class TalentCommunitySignupViewSet(viewsets.ModelViewSet):
    serializer_class = TalentCommunitySignupSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["consent_recorded"]
    search_fields = ["email", "first_name", "last_name"]

    def get_queryset(self):
        return TalentCommunitySignup.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class FAQItemViewSet(viewsets.ModelViewSet):
    serializer_class = FAQItemSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["site", "is_published"]

    def get_queryset(self):
        return FAQItem.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class RecruitingCalendarEventViewSet(viewsets.ModelViewSet):
    serializer_class = RecruitingCalendarEventSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["event_type", "is_published", "is_virtual"]
    ordering_fields = ["starts_at"]

    def get_queryset(self):
        return RecruitingCalendarEvent.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            created_by=self.request.user,
        )


# ── Extended Feature 2 Serializers ────────────────────────────────────────────

class EVPBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = EVPBlock
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class EmployeeTestimonialSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeTestimonial
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class RecruiterProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecruiterProfile
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class DepartmentPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepartmentPage
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class OfficePageSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfficePage
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class JobDistributionChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobDistributionChannel
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "last_sync_at"]
        extra_kwargs = {"api_key": {"write_only": True}}


class JobDistributionPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobDistributionPost
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "posted_at"]


class MarketingCalendarEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketingCalendarEntry
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "created_by"]


class BrandAnalyticsSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrandAnalyticsSnapshot
        fields = "__all__"
        read_only_fields = ["id"]


class ChatbotFAQFlowSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatbotFAQFlow
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class DayInLifeSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DayInLifeSection
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


# ── Extended Feature 2 ViewSets ───────────────────────────────────────────────

class EVPBlockViewSet(viewsets.ModelViewSet):
    serializer_class = EVPBlockSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["site", "is_published"]

    def get_queryset(self):
        return EVPBlock.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class EmployeeTestimonialViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeTestimonialSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["site", "is_featured"]

    def get_queryset(self):
        return EmployeeTestimonial.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class RecruiterProfileViewSet(viewsets.ModelViewSet):
    serializer_class = RecruiterProfileSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["is_public"]

    def get_queryset(self):
        return RecruiterProfile.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class DepartmentPageViewSet(viewsets.ModelViewSet):
    serializer_class = DepartmentPageSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["site", "is_published"]

    def get_queryset(self):
        return DepartmentPage.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class OfficePageViewSet(viewsets.ModelViewSet):
    serializer_class = OfficePageSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["site", "is_published", "country"]

    def get_queryset(self):
        return OfficePage.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class JobDistributionChannelViewSet(viewsets.ModelViewSet):
    serializer_class = JobDistributionChannelSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["channel_type", "is_active", "auto_post"]

    def get_queryset(self):
        return JobDistributionChannel.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=["post"])
    def distribute(self, request, pk=None):
        """Post a job to this distribution channel."""
        from django.utils import timezone
        channel = self.get_object()
        job_id = request.data.get("job_id")
        if not job_id:
            return Response({"error": "job_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        post, created = JobDistributionPost.objects.get_or_create(
            tenant_id=self.request.tenant_id,
            job_id=job_id,
            channel=channel,
            defaults={"status": "pending"},
        )
        # Simulate posting — in production this would call the channel API
        post.status = "posted"
        post.posted_at = timezone.now()
        post.save(update_fields=["status", "posted_at", "updated_at"])
        channel.last_sync_at = timezone.now()
        channel.save(update_fields=["last_sync_at", "updated_at"])
        return Response(JobDistributionPostSerializer(post).data)


class JobDistributionPostViewSet(viewsets.ModelViewSet):
    serializer_class = JobDistributionPostSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["job", "channel", "status"]

    def get_queryset(self):
        return JobDistributionPost.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class MarketingCalendarEntryViewSet(viewsets.ModelViewSet):
    serializer_class = MarketingCalendarEntrySerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["entry_type", "status", "linked_job"]
    ordering_fields = ["scheduled_date"]

    def get_queryset(self):
        return MarketingCalendarEntry.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            created_by=self.request.user,
        )


class BrandAnalyticsSnapshotViewSet(viewsets.ModelViewSet):
    serializer_class = BrandAnalyticsSnapshotSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["site"]
    ordering_fields = ["date"]

    def get_queryset(self):
        return BrandAnalyticsSnapshot.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=False, methods=["get"])
    def brand_analytics_summary(self, request):
        """Aggregated stats across all sites for the tenant."""
        from django.db.models import Sum, Avg
        qs = self.get_queryset()
        site_id = request.query_params.get("site")
        if site_id:
            qs = qs.filter(site_id=site_id)

        agg = qs.aggregate(
            total_views=Sum("career_site_views"),
            total_visitors=Sum("unique_visitors"),
            total_starts=Sum("applications_started"),
            total_completions=Sum("applications_completed"),
            avg_bounce=Avg("bounce_rate"),
            avg_time=Avg("avg_time_on_site_seconds"),
        )

        total_starts = agg["total_starts"] or 0
        total_visitors = agg["total_visitors"] or 0
        total_completions = agg["total_completions"] or 0

        return Response({
            **agg,
            "application_start_rate": round(total_starts / total_visitors * 100, 1) if total_visitors else 0,
            "application_completion_rate": round(total_completions / total_starts * 100, 1) if total_starts else 0,
            "days_counted": qs.count(),
        })


class ChatbotFAQFlowViewSet(viewsets.ModelViewSet):
    serializer_class = ChatbotFAQFlowSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["site", "flow_type", "is_active"]

    def get_queryset(self):
        return ChatbotFAQFlow.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def chatbot_query(self, request):
        """Public endpoint — match user query keywords to a chatbot flow response."""
        query = (request.data.get("query") or "").lower()
        site_id = request.data.get("site_id")
        if not query or not site_id:
            return Response({"error": "query and site_id are required"}, status=status.HTTP_400_BAD_REQUEST)

        flows = ChatbotFAQFlow.objects.filter(site_id=site_id, is_active=True)
        best_match = None
        best_score = 0
        for flow in flows:
            keywords = [k.lower() for k in (flow.trigger_keywords or [])]
            score = sum(1 for kw in keywords if kw in query)
            if score > best_score:
                best_score = score
                best_match = flow

        if best_match:
            return Response({
                "response": best_match.response,
                "flow_type": best_match.flow_type,
                "matched": True,
            })
        return Response({
            "response": "I'm not sure about that. Please browse our open roles or sign up for job alerts!",
            "flow_type": "faq",
            "matched": False,
        })


class DayInLifeSectionViewSet(viewsets.ModelViewSet):
    serializer_class = DayInLifeSectionSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["site", "media_type", "is_published"]

    def get_queryset(self):
        return DayInLifeSection.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


# ── Router & URLs ─────────────────────────────────────────────────────────────

router = DefaultRouter()
router.register("career-sites", CareerSiteViewSet, basename="career-sites")
router.register("pages", CareerSitePageViewSet, basename="career-site-pages")
router.register("campaign-landings", CampaignLandingViewSet, basename="campaign-landings")
router.register("brand-assets", BrandAssetViewSet, basename="brand-assets")
router.register("job-ad-variants", JobAdVariantViewSet, basename="job-ad-variants")
router.register("utm-tracking", UTMTrackingViewSet, basename="utm-tracking")
router.register("social-posts", SocialPostViewSet, basename="social-posts")
router.register("talent-community", TalentCommunitySignupViewSet, basename="talent-community")
router.register("faq", FAQItemViewSet, basename="faq")
router.register("events", RecruitingCalendarEventViewSet, basename="recruiting-events")
# Feature 2 extended
router.register("evp-blocks", EVPBlockViewSet, basename="evp-blocks")
router.register("testimonials", EmployeeTestimonialViewSet, basename="testimonials")
router.register("recruiter-profiles", RecruiterProfileViewSet, basename="recruiter-profiles")
router.register("department-pages", DepartmentPageViewSet, basename="department-pages")
router.register("office-pages", OfficePageViewSet, basename="office-pages")
router.register("distribution-channels", JobDistributionChannelViewSet, basename="distribution-channels")
router.register("distribution-posts", JobDistributionPostViewSet, basename="distribution-posts")
router.register("marketing-calendar", MarketingCalendarEntryViewSet, basename="marketing-calendar")
router.register("brand-analytics", BrandAnalyticsSnapshotViewSet, basename="brand-analytics")
router.register("chatbot-flows", ChatbotFAQFlowViewSet, basename="chatbot-flows")
router.register("day-in-life", DayInLifeSectionViewSet, basename="day-in-life")

urlpatterns = [
    path("", include(router.urls)),
]
