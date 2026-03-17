import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="testrecruiter",
        email="recruiter@agency.test",
        password="testpass123",
        role="recruiter",
    )


@pytest.fixture
def auth_client(client, user):
    client.force_login(user)
    return client
