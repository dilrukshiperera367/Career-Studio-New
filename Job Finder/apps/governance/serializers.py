"""AI Governance serializers."""
from rest_framework import serializers
from .models import AIDecisionLog, BiasMetric, Guardrail


class AIDecisionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIDecisionLog
        fields = [
            "id", "decision_type", "action", "candidate",
            "candidate_name", "job_title", "match_score",
            "inputs", "output", "is_reviewed", "reviewer",
            "reviewed_at", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class BiasMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = BiasMetric
        fields = ["id", "group", "metric_name", "value", "threshold",
                  "status", "measured_at"]
        read_only_fields = ["id", "measured_at"]


class GuardrailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guardrail
        fields = ["id", "name", "description", "is_active", "category",
                  "updated_at"]
        read_only_fields = ["id", "updated_at"]
