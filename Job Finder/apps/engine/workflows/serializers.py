from rest_framework import serializers
from .models import (
    WorkflowDefinition, WorkflowStage, WorkflowInstance,
    WorkflowTask, WorkflowTransition
)


class WorkflowStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowStage
        fields = ['id', 'name', 'slug', 'description', 'order',
                  'is_terminal', 'is_automated', 'required_approvals',
                  'sla_hours', 'color']


class WorkflowDefinitionListSerializer(serializers.ModelSerializer):
    stage_count = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowDefinition
        fields = ['id', 'name', 'slug', 'workflow_type', 'description',
                  'is_default', 'is_active', 'stage_count']

    def get_stage_count(self, obj):
        return obj.stages.count()


class WorkflowDefinitionDetailSerializer(serializers.ModelSerializer):
    stages = WorkflowStageSerializer(many=True, read_only=True)

    class Meta:
        model = WorkflowDefinition
        fields = ['id', 'name', 'slug', 'workflow_type', 'description',
                  'organization', 'is_default', 'is_active', 'config',
                  'stages', 'created_at', 'updated_at']


class WorkflowTaskSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowTask
        fields = ['id', 'title', 'description', 'assigned_to',
                  'assigned_to_name', 'priority', 'status', 'due_date',
                  'completed_at', 'is_blocking', 'requires_human_review',
                  'metadata', 'created_at']
        read_only_fields = ['completed_at']

    def get_assigned_to_name(self, obj):
        return str(obj.assigned_to) if obj.assigned_to else None


class WorkflowTransitionSerializer(serializers.ModelSerializer):
    from_stage_name = serializers.CharField(
        source='from_stage.name', read_only=True, default='Start'
    )
    to_stage_name = serializers.CharField(
        source='to_stage.name', read_only=True, default='End'
    )
    triggered_by_name = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowTransition
        fields = ['id', 'from_stage', 'from_stage_name',
                  'to_stage', 'to_stage_name',
                  'triggered_by', 'triggered_by_name',
                  'trigger_type', 'reason', 'created_at']

    def get_triggered_by_name(self, obj):
        return str(obj.triggered_by) if obj.triggered_by else 'System'


class WorkflowInstanceSerializer(serializers.ModelSerializer):
    workflow_name = serializers.CharField(source='workflow.name', read_only=True)
    current_stage_name = serializers.CharField(
        source='current_stage.name', read_only=True, default=''
    )
    tasks = WorkflowTaskSerializer(many=True, read_only=True)
    recent_transitions = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowInstance
        fields = ['id', 'workflow', 'workflow_name', 'current_stage',
                  'current_stage_name', 'status', 'entity_type', 'entity_id',
                  'assigned_to', 'metadata', 'started_at', 'completed_at',
                  'tasks', 'recent_transitions']

    def get_recent_transitions(self, obj):
        transitions = obj.transitions.all()[:10]
        return WorkflowTransitionSerializer(transitions, many=True).data


class AdvanceWorkflowSerializer(serializers.Serializer):
    """For advancing a workflow to the next stage."""
    to_stage_id = serializers.UUIDField()
    reason = serializers.CharField(required=False, default='')
