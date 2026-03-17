"""Views for tenants — subscription status, trial info, tenant management."""

from datetime import timedelta
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone

from tenants.models import Tenant
from tenants.enterprise import Subscription


class TrialStatusView(APIView):
    """GET trial status — days remaining, expiry, grace period info."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant not found'}, status=status.HTTP_404_NOT_FOUND)

        days_remaining = None
        is_expired = False
        is_in_grace = False

        if tenant.trial_ends_at:
            now = timezone.now()
            if now <= tenant.trial_ends_at:
                days_remaining = max(0, (tenant.trial_ends_at - now).days)
            else:
                is_expired = True
                grace_end = tenant.trial_ends_at + timedelta(days=3)
                is_in_grace = now <= grace_end

        return Response({
            'is_trial': tenant.status == 'trial',
            'trial_ends_at': tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None,
            'days_remaining': days_remaining,
            'is_expired': is_expired,
            'is_in_grace_period': is_in_grace,
            'status': tenant.status,
            'plan': tenant.plan,
        })


class SubscriptionView(APIView):
    """GET subscription details. PATCH to update plan."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            sub = Subscription.objects.get(tenant=tenant)
        except Subscription.DoesNotExist:
            return Response({
                'plan': tenant.plan,
                'status': tenant.status,
                'trial_ends_at': tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None,
                'has_subscription': False,
            })

        return Response({
            'id': str(sub.id),
            'plan': sub.plan,
            'status': sub.status,
            'billing_cycle': sub.billing_cycle,
            'price_per_user': str(sub.price_per_user),
            'max_users': sub.max_users,
            'current_users': sub.current_users,
            'trial_ends_at': sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
            'current_period_start': sub.current_period_start.isoformat() if sub.current_period_start else None,
            'current_period_end': sub.current_period_end.isoformat() if sub.current_period_end else None,
            'days_remaining': sub.days_remaining,
            'is_active': sub.is_active,
            'has_subscription': True,
        })

    def patch(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            sub = Subscription.objects.get(tenant=tenant)
        except Subscription.DoesNotExist:
            return Response({'error': 'No subscription found'}, status=status.HTTP_404_NOT_FOUND)

        allowed_fields = {'plan', 'billing_cycle'}
        for field in allowed_fields:
            if field in request.data:
                setattr(sub, field, request.data[field])
        sub.save()

        return Response({'message': 'Subscription updated', 'plan': sub.plan, 'billing_cycle': sub.billing_cycle})


class TenantDetailView(APIView):
    """GET current tenant info including trial status."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant not found'}, status=status.HTTP_404_NOT_FOUND)

        days_remaining = None
        if tenant.trial_ends_at and tenant.status == 'trial':
            delta = tenant.trial_ends_at - timezone.now()
            days_remaining = max(0, delta.days)

        return Response({
            'id': str(tenant.id),
            'name': tenant.name,
            'slug': tenant.slug,
            'plan': tenant.plan,
            'status': tenant.status,
            'max_employees': tenant.max_employees,
            'trial_ends_at': tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None,
            'trial_days_remaining': days_remaining,
            'created_at': tenant.created_at.isoformat(),
        })
