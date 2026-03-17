import pytest
from django.contrib.auth import get_user_model
from apps.agencies.models import Agency, AgencyClient, AgencyRecruiter

User = get_user_model()


@pytest.mark.django_db
class TestAgency:
    def test_create_agency(self):
        owner = User.objects.create_user(
            username="owner", email="owner@agencyos.test", password="pass123"
        )
        agency = Agency.objects.create(
            name="Test Agency",
            slug="test-agency",
            owner=owner,
        )
        assert agency.name == "Test Agency"
        assert str(agency) == "Test Agency"

    def test_agency_client(self):
        owner = User.objects.create_user(
            username="owner2", email="owner2@agencyos.test", password="pass123"
        )
        agency = Agency.objects.create(name="Agency 2", slug="agency-2", owner=owner)
        client = AgencyClient.objects.create(
            agency=agency,
            employer_name="TechCorp Ltd",
            employer_ref="techcorp-001",
        )
        assert client.employer_name == "TechCorp Ltd"
        assert "TechCorp" in str(client)

    def test_agency_recruiter(self):
        owner = User.objects.create_user(
            username="owner3", email="owner3@agencyos.test", password="pass123"
        )
        recruiter_user = User.objects.create_user(
            username="recruiter1", email="recruiter1@agencyos.test", password="pass123"
        )
        agency = Agency.objects.create(name="Agency 3", slug="agency-3", owner=owner)
        recruiter = AgencyRecruiter.objects.create(
            agency=agency, user=recruiter_user, role="recruiter"
        )
        assert recruiter.role == "recruiter"
