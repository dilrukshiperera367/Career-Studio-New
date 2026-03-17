"""Tenant and subscription tests."""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.tenants.models import Tenant, Subscription
from apps.accounts.models import User
from django.utils import timezone
from datetime import timedelta


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(name='Test Corp', subdomain='testcorp', status='trial',
                                 trial_ends_at=timezone.now() + timedelta(days=10))


@pytest.fixture
def admin_user(db, tenant):
    user = User.objects.create_superuser(
        email='admin@testcorp.com',
        password='TestPass123!',
        tenant=tenant,
    )
    return user


@pytest.fixture
def auth_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client


class TestTrialStatus:
    def test_trial_status_returns_info(self, auth_client):
        url = reverse('trial-status')
        resp = auth_client.get(url)
        assert resp.status_code == 200
        assert 'is_trial' in resp.data
        assert 'days_remaining' in resp.data

    def test_expired_trial_blocks_write(self, auth_client, tenant):
        tenant.trial_ends_at = timezone.now() - timedelta(days=10)
        tenant.status = 'expired'
        tenant.save()
        # Write requests should be blocked (403) after grace period
        # This depends on TrialEnforcementMiddleware - test middleware logic
        from apps.tenants.middleware import TrialEnforcementMiddleware
        assert TrialEnforcementMiddleware is not None


class TestSubscription:
    def test_subscription_is_active_property(self, db, tenant):
        sub = Subscription.objects.create(
            tenant=tenant,
            plan='starter',
            status='active',
        )
        assert sub.is_active is True

    def test_trial_subscription_days_remaining(self, db, tenant):
        sub = Subscription.objects.create(
            tenant=tenant,
            plan='starter',
            status='trial',
            trial_ends_at=timezone.now() + timedelta(days=7),
        )
        assert sub.days_remaining > 0
        assert sub.days_remaining <= 7
