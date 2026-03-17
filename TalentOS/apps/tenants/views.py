"""Views for tenants app — includes tenant detail, settings, and subscription management."""

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.tenants.models import Tenant, TenantSettings
from apps.accounts.models import Subscription
from apps.tenants.serializers import TenantSerializer, TenantSettingsSerializer, SubscriptionSerializer
from apps.accounts.permissions import IsTenantAdmin, IsAdminUser


@extend_schema(tags=['Tenants'])
class TenantDetailView(generics.RetrieveUpdateAPIView):
    """Get/update current tenant."""
    serializer_class = TenantSerializer
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def get_object(self):
        return Tenant.objects.get(id=self.request.tenant_id)


@extend_schema(tags=['Tenants'])
class TenantSettingsView(generics.RetrieveUpdateAPIView):
    """Get/update tenant settings."""
    serializer_class = TenantSettingsSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_object(self):
        settings, _ = TenantSettings.objects.get_or_create(tenant_id=self.request.tenant_id)
        return settings

    def perform_update(self, serializer):
        """Encrypt the SMTP password before persisting to the database."""
        from apps.shared.encryption import encrypt_value
        validated = serializer.validated_data
        smtp = validated.get("smtp_config", {})
        if smtp and smtp.get("password"):
            smtp = dict(smtp)
            smtp["password"] = encrypt_value(smtp["password"])
            validated["smtp_config"] = smtp
        serializer.save(**validated)


@extend_schema(tags=['Tenants'])
class SubscriptionView(APIView):
    """GET subscription status. PATCH to update plan/billing cycle."""
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def get(self, request):
        try:
            subscription = Subscription.objects.get(tenant_id=request.tenant_id)
        except Subscription.DoesNotExist:
            return Response({"error": "No subscription found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = SubscriptionSerializer(subscription)
        return Response(serializer.data)

    def patch(self, request):
        try:
            subscription = Subscription.objects.get(tenant_id=request.tenant_id)
        except Subscription.DoesNotExist:
            return Response({"error": "No subscription found"}, status=status.HTTP_404_NOT_FOUND)

        allowed_fields = {"plan", "billing_cycle"}
        update_data = {k: v for k, v in request.data.items() if k in allowed_fields}
        serializer = SubscriptionSerializer(subscription, data=update_data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


@extend_schema(tags=['Tenants'])
class TrialStatusView(APIView):
    """GET trial status — days remaining, expiry, grace period info."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            tenant = Tenant.objects.get(id=request.tenant_id)
        except Tenant.DoesNotExist:
            return Response({"error": "Tenant not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "is_trial": tenant.is_trial,
            "trial_ends_at": tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None,
            "days_remaining": tenant.trial_days_remaining,
            "is_expired": tenant.is_trial_expired,
            "is_in_grace_period": tenant.is_in_grace_period,
            "status": tenant.status,
            "plan": tenant.plan,
        })
