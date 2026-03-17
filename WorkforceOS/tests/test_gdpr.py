"""Integration tests for GDPR anonymisation endpoint."""
import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestGdprEndpoints:

    def setup_method(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='gdpradmin', email='gdpr@hrm.test', password='testpass123', is_staff=True
        )
        self.client.force_authenticate(user=self.admin)

    def test_gdpr_delete_nonexistent_employee(self):
        response = self.client.post('/api/v1/employees/99999/gdpr-delete/')
        assert response.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        )

    def test_gdpr_delete_requires_auth(self):
        anon = APIClient()
        assert anon.post('/api/v1/employees/1/gdpr-delete/').status_code in (401, 403)
