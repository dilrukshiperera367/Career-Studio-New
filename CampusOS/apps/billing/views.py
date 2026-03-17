"""CampusOS — Billing views."""

from rest_framework import generics, permissions
from apps.shared.permissions import IsCampusAdmin
from .models import CampusBillingEvent, CampusInvoice, CampusPlan, CampusSubscription, StudentPremiumPlan
from .serializers import (
    CampusBillingEventSerializer,
    CampusInvoiceSerializer,
    CampusPlanSerializer,
    CampusSubscriptionSerializer,
    StudentPremiumPlanSerializer,
)


class CampusPlanListView(generics.ListAPIView):
    """Public listing of available campus plans."""
    serializer_class = CampusPlanSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return CampusPlan.objects.filter(is_active=True)


class CampusSubscriptionView(generics.RetrieveAPIView):
    """Campus admin views their institution's active subscription."""
    serializer_class = CampusSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated, IsCampusAdmin]

    def get_object(self):
        return CampusSubscription.objects.filter(
            campus=self.request.user.campus, status="active"
        ).select_related("plan").first()


class CampusInvoiceListView(generics.ListAPIView):
    serializer_class = CampusInvoiceSerializer
    permission_classes = [permissions.IsAuthenticated, IsCampusAdmin]

    def get_queryset(self):
        return CampusInvoice.objects.filter(campus=self.request.user.campus).order_by("-created_at")


class CampusBillingEventListView(generics.ListAPIView):
    serializer_class = CampusBillingEventSerializer
    permission_classes = [permissions.IsAuthenticated, IsCampusAdmin]

    def get_queryset(self):
        return CampusBillingEvent.objects.filter(campus=self.request.user.campus).order_by("-created_at")


class MyStudentPlanView(generics.RetrieveAPIView):
    serializer_class = StudentPremiumPlanSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return StudentPremiumPlan.objects.filter(
            student=self.request.user, status="active"
        ).first()
