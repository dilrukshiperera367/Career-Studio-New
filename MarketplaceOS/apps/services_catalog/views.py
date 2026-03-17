from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.utils.text import slugify
from .models import ServiceCategory, Service, ServicePackage, ServiceAddOn, SavedProvider, SavedService
from .serializers import (
    ServiceCategorySerializer, ServiceSerializer, ServiceListSerializer,
    ServicePackageSerializer, ServiceAddOnSerializer,
    SavedProviderSerializer, SavedServiceSerializer,
)


class ServiceCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Publicly accessible service categories."""
    queryset = ServiceCategory.objects.filter(is_active=True, parent=None)
    serializer_class = ServiceCategorySerializer
    permission_classes = [permissions.AllowAny]
    search_fields = ["name", "description"]


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.filter(status="active")
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    search_fields = ["title", "description", "tags", "skills_covered"]
    filterset_fields = ["service_type", "delivery_mode", "category", "visibility", "status", "is_featured"]
    ordering_fields = ["price_lkr", "total_bookings", "average_rating", "created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return ServiceListSerializer
        return ServiceSerializer

    def get_queryset(self):
        qs = Service.objects.filter(status="active").select_related("provider", "category")
        # Price range filter
        min_price = self.request.query_params.get("min_price")
        max_price = self.request.query_params.get("max_price")
        if min_price:
            qs = qs.filter(price_lkr__gte=min_price)
        if max_price:
            qs = qs.filter(price_lkr__lte=max_price)
        # Duration filter
        max_duration = self.request.query_params.get("max_duration")
        if max_duration:
            qs = qs.filter(duration_minutes__lte=max_duration)
        # Language filter
        language = self.request.query_params.get("language")
        if language:
            qs = qs.filter(languages__contains=language)
        return qs

    def perform_create(self, serializer):
        title = serializer.validated_data.get("title", "")
        provider = self.request.user.provider_profile
        slug = slugify(title) or f"service-{provider.id}"
        serializer.save(provider=provider, slug=slug)

    @action(detail=False, methods=["get"])
    def featured(self, request):
        """Featured services for homepage/category pages."""
        qs = Service.objects.filter(status="active", is_featured=True).select_related("provider")[:20]
        serializer = ServiceListSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def by_goal(self, request):
        """
        Returns services matched to a goal string.
        Goals: 'get_first_job', 'switch_career', 'interview_prep', 'negotiate_salary', etc.
        """
        goal = request.query_params.get("goal", "")
        goal_to_types = {
            "get_first_job": ["resume_review", "linkedin_review", "career_coaching", "mock_interview"],
            "switch_career": ["career_coaching", "mentoring_session", "job_search_strategy"],
            "interview_prep": ["mock_interview", "technical_interview", "career_coaching"],
            "negotiate_salary": ["salary_negotiation", "career_coaching"],
            "get_promoted": ["leadership_coaching", "mentoring_session", "soft_skills_coaching"],
        }
        types = goal_to_types.get(goal, [])
        qs = Service.objects.filter(status="active", service_type__in=types) if types else Service.objects.none()
        serializer = ServiceListSerializer(qs[:20], many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def my_services(self, request):
        """Provider's own service listings including drafts."""
        try:
            provider = request.user.provider_profile
        except Exception:
            return Response({"detail": "Not a provider."}, status=403)
        qs = Service.objects.filter(provider=provider).order_by("-created_at")
        serializer = ServiceSerializer(qs, many=True)
        return Response(serializer.data)


class ServicePackageViewSet(viewsets.ModelViewSet):
    serializer_class = ServicePackageSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["service", "is_active"]

    def get_queryset(self):
        return ServicePackage.objects.filter(service__provider__user=self.request.user)


class SavedProviderViewSet(viewsets.ModelViewSet):
    serializer_class = SavedProviderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SavedProvider.objects.filter(user=self.request.user).select_related("provider")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SavedServiceViewSet(viewsets.ModelViewSet):
    serializer_class = SavedServiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SavedService.objects.filter(user=self.request.user).select_related("service")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
