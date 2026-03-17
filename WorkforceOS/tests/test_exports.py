"""Integration tests for HRM CSV/Excel export endpoints."""
import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestExportEndpoints:

    def setup_method(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='exportuser', email='export@hrm.test', password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_export_employees_csv(self):
        response = self.client.get('/api/v1/export/employees/', {'format': 'csv'})
        assert response.status_code == status.HTTP_200_OK
        assert 'text/csv' in response['Content-Type']

    def test_export_employees_xlsx(self):
        response = self.client.get('/api/v1/export/employees/', {'format': 'xlsx'})
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST)

    def test_export_leave_requests_csv(self):
        response = self.client.get('/api/v1/export/leave-requests/', {'format': 'csv'})
        assert response.status_code == status.HTTP_200_OK

    def test_export_payroll_csv(self):
        response = self.client.get('/api/v1/export/payroll/', {'format': 'csv'})
        assert response.status_code == status.HTTP_200_OK

    def test_export_requires_auth(self):
        anon = APIClient()
        assert anon.get('/api/v1/export/employees/').status_code in (401, 403)
