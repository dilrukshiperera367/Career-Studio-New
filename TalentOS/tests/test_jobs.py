"""Job API tests."""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.tenants.models import Tenant
from apps.accounts.models import User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def tenant(db):
    from django.utils import timezone
    from datetime import timedelta
    return Tenant.objects.create(name='Jobs Corp', subdomain='jobscorp', status='active',
                                 trial_ends_at=timezone.now() + timedelta(days=10))


@pytest.fixture
def user(db, tenant):
    return User.objects.create_superuser(
        email='admin@jobscorp.com',
        password='TestPass123!',
        tenant=tenant,
    )


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


class TestJobList:
    def test_list_requires_auth(self, api_client):
        url = reverse('job-list')
        resp = api_client.get(url)
        assert resp.status_code == 401

    def test_list_returns_ok(self, auth_client):
        url = reverse('job-list')
        resp = auth_client.get(url)
        assert resp.status_code == 200

    def test_create_job(self, auth_client, tenant):
        url = reverse('job-list')
        data = {
            'title': 'Software Engineer',
            'department': 'Engineering',
            'employment_type': 'full_time',
            'status': 'draft',
        }
        resp = auth_client.post(url, data, format='json')
        assert resp.status_code in (200, 201)
