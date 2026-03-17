"""Integration tests for scoring endpoints."""
import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestScoringEndpoints:

    def setup_method(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='scorer', email='scorer@ats.test', password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_team_scorecard_requires_application_id(self):
        response = self.client.get('/api/v1/scoring/team-scorecard/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'application_id' in str(response.data).lower()

    def test_team_scorecard_nonexistent_application(self):
        response = self.client.get('/api/v1/scoring/team-scorecard/', {'application_id': 99999})
        assert response.status_code in (
            status.HTTP_200_OK,   # returns empty result
            status.HTTP_404_NOT_FOUND,
        )

    def test_team_scorecard_requires_auth(self):
        anon = APIClient()
        response = anon.get('/api/v1/scoring/team-scorecard/', {'application_id': 1})
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_list_scorecard_batches(self):
        response = self.client.get('/api/v1/scoring/batches/')
        assert response.status_code in (
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
        )
