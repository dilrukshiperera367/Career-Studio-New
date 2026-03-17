from rest_framework import serializers
from .models import CampusEvent, EventFeedback, EventRegistration, EventSpeaker


class EventSpeakerSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventSpeaker
        fields = "__all__"
        read_only_fields = ["id"]


class CampusEventListSerializer(serializers.ModelSerializer):
    registered_count = serializers.SerializerMethodField()

    class Meta:
        model = CampusEvent
        fields = [
            "id", "title", "event_type", "start_datetime", "end_datetime", "mode",
            "venue_name", "status", "employer", "registered_count", "max_capacity", "is_mandatory",
        ]

    def get_registered_count(self, obj):
        return obj.registrations.filter(waitlisted=False).count()


class CampusEventDetailSerializer(serializers.ModelSerializer):
    speakers = EventSpeakerSerializer(many=True, read_only=True)
    registered_count = serializers.SerializerMethodField()

    class Meta:
        model = CampusEvent
        fields = "__all__"
        read_only_fields = ["id", "campus"]

    def get_registered_count(self, obj):
        return obj.registrations.filter(waitlisted=False).count()


class EventRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventRegistration
        fields = "__all__"
        read_only_fields = ["id", "student", "event", "registration_number", "attended", "check_in_at", "qr_code_data"]


class EventFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventFeedback
        fields = "__all__"
        read_only_fields = ["id"]
