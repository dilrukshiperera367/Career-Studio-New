from rest_framework import serializers
from .models import MessageThread, Message, MessageAttachment, SystemNotification


class MessageAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageAttachment
        fields = "__all__"
        read_only_fields = ["id", "uploaded_at", "is_scanned", "is_safe"]


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    attachments = MessageAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = "__all__"
        read_only_fields = ["id", "sent_at", "is_flagged", "flag_reason", "filtered_body", "status"]

    def get_sender_name(self, obj):
        if obj.sender:
            return obj.sender.get_full_name() or obj.sender.email
        return "System"


class MessageThreadSerializer(serializers.ModelSerializer):
    unread_count = serializers.SerializerMethodField()
    other_participant = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = MessageThread
        fields = "__all__"
        read_only_fields = ["id", "created_at", "unread_a", "unread_b", "last_message_at", "is_flagged"]

    def get_unread_count(self, obj):
        request = self.context.get("request")
        if request and request.user:
            return obj.get_unread_count(request.user)
        return 0

    def get_other_participant(self, obj):
        request = self.context.get("request")
        if not request:
            return None
        user = request.user
        other = obj.participant_b if user == obj.participant_a else obj.participant_a
        return {"id": str(other.id), "name": other.get_full_name() or other.email}

    def get_last_message(self, obj):
        msg = obj.messages.order_by("-sent_at").first()
        if not msg:
            return None
        return {"body": msg.filtered_body or msg.body, "sent_at": msg.sent_at, "is_flagged": msg.is_flagged}


class SystemNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemNotification
        fields = "__all__"
        read_only_fields = ["id", "created_at", "read_at"]
