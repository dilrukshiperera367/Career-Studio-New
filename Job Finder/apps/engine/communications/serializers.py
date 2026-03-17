from rest_framework import serializers
from .models import CommunicationTemplate, CommunicationMessage, CommunicationPreference


class CommunicationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommunicationTemplate
        fields = ['id', 'name', 'slug', 'channel', 'category',
                  'subject', 'body', 'language', 'is_active',
                  'organization', 'created_at', 'updated_at']


class CommunicationMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommunicationMessage
        fields = ['id', 'template', 'channel', 'category',
                  'sent_by', 'recipient', 'subject', 'body',
                  'status', 'sent_at', 'delivered_at', 'opened_at',
                  'entity_type', 'entity_id', 'created_at']
        read_only_fields = ['sent_at', 'delivered_at', 'opened_at']


class CommunicationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommunicationPreference
        fields = ['email_enabled', 'sms_enabled', 'whatsapp_enabled',
                  'push_enabled', 'in_app_enabled', 'muted_categories',
                  'quiet_hours_start', 'quiet_hours_end',
                  'preferred_language']


class SendMessageSerializer(serializers.Serializer):
    template_slug = serializers.SlugField(required=False)
    channel = serializers.ChoiceField(choices=CommunicationTemplate.CHANNEL_CHOICES)
    recipient_id = serializers.IntegerField()
    subject = serializers.CharField(max_length=500, required=False, default='')
    body = serializers.CharField()
    entity_type = serializers.CharField(max_length=100, required=False, default='')
    entity_id = serializers.UUIDField(required=False)
