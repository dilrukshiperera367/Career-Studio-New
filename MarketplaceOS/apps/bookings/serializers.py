from rest_framework import serializers
from .models import Booking, BookingIntakeResponse, BookingReminder, RecurringPlan, WaitlistEntry


class BookingIntakeResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingIntakeResponse
        fields = "__all__"
        read_only_fields = ["id"]


class BookingReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingReminder
        fields = "__all__"
        read_only_fields = ["id", "sent_at", "is_sent"]


class BookingSerializer(serializers.ModelSerializer):
    intake_responses = BookingIntakeResponseSerializer(many=True, read_only=True)
    reminders = BookingReminderSerializer(many=True, read_only=True)
    buyer_email = serializers.EmailField(source="buyer.email", read_only=True)
    provider_name = serializers.CharField(source="provider.display_name", read_only=True)
    service_title = serializers.CharField(source="service.title", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Booking
        fields = "__all__"
        read_only_fields = [
            "id", "reference", "status", "status_changed_at",
            "reminder_24h_sent", "reminder_1h_sent",
            "review_requested", "review_submitted",
            "created_at", "updated_at",
        ]


class BookingListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing views."""
    buyer_email = serializers.EmailField(source="buyer.email", read_only=True)
    provider_name = serializers.CharField(source="provider.display_name", read_only=True)
    service_title = serializers.CharField(source="service.title", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id", "reference", "status", "status_label",
            "buyer_email", "provider_name", "service_title",
            "start_time", "end_time", "delivery_mode",
            "price_lkr", "currency", "created_at",
        ]


class RecurringPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecurringPlan
        fields = "__all__"
        read_only_fields = ["id", "sessions_completed", "created_at"]


class WaitlistEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = WaitlistEntry
        fields = "__all__"
        read_only_fields = ["id", "notified", "notified_at", "created_at"]
