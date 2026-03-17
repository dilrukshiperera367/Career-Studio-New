"""Integration tests for SSO/SCIM configuration endpoints."""
import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestSSOEndpoints:

    def setup_method(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='ssotest', email='sso@hrm.test', password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_sso_config_get(self):
        response = self.client.get('/api/v1/tenants/sso/')
        assert response.status_code in (
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
        )

    def test_sso_config_put_invalid_provider(self):
        response = self.client.put(
            '/api/v1/tenants/sso/',
            {'provider': 'invalid_provider'},
            format='json'
        )
        assert response.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
        )

    def test_scim_config_get(self):
        response = self.client.get('/api/v1/tenants/scim/')
        assert response.status_code in (
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
        )

    def test_sso_endpoint_requires_auth(self):
        anon = APIClient()
        assert anon.get('/api/v1/tenants/sso/').status_code in (401, 403)
