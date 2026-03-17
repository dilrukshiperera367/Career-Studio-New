"""Serializers for workflow management."""

from rest_framework import serializers
from .models import AutomationRule, WorkflowExecution


class WorkflowRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationRule
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class WorkflowExecutionSerializer(serializers.ModelSerializer):
    rule_name = serializers.CharField(source="rule.name", read_only=True)

    class Meta:
        model = WorkflowExecution
        fields = "__all__"
        read_only_fields = ["id", "executed_at"]
