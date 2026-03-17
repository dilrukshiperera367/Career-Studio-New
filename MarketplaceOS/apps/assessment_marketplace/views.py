from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import (
    AssessmentVendor, AssessmentProduct, AssessmentOrder,
    AssessmentDelivery, AssessmentResult,
)
from .serializers import (
    AssessmentVendorSerializer, AssessmentProductSerializer,
    AssessmentProductListSerializer, AssessmentOrderSerializer,
    AssessmentOrderListSerializer, AssessmentDeliverySerializer,
    AssessmentResultSerializer,
)


class AssessmentVendorViewSet(viewsets.ModelViewSet):
    queryset = AssessmentVendor.objects.select_related("provider").all()
    serializer_class = AssessmentVendorSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]


class AssessmentProductViewSet(viewsets.ModelViewSet):
    serializer_class = AssessmentProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = AssessmentProduct.objects.select_related("vendor").prefetch_related("role_maps").filter(is_active=True)
        category = self.request.query_params.get("category")
        vendor = self.request.query_params.get("vendor")
        delivery_format = self.request.query_params.get("delivery_format")
        if category:
            qs = qs.filter(category=category)
        if vendor:
            qs = qs.filter(vendor__id=vendor)
        if delivery_format:
            qs = qs.filter(delivery_format=delivery_format)
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return AssessmentProductListSerializer
        return AssessmentProductSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=["get"], url_path="featured")
    def featured(self, request):
        qs = self.get_queryset().filter(is_featured=True)
        serializer = AssessmentProductListSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="recommended-for/(?P<job_role>[^/.]+)")
    def recommended_for_role(self, request, pk=None, job_role=None):
        from .models import AssessmentRoleMap
        maps = AssessmentRoleMap.objects.filter(job_role__iexact=job_role).select_related("assessment")
        products = [m.assessment for m in maps.order_by("-relevance_score")[:10]]
        serializer = AssessmentProductListSerializer(products, many=True)
        return Response(serializer.data)


class AssessmentOrderViewSet(viewsets.ModelViewSet):
    serializer_class = AssessmentOrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return AssessmentOrder.objects.filter(purchased_by=user).select_related("assessment", "payment")

    def get_serializer_class(self):
        if self.action == "list":
            return AssessmentOrderListSerializer
        return AssessmentOrderSerializer

    def perform_create(self, serializer):
        serializer.save(purchased_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="deliver")
    def deliver_to_candidate(self, request, pk=None):
        """
        Body: { candidate_id: <uuid>, candidate_email: <email> }
        Creates an AssessmentDelivery record and returns invite details.
        """
        order = self.get_object()
        if order.status not in [AssessmentOrder.OrderStatus.PAID, AssessmentOrder.OrderStatus.IN_DELIVERY]:
            return Response(
                {"detail": "Order must be in paid status before delivering."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from django.contrib.auth import get_user_model
        User = get_user_model()
        candidate_id = request.data.get("candidate_id")
        candidate_email = request.data.get("candidate_email", "")

        if not candidate_id:
            return Response({"detail": "candidate_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        candidate = get_object_or_404(User, pk=candidate_id)
        existing_delivery_count = order.deliveries.count()
        if existing_delivery_count >= order.quantity:
            return Response(
                {"detail": "All assessment seats in this order have been delivered."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        delivery = AssessmentDelivery.objects.create(
            order=order,
            candidate=candidate,
            candidate_email=candidate_email or candidate.email,
        )
        # Move order to IN_DELIVERY when first delivery is created
        if order.status == AssessmentOrder.OrderStatus.PAID:
            order.status = AssessmentOrder.OrderStatus.IN_DELIVERY
            order.save(update_fields=["status"])

        serializer = AssessmentDeliverySerializer(delivery)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AssessmentDeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AssessmentDeliverySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return AssessmentDelivery.objects.filter(candidate=user).select_related("order__assessment")

    @action(detail=True, methods=["get"], url_path="result")
    def my_result(self, request, pk=None):
        delivery = self.get_object()
        try:
            result = delivery.result
        except AssessmentResult.DoesNotExist:
            return Response({"detail": "Result not yet available."}, status=status.HTTP_404_NOT_FOUND)

        if not result.is_visible_to_candidate:
            return Response(
                {"detail": "Your result is not yet released."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = AssessmentResultSerializer(result)
        return Response(serializer.data)


class AssessmentResultViewSet(viewsets.ModelViewSet):
    """Admin / vendor endpoint for ingesting results."""
    queryset = AssessmentResult.objects.select_related("delivery__order__assessment").all()
    serializer_class = AssessmentResultSerializer
    permission_classes = [permissions.IsAdminUser]
