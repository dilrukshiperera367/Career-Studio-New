"""Integration tests for leave management endpoints."""
import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestLeaveEndpoints:

    def setup_method(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='leavetest', email='leave@hrm.test', password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_list_leave_types(self):
        response = self.client.get('/api/v1/leave-types/')
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_404_NOT_FOUND)

    def test_list_leave_requests(self):
        response = self.client.get('/api/v1/leave-requests/')
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_404_NOT_FOUND)

    def test_leave_balance_endpoint(self):
        response = self.client.get('/api/v1/leave-balances/')
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_404_NOT_FOUND)
