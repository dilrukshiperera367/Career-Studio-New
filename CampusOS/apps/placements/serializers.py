"""CampusOS — Placements serializers."""

from rest_framework import serializers
from .models import (
    DriveEligibilityRule,
    DriveOffer,
    DriveSlot,
    PlacementDrive,
    PlacementSeason,
    StudentDriveRegistration,
)


class PlacementSeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlacementSeason
        fields = "__all__"
        read_only_fields = ["id", "campus", "created_at", "updated_at"]


class DriveEligibilityRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriveEligibilityRule
        fields = "__all__"
        read_only_fields = ["id"]


class PlacementDriveSerializer(serializers.ModelSerializer):
    registration_count = serializers.IntegerField(source="registrations.count", read_only=True)
    eligibility_rule = DriveEligibilityRuleSerializer(read_only=True)

    class Meta:
        model = PlacementDrive
        fields = "__all__"
        read_only_fields = [
            "id", "campus", "total_offers", "accepted_offers", "created_at", "updated_at",
        ]


class StudentDriveRegistrationSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    drive_name = serializers.CharField(source="drive.company_name", read_only=True)

    class Meta:
        model = StudentDriveRegistration
        fields = "__all__"
        read_only_fields = [
            "id", "registration_number", "shortlisted_at", "created_at", "updated_at",
        ]


class DriveSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriveSlot
        fields = "__all__"
        read_only_fields = ["id", "booked_count", "created_at", "updated_at"]


class DriveOfferSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    company_name = serializers.CharField(source="drive.company_name", read_only=True)

    class Meta:
        model = DriveOffer
        fields = "__all__"
        read_only_fields = [
            "id", "other_offers_count", "accepted_at", "created_at", "updated_at",
        ]
