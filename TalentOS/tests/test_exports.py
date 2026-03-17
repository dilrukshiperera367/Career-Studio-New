"""Integration tests for CSV/Excel export endpoints."""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestExportEndpoints:
    """Test data export views."""

    def setup_method(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_export_candidates_csv(self):
        response = self.client.get('/api/v1/export/candidates/', {'format': 'csv'})
        assert response.status_code == status.HTTP_200_OK
        assert 'text/csv' in response['Content-Type']

    def test_export_candidates_xlsx(self):
        response = self.client.get('/api/v1/export/candidates/', {'format': 'xlsx'})
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST)
        if response.status_code == status.HTTP_200_OK:
            assert 'spreadsheetml' in response['Content-Type'] or 'octet-stream' in response['Content-Type']

    def test_export_jobs_csv(self):
        response = self.client.get('/api/v1/export/jobs/', {'format': 'csv'})
        assert response.status_code == status.HTTP_200_OK
        assert 'text/csv' in response['Content-Type']

    def test_export_applications_csv(self):
        response = self.client.get('/api/v1/export/applications/', {'format': 'csv'})
        assert response.status_code == status.HTTP_200_OK
        assert 'text/csv' in response['Content-Type']

    def test_export_requires_authentication(self):
        anon_client = APIClient()
        response = anon_client.get('/api/v1/export/candidates/')
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
