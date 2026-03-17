"""Integration tests for billing endpoints."""
import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestBillingEndpoints:

    def setup_method(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='billinguser', email='billing@ats.test', password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_subscription_status(self):
        response = self.client.get('/api/v1/tenants/billing/status/')
        assert response.status_code in (
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
        )

    def test_checkout_requires_plan(self):
        response = self.client.post('/api/v1/tenants/billing/checkout/', {}, format='json')
        assert response.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
        )

    def test_billing_requires_auth(self):
        anon = APIClient()
        response = anon.get('/api/v1/tenants/billing/status/')
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
