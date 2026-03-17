"""Candidate API tests."""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.tenants.models import Tenant
from apps.accounts.models import User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def tenant(db):
    from django.utils import timezone
    from datetime import timedelta
    return Tenant.objects.create(name='Test Corp', subdomain='testcorp2', status='active',
                                 trial_ends_at=timezone.now() + timedelta(days=10))


@pytest.fixture
def user(db, tenant):
    return User.objects.create_superuser(
        email='admin2@testcorp.com',
        password='TestPass123!',
        tenant=tenant,
    )


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


class TestCandidateList:
    def test_list_requires_auth(self, api_client):
        url = reverse('candidate-list')
        resp = api_client.get(url)
        assert resp.status_code == 401

    def test_list_returns_paginated_result(self, auth_client):
        url = reverse('candidate-list')
        resp = auth_client.get(url)
        assert resp.status_code == 200
        # Pagination response has 'results' key
        assert 'results' in resp.data or isinstance(resp.data, list)

    def test_create_candidate(self, auth_client):
        url = reverse('candidate-list')
        data = {
            'full_name': 'Jane Doe',
            'email': 'jane@example.com',
            'phone': '+1234567890',
            'source': 'manual',
        }
        resp = auth_client.post(url, data, format='json')
        assert resp.status_code in (200, 201)
