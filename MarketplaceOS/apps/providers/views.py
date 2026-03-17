from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.utils.text import slugify
from django.utils import timezone as tz
from .models import (
    Provider, ProviderCredential, ProviderAvailabilitySlot,
    ProviderBlackout, ProviderBadge, ProviderApplication,
)
from .serializers import (
    ProviderSerializer, ProviderListSerializer, ProviderCredentialSerializer,
    ProviderAvailabilitySlotSerializer, ProviderBlackoutSerializer,
    ProviderBadgeSerializer, ProviderApplicationSerializer,
)


class ProviderViewSet(viewsets.ModelViewSet):
    queryset = Provider.objects.filter(status="approved")
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    search_fields = ["display_name", "headline", "bio", "skills", "industries"]
    filterset_fields = ["provider_type", "status", "is_verified", "is_featured", "timezone", "country"]
    ordering_fields = ["trust_score", "average_rating", "total_sessions", "base_rate_lkr", "created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return ProviderListSerializer
        return ProviderSerializer

    def get_queryset(self):
        qs = Provider.objects.filter(status="approved").select_related("user").prefetch_related("badges")
        # Filters
        provider_type = self.request.query_params.get("provider_type")
        if provider_type:
            qs = qs.filter(provider_type=provider_type)
        min_rate = self.request.query_params.get("min_rate")
        max_rate = self.request.query_params.get("max_rate")
        if min_rate:
            qs = qs.filter(base_rate_lkr__gte=min_rate)
        if max_rate:
            qs = qs.filter(base_rate_lkr__lte=max_rate)
        languages = self.request.query_params.get("languages")
        if languages:
            qs = qs.filter(languages__contains=languages)
        return qs

    def perform_create(self, serializer):
        display_name = serializer.validated_data.get("display_name", "")
        slug = slugify(display_name) or f"provider-{self.request.user.id}"
        serializer.save(user=self.request.user, slug=slug, status="pending")

    @action(detail=True, methods=["get"])
    def public_profile(self, request, pk=None):
        """Full public-facing provider profile."""
        provider = self.get_object()
        serializer = ProviderSerializer(provider)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def dashboard(self, request, pk=None):
        """Provider dashboard KPIs."""
        provider = self.get_object()
        return Response({
            "total_sessions": provider.total_sessions,
            "total_reviews": provider.total_reviews,
            "average_rating": float(provider.average_rating),
            "completion_rate": float(provider.completion_rate),
            "repeat_booking_rate": float(provider.repeat_booking_rate),
            "trust_score": float(provider.trust_score),
            "response_time_hours": float(provider.response_time_hours),
            "profile_completion_pct": provider.profile_completion_pct,
            "status": provider.status,
            "badges": [b.badge_type for b in provider.badges.filter(is_active=True)],
        })

    @action(detail=False, methods=["get"])
    def my_profile(self, request):
        """Return the authenticated user's provider profile."""
        try:
            provider = request.user.provider_profile
        except Provider.DoesNotExist:
            return Response({"detail": "Provider profile not found."}, status=404)
        serializer = ProviderSerializer(provider)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def featured(self, request):
        """Featured providers for homepage/category spotlights."""
        providers = Provider.objects.filter(status="approved", is_featured=True)[:12]
        serializer = ProviderListSerializer(providers, many=True)
        return Response(serializer.data)


class ProviderCredentialViewSet(viewsets.ModelViewSet):
    serializer_class = ProviderCredentialSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["provider", "credential_type", "is_verified"]

    def get_queryset(self):
        return ProviderCredential.objects.filter(
            provider__user=self.request.user
        ).select_related("provider")


class ProviderAvailabilityViewSet(viewsets.ModelViewSet):
    serializer_class = ProviderAvailabilitySlotSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["provider", "day_of_week", "is_active"]

    def get_queryset(self):
        return ProviderAvailabilitySlot.objects.filter(
            provider__user=self.request.user
        )


class ProviderBlackoutViewSet(viewsets.ModelViewSet):
    serializer_class = ProviderBlackoutSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ProviderBlackout.objects.filter(provider__user=self.request.user)


class ProviderApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = ProviderApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["status"]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return ProviderApplication.objects.all().select_related("provider", "reviewed_by")
        return ProviderApplication.objects.filter(provider__user=user)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """Submit the application for review."""
        app = self.get_object()
        if app.status not in ("draft", "info_requested"):
            return Response({"detail": "Cannot resubmit from current status."}, status=400)
        app.status = "submitted"
        app.submitted_at = tz.now()
        app.save()
        return Response({"detail": "Application submitted for review."})

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Admin: approve a provider application."""
        if request.user.role != "admin":
            return Response(status=403)
        app = self.get_object()
        app.status = "approved"
        app.reviewed_by = request.user
        app.reviewed_at = tz.now()
        app.save()
        app.provider.status = "approved"
        app.provider.save()
        return Response({"detail": "Provider approved."})

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Admin: reject a provider application."""
        if request.user.role != "admin":
            return Response(status=403)
        app = self.get_object()
        app.status = "rejected"
        app.rejection_reason = request.data.get("reason", "")
        app.reviewed_by = request.user
        app.reviewed_at = tz.now()
        app.save()
        app.provider.status = "archived"
        app.provider.save()
        return Response({"detail": "Application rejected."})
