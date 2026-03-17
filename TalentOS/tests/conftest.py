"""Shared conftest.py for pytest — provides factories, fixtures, and test database config."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def api_client():
    """Unauthenticated API client."""
    return APIClient()


@pytest.fixture
def user_factory(db):
    """Factory for creating test users with different roles."""
    created = []

    def make(email="test@demo.com", password="TestPass123!", **kwargs):
        defaults = {
            "first_name": kwargs.pop("first_name", "Test"),
            "last_name": kwargs.pop("last_name", "User"),
            "user_type": kwargs.pop("user_type", "company_admin"),
        }
        defaults.update(kwargs)
        user = User.objects.create_user(email=email, password=password, **defaults)
        created.append(user)
        return user

    yield make

    # Cleanup
    for u in created:
        u.delete()


@pytest.fixture
def admin_user(user_factory):
    """Pre-created admin user."""
    return user_factory(email="admin@test.com", user_type="company_admin")


@pytest.fixture
def recruiter_user(user_factory):
    """Pre-created recruiter user."""
    return user_factory(email="recruiter@test.com", user_type="recruiter")


@pytest.fixture
def auth_client(admin_user):
    """Authenticated API client with admin user."""
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def recruiter_client(recruiter_user):
    """Authenticated API client with recruiter user."""
    client = APIClient()
    client.force_authenticate(user=recruiter_user)
    return client


@pytest.fixture
def candidate_factory(db):
    """Factory for creating test candidates."""
    from apps.candidates.models import Candidate

    created = []

    def make(**kwargs):
        defaults = {
            "name": f"Candidate {len(created) + 1}",
            "email": f"candidate{len(created) + 1}@test.com",
            "phone": f"+1-555-{100 + len(created):03d}-0001",
            "source": "test",
        }
        defaults.update(kwargs)
        candidate = Candidate.objects.create(**defaults)
        created.append(candidate)
        return candidate

    yield make

    for c in created:
        c.delete()


@pytest.fixture
def job_factory(db):
    """Factory for creating test jobs."""
    from apps.jobs.models import Job

    created = []

    def make(**kwargs):
        defaults = {
            "title": f"Test Job {len(created) + 1}",
            "department": "Engineering",
            "location": "Remote",
            "status": "open",
        }
        defaults.update(kwargs)
        job = Job.objects.create(**defaults)
        created.append(job)
        return job

    yield make

    for j in created:
        j.delete()


@pytest.fixture
def application_factory(db, candidate_factory, job_factory):
    """Factory for creating test applications."""
    from apps.applications.models import Application

    created = []

    def make(candidate=None, job=None, **kwargs):
        c = candidate or candidate_factory()
        j = job or job_factory()
        defaults = {
            "candidate": c,
            "job": j,
            "status": "active",
            "current_stage_name": "applied",
        }
        defaults.update(kwargs)
        application = Application.objects.create(**defaults)
        created.append(application)
        return application

    yield make

    for a in created:
        a.delete()
