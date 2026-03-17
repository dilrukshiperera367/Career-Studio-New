from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone as tz
from .models import Review, ProviderResponse, ReviewFlag, OutcomeTag, ReviewSummary
from .serializers import (
    ReviewSerializer, ReviewListSerializer, ProviderResponseSerializer,
    ReviewFlagSerializer, OutcomeTagSerializer, ReviewSummarySerializer,
)


class OutcomeTagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OutcomeTag.objects.filter(is_active=True)
    serializer_class = OutcomeTagSerializer
    permission_classes = [permissions.AllowAny]


class ReviewViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = ["provider", "rating_overall", "moderation_status", "is_featured"]
    ordering_fields = ["created_at", "rating_overall", "helpful_votes"]

    def get_serializer_class(self):
        if self.action in ("list", "provider_reviews"):
            return ReviewListSerializer
        return ReviewSerializer

    def get_queryset(self):
        qs = Review.objects.filter(moderation_status="approved").select_related(
            "reviewer", "provider", "provider_response",
        ).prefetch_related("outcome_tags")
        provider_id = self.request.query_params.get("provider")
        if provider_id:
            qs = qs.filter(provider_id=provider_id)
        return qs

    def perform_create(self, serializer):
        booking = serializer.validated_data.get("booking")
        serializer.save(reviewer=self.request.user, provider=booking.provider)

    @action(detail=True, methods=["post"])
    def vote_helpful(self, request, pk=None):
        review = self.get_object()
        review.helpful_votes += 1
        review.save(update_fields=["helpful_votes"])
        return Response({"helpful_votes": review.helpful_votes})

    @action(detail=False, methods=["get"], url_path="by-provider/(?P<provider_id>[^/.]+)")
    def provider_reviews(self, request, provider_id=None):
        qs = Review.objects.filter(
            provider_id=provider_id,
            moderation_status="approved",
        ).select_related("reviewer", "provider_response").prefetch_related("outcome_tags")
        serializer = ReviewListSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def my_reviews(self, request):
        """Buyer's given reviews."""
        reviews = Review.objects.filter(reviewer=request.user)
        return Response(ReviewSerializer(reviews, many=True).data)


class ProviderResponseViewSet(viewsets.ModelViewSet):
    serializer_class = ProviderResponseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ProviderResponse.objects.filter(
            review__provider__user=self.request.user
        )


class ReviewFlagViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewFlagSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return ReviewFlag.objects.all()
        return ReviewFlag.objects.filter(flagged_by=user)

    def perform_create(self, serializer):
        serializer.save(flagged_by=self.request.user)


class ReviewSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ReviewSummarySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return ReviewSummary.objects.all()
