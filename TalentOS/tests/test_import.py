"""Integration tests for bulk import endpoints."""
import io
import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestImportEndpoints:

    def setup_method(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='importuser', email='import@ats.test', password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def _make_csv(self, content):
        return io.BytesIO(content.encode('utf-8'))

    def test_import_candidates_no_file(self):
        response = self.client.post('/api/v1/import/candidates/', {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_import_candidates_invalid_format(self):
        fake_file = io.BytesIO(b'not a csv')
        fake_file.name = 'data.txt'
        response = self.client.post(
            '/api/v1/import/candidates/',
            {'file': fake_file},
            format='multipart'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_import_candidates_empty_csv(self):
        csv_content = 'first_name,last_name,email\n'
        f = self._make_csv(csv_content)
        f.name = 'candidates.csv'
        response = self.client.post(
            '/api/v1/import/candidates/',
            {'file': f},
            format='multipart'
        )
        # Empty CSV with just header = 0 rows imported
        assert response.status_code in (status.HTTP_201_CREATED, status.HTTP_207_MULTI_STATUS)

    def test_import_requires_auth(self):
        anon = APIClient()
        response = anon.post('/api/v1/import/candidates/', {})
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
