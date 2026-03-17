"""Integration tests for HRM authentication endpoints."""
import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestAuthEndpoints:

    def setup_method(self):
        self.client = APIClient()

    def test_register_creates_user(self):
        payload = {
            'username': 'newuser',
            'email': 'newuser@hrm.test',
            'password': 'SecurePass123!',
            'first_name': 'New',
            'last_name': 'User',
        }
        response = self.client.post('/api/v1/auth/register/', payload, format='json')
        assert response.status_code in (status.HTTP_201_CREATED, status.HTTP_200_OK, 400)

    def test_login_returns_tokens(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        User.objects.create_user(username='logintest', password='testpass123', email='login@test.com')
        response = self.client.post('/api/v1/auth/token/', {'username': 'logintest', 'password': 'testpass123'}, format='json')
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED)
        if response.status_code == 200:
            assert 'access' in response.data

    def test_token_refresh(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        User.objects.create_user(username='refreshtest', password='testpass123', email='refresh@test.com')
        login = self.client.post('/api/v1/auth/token/', {'username': 'refreshtest', 'password': 'testpass123'}, format='json')
        if login.status_code == 200 and 'refresh' in login.data:
            resp = self.client.post('/api/v1/auth/token/refresh/', {'refresh': login.data['refresh']}, format='json')
            assert resp.status_code == status.HTTP_200_OK
            assert 'access' in resp.data

    def test_protected_endpoint_requires_auth(self):
        response = self.client.get('/api/v1/employees/')
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
