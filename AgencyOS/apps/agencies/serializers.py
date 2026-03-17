from rest_framework import serializers
from .models import (
    Agency, AgencyClient, AgencyRecruiter, AgencyJobOrder,
    AgencySubmission, AgencyPlacement, AgencyContractor, TalentPool,
)


class AgencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Agency
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class AgencyClientSerializer(serializers.ModelSerializer):
    agency_name = serializers.CharField(source="agency.name", read_only=True)

    class Meta:
        model = AgencyClient
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class AgencyRecruiterSerializer(serializers.ModelSerializer):
    agency_name = serializers.CharField(source="agency.name", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = AgencyRecruiter
        fields = "__all__"
        read_only_fields = ["id", "joined_at", "updated_at"]


class AgencyJobOrderSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.employer_name", read_only=True)
    agency_name = serializers.CharField(source="agency.name", read_only=True)

    class Meta:
        model = AgencyJobOrder
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class AgencySubmissionSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source="job_order.title", read_only=True)
    client_name = serializers.CharField(source="client.employer_name", read_only=True)
    agency_name = serializers.CharField(source="agency.name", read_only=True)

    class Meta:
        model = AgencySubmission
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "ownership_start"]


class AgencyPlacementSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="submission.candidate_name", read_only=True)
    job_title = serializers.CharField(source="submission.job_order.title", read_only=True)
    client_name = serializers.CharField(source="submission.client.employer_name", read_only=True)

    class Meta:
        model = AgencyPlacement
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class AgencyContractorSerializer(serializers.ModelSerializer):
    agency_name = serializers.CharField(source="agency.name", read_only=True)
    current_client_name = serializers.CharField(
        source="current_client.employer_name", read_only=True
    )

    class Meta:
        model = AgencyContractor
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class TalentPoolSerializer(serializers.ModelSerializer):
    agency_name = serializers.CharField(source="agency.name", read_only=True)
    member_count = serializers.SerializerMethodField()

    def get_member_count(self, obj):
        return obj.members.count()

    class Meta:
        model = TalentPool
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]
