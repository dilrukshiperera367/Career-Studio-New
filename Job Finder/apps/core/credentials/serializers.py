from rest_framework import serializers
from .models import Credential, CredentialShare


class CredentialListSerializer(serializers.ModelSerializer):
    is_expired = serializers.BooleanField(read_only=True)
    is_expiring_soon = serializers.BooleanField(read_only=True)

    class Meta:
        model = Credential
        fields = ['id', 'title', 'credential_type', 'status', 'source',
                  'issuer_name', 'issued_date', 'expiry_date',
                  'is_expired', 'is_expiring_soon', 'is_public', 'created_at']


class CredentialDetailSerializer(serializers.ModelSerializer):
    is_expired = serializers.BooleanField(read_only=True)
    is_expiring_soon = serializers.BooleanField(read_only=True)
    linked_skill_names = serializers.SerializerMethodField()

    class Meta:
        model = Credential
        fields = ['id', 'title', 'credential_type', 'status', 'source',
                  'issuer_name', 'issuer_url', 'issuer_logo_url',
                  'issued_date', 'expiry_date', 'credential_url',
                  'credential_id', 'badge_json', 'evidence_url',
                  'description', 'linked_skills', 'linked_skill_names',
                  'is_public', 'is_expired', 'is_expiring_soon',
                  'verified_at', 'created_at', 'updated_at']

    def get_linked_skill_names(self, obj):
        return list(obj.linked_skills.values_list('name', flat=True))


class CredentialCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Credential
        fields = ['title', 'credential_type', 'issuer_name', 'issuer_url',
                  'issued_date', 'expiry_date', 'credential_url',
                  'credential_id', 'badge_json', 'evidence_url',
                  'description', 'linked_skills', 'is_public']


class CredentialShareSerializer(serializers.ModelSerializer):
    credential_title = serializers.CharField(source='credential.title', read_only=True)

    class Meta:
        model = CredentialShare
        fields = ['id', 'credential', 'credential_title', 'shared_with',
                  'shared_at', 'viewed_at', 'expires_at']
        read_only_fields = ['shared_at', 'viewed_at']
