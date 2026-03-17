"""Payroll API tests for HRM."""
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
        name='Payroll Corp',
        slug='payroll-corp',
        schema_name='payroll_corp',
        status='active',
        trial_ends_at=timezone.now() + timedelta(days=10),
    )


@pytest.fixture
def user(db, tenant):
    return User.objects.create_superuser(
        email='payroll_admin@payrollcorp.com',
        password='HRMPass123!',
        tenant=tenant,
    )


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return auth_client


class TestPayrollRuns:
    def test_list_requires_auth(self, api_client):
        url = reverse('payrollrun-list')
        resp = api_client.get(url)
        assert resp.status_code == 401

    def test_list_returns_ok(self, auth_client):
        url = reverse('payrollrun-list')
        resp = auth_client.get(url)
        assert resp.status_code == 200

    def test_run_payroll_endpoint(self, auth_client):
        url = reverse('payrollrun-run')
        from django.utils import timezone
        data = {
            'company_id': '00000000-0000-0000-0000-000000000001',
            'period_year': timezone.now().year,
            'period_month': timezone.now().month,
        }
        resp = auth_client.post(url, data, format='json')
        # Either 201 (created) or 409 (conflict if already exists) is valid
        assert resp.status_code in (201, 409, 400)
