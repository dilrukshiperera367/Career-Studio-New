"""Employee API tests for HRM."""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from authentication.models import User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def tenant(db):
    from tenants.models import Tenant
    from django.utils import timezone
    from datetime import timedelta
    return Tenant.objects.create(
        name='Employees Corp',
        slug='emp-corp',
        schema_name='emp_corp',
        status='active',
        trial_ends_at=timezone.now() + timedelta(days=10),
    )


@pytest.fixture
def user(db, tenant):
    return User.objects.create_superuser(
        email='hr_admin@empcorp.com',
        password='HRMPass123!',
        tenant=tenant,
    )


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


class TestEmployeeList:
    def test_list_requires_auth(self, api_client):
        url = reverse('employee-list')
        resp = api_client.get(url)
        assert resp.status_code == 401

    def test_list_returns_ok(self, auth_client):
        url = reverse('employee-list')
        resp = auth_client.get(url)
        assert resp.status_code == 200
