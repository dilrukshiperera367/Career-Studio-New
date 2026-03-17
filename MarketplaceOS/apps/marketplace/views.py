from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import (
    SavedProvider, SavedService, ProviderComparison,
    BuyerProfile, MatchRequest, MatchRecommendation, RecommendationFeedback,
)
from .serializers import (
    SavedProviderSerializer, SavedServiceSerializer, ProviderComparisonSerializer,
    BuyerProfileSerializer, MatchRequestSerializer, MatchRecommendationSerializer,
    RecommendationFeedbackSerializer,
)


class SavedProviderViewSet(viewsets.ModelViewSet):
    serializer_class = SavedProviderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SavedProvider.objects.filter(buyer=self.request.user).select_related("provider")

    def perform_create(self, serializer):
        serializer.save(buyer=self.request.user)


class SavedServiceViewSet(viewsets.ModelViewSet):
    serializer_class = SavedServiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SavedService.objects.filter(buyer=self.request.user).select_related("service")

    def perform_create(self, serializer):
        serializer.save(buyer=self.request.user)


class ProviderComparisonViewSet(viewsets.ModelViewSet):
    serializer_class = ProviderComparisonSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ProviderComparison.objects.filter(buyer=self.request.user).prefetch_related("providers")

    def perform_create(self, serializer):
        serializer.save(buyer=self.request.user)

    @action(detail=True, methods=["post"], url_path="add-provider/(?P<provider_id>[^/.]+)")
    def add_provider(self, request, pk=None, provider_id=None):
        comparison = self.get_object()
        if comparison.providers.count() >= 4:
            return Response(
                {"detail": "Maximum 4 providers per comparison."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from apps.providers.models import Provider
        from django.shortcuts import get_object_or_404
        provider = get_object_or_404(Provider, pk=provider_id)
        comparison.providers.add(provider)
        return Response({"detail": "Provider added to comparison."})

    @action(detail=True, methods=["delete"], url_path="remove-provider/(?P<provider_id>[^/.]+)")
    def remove_provider(self, request, pk=None, provider_id=None):
        comparison = self.get_object()
        comparison.providers.filter(pk=provider_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BuyerProfileViewSet(viewsets.ModelViewSet):
    serializer_class = BuyerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BuyerProfile.objects.filter(buyer=self.request.user)

    def perform_create(self, serializer):
        serializer.save(buyer=self.request.user)

    @action(detail=False, methods=["get", "put", "patch"], url_path="me")
    def my_profile(self, request):
        profile, _ = BuyerProfile.objects.get_or_create(buyer=request.user)
        if request.method == "GET":
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        serializer = self.get_serializer(profile, data=request.data, partial=(request.method == "PATCH"))
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class MatchRequestViewSet(viewsets.ModelViewSet):
    serializer_class = MatchRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MatchRequest.objects.filter(buyer=self.request.user).prefetch_related("recommendations")

    def perform_create(self, serializer):
        import datetime
        from django.utils import timezone
        expires = timezone.now() + datetime.timedelta(days=7)
        match_request = serializer.save(buyer=self.request.user, expires_at=expires)
        # Trigger basic rule-based matching synchronously (AI matching via Celery)
        self._generate_basic_matches(match_request)

    def _generate_basic_matches(self, match_request):
        """
        Rule-based matching fallback.  Finds providers by type + active status,
        ranks by trust_score and average_rating.
        """
        from apps.providers.models import Provider
        qs = Provider.objects.filter(status="approved")
        if match_request.provider_type:
            qs = qs.filter(provider_type=match_request.provider_type)
        if match_request.budget_max_lkr:
            qs = qs.filter(hourly_rate_lkr__lte=match_request.budget_max_lkr)
        qs = qs.order_by("-trust_score", "-average_rating")[:5]
        for rank, provider in enumerate(qs, start=1):
            MatchRecommendation.objects.create(
                match_request=match_request,
                provider=provider,
                rank=rank,
                match_score=min(float(provider.trust_score or 0), 100),
                match_reasons=["availability", "type_match"],
                source=MatchRecommendation.RecommendationSource.ALGORITHM,
            )
        match_request.status = MatchRequest.MatchStatus.COMPLETED
        match_request.save(update_fields=["status"])

    @action(detail=True, methods=["post"], url_path="feedback/(?P<recommendation_id>[^/.]+)")
    def submit_feedback(self, request, pk=None, recommendation_id=None):
        from django.shortcuts import get_object_or_404
        recommendation = get_object_or_404(MatchRecommendation, pk=recommendation_id, match_request=self.get_object())
        serializer = RecommendationFeedbackSerializer(data={**request.data, "recommendation": recommendation.id})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MarketplaceSearchView(viewsets.ViewSet):
    """
    Unified search endpoint that queries providers + services.
    GET /api/search/?q=...&category=...&provider_type=...&price_max=...
    """
    permission_classes = [permissions.AllowAny]

    def list(self, request):
        from apps.providers.models import Provider
        from apps.services_catalog.models import Service

        q = request.query_params.get("q", "").strip()
        category = request.query_params.get("category", "")
        provider_type = request.query_params.get("provider_type", "")
        price_max = request.query_params.get("price_max")
        delivery_mode = request.query_params.get("delivery_mode", "")

        # Providers
        providers_qs = Provider.objects.filter(status="approved")
        if q:
            providers_qs = providers_qs.filter(
                Q(display_name__icontains=q) |
                Q(headline__icontains=q) |
                Q(bio__icontains=q) |
                Q(skills__icontains=q)
            )
        if provider_type:
            providers_qs = providers_qs.filter(provider_type=provider_type)
        if price_max:
            try:
                providers_qs = providers_qs.filter(hourly_rate_lkr__lte=float(price_max))
            except ValueError:
                pass
        providers_qs = providers_qs.order_by("-is_featured", "-trust_score", "-average_rating")[:20]

        # Services
        services_qs = Service.objects.filter(status="active", visibility="public")
        if q:
            services_qs = services_qs.filter(
                Q(title__icontains=q) |
                Q(description__icontains=q)
            )
        if delivery_mode:
            services_qs = services_qs.filter(delivery_mode=delivery_mode)
        services_qs = services_qs.select_related("provider")[:20]

        from apps.providers.serializers import ProviderListSerializer
        from apps.services_catalog.serializers import ServiceListSerializer

        return Response({
            "providers": ProviderListSerializer(providers_qs, many=True, context={"request": request}).data,
            "services": ServiceListSerializer(services_qs, many=True, context={"request": request}).data,
        })
