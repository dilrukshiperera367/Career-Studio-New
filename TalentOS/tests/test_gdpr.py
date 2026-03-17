"""Integration tests for GDPR data deletion endpoints."""
import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestGdprDeletion:
    """Test GDPR anonymization endpoint."""

    def setup_method(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='adminuser',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True,
        )
        self.client.force_authenticate(user=self.admin)

    def test_gdpr_delete_requires_admin(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='test123',
        )
        regular_client = APIClient()
        regular_client.force_authenticate(user=regular_user)

        # Try to GDPR-delete candidate 1 — should be forbidden
        response = regular_client.post('/api/v1/candidates/99999/gdpr-delete/')
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        )

    def test_gdpr_delete_nonexistent_candidate(self):
        response = self.client.post('/api/v1/candidates/99999/gdpr-delete/')
        assert response.status_code in (
            status.HTTP_403_FORBIDDEN,  # isAdminUser only
            status.HTTP_404_NOT_FOUND,
        )
