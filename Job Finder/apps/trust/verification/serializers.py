from rest_framework import serializers
from .models import EmployerVerification, RecruiterVerification, FraudReport, TrustScore


class EmployerVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployerVerification
        fields = ['id', 'employer', 'status', 'method', 'domain',
                  'verified_at', 'expires_at', 'created_at']
        read_only_fields = ['status', 'verified_at']


class RecruiterVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecruiterVerification
        fields = ['id', 'user', 'employer', 'status', 'linkedin_url',
                  'trust_score', 'verified_at', 'created_at']
        read_only_fields = ['status', 'trust_score', 'verified_at']


class FraudReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = FraudReport
        fields = ['id', 'reported_by', 'report_type', 'entity_type',
                  'entity_id', 'description', 'evidence_urls', 'status',
                  'risk_score', 'created_at']
        read_only_fields = ['reported_by', 'status', 'risk_score']


class TrustScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrustScore
        fields = ['entity_type', 'entity_id', 'overall_score',
                  'verification_score', 'activity_score', 'report_score',
                  'last_computed']
