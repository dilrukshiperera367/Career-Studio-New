"""Messaging serializers."""
from rest_framework import serializers
from .models import MessageThread, Message


class MessageSerializer(serializers.ModelSerializer):
    sender_email = serializers.EmailField(source="sender.email", read_only=True)

    class Meta:
        model = Message
        fields = [
            "id", "thread", "sender", "sender_email", "body",
            "attachment", "is_read", "read_at", "is_system_message", "created_at",
        ]
        read_only_fields = ["id", "sender", "sender_email", "is_read", "read_at", "is_system_message", "created_at"]


class MessageCreateSerializer(serializers.Serializer):
    body = serializers.CharField()
    attachment = serializers.FileField(required=False)


class MessageThreadSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    other_participant = serializers.SerializerMethodField()

    class Meta:
        model = MessageThread
        fields = [
            "id", "job", "application", "subject",
            "last_message_at", "last_message", "unread_count",
            "other_participant", "created_at",
        ]
        read_only_fields = fields

    def get_last_message(self, obj):
        msg = obj.messages.order_by("-created_at").first()
        if msg:
            return {"body": msg.body[:100], "sender": str(msg.sender_id), "created_at": msg.created_at}
        return None

    def get_unread_count(self, obj):
        user = self.context.get("request", {})
        if hasattr(user, "user"):
            user = user.user
            return obj.messages.filter(is_read=False).exclude(sender=user).count()
        return 0

    def get_other_participant(self, obj):
        request = self.context.get("request")
        if request:
            user = request.user
            other = obj.participant_two if obj.participant_one == user else obj.participant_one
            return {"id": str(other.id), "email": other.email}
        return None


class ThreadCreateSerializer(serializers.Serializer):
    recipient_id = serializers.UUIDField()
    job_id = serializers.UUIDField(required=False)
    subject = serializers.CharField(max_length=200, required=False, default="")
    body = serializers.CharField()
