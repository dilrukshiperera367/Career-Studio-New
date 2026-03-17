"""Authentication endpoint tests for HRM."""
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
        name='HRM Test Corp',
        slug='hrm-testcorp',
        schema_name='hrm_testcorp',
        status='active',
        trial_ends_at=timezone.now() + timedelta(days=10),
    )


@pytest.fixture
def user(db, tenant):
    return User.objects.create_user(
        email='hrm_test@testcorp.com',
        password='HRMPass123!',
        tenant=tenant,
        is_active=True,
    )


class TestHRMLogin:
    def test_login_returns_tokens(self, api_client, user):
        url = reverse('token_obtain_pair')
        resp = api_client.post(url, {'email': user.email, 'password': 'HRMPass123!'}, format='json')
        assert resp.status_code == 200
        assert 'access' in resp.data

    def test_login_wrong_password(self, api_client, user):
        url = reverse('token_obtain_pair')
        resp = api_client.post(url, {'email': user.email, 'password': 'wrong'}, format='json')
        assert resp.status_code == 401

    def test_logout_endpoint_exists(self, api_client, user):
        login_url = reverse('token_obtain_pair')
        tokens = api_client.post(login_url, {'email': user.email, 'password': 'HRMPass123!'}, format='json').data
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        logout_url = reverse('auth-logout')
        resp = api_client.post(logout_url, {'refresh': tokens['refresh']}, format='json')
        assert resp.status_code == 205
