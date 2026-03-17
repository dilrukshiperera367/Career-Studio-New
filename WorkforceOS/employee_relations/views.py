"""
Employee Relations — ViewSets for ER cases, case notes, disciplinary actions,
performance improvement plans, and ethics intake.
"""

from django.utils import timezone
from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from config.base_api import TenantViewSetMixin, TenantSerializerMixin
from config.permissions import PermissionViewSetMixin
from .models import (
    ERCase,
    ERCaseNote,
    DisciplinaryAction,
    PImprovementPlan,
    EthicsIntake,
)


# ─── Serializers ────────────────────────────────────────────────────────────

class ERCaseSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    subject_employee_name = serializers.SerializerMethodField()
    complainant_name = serializers.SerializerMethodField()

    class Meta:
        model = ERCase
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at', 'case_number')

    def get_subject_employee_name(self, obj):
        return obj.subject_employee.full_name if obj.subject_employee else None

    def get_complainant_name(self, obj):
        return obj.complainant.full_name if obj.complainant else None


class ERCaseNoteSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    author_display = serializers.SerializerMethodField()
    case_number = serializers.SerializerMethodField()

    class Meta:
        model = ERCaseNote
        fields = '__all__'
        read_only_fields = ('id', 'created_at')

    def get_author_display(self, obj):
        return str(obj.author) if obj.author else None

    def get_case_number(self, obj):
        return obj.case.case_number if obj.case else None

    def create(self, validated_data):
        # ERCaseNote has no tenant FK; delegate straight to super without injecting tenant_id
        request = self.context.get('request')
        if request and not validated_data.get('author_id'):
            validated_data['author'] = request.user
        return super(serializers.ModelSerializer, self).create(validated_data)


class DisciplinaryActionSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = DisciplinaryAction
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')

    def get_employee_name(self, obj):
        return obj.employee.full_name if obj.employee else None


class PImprovementPlanSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    manager_name = serializers.SerializerMethodField()

    class Meta:
        model = PImprovementPlan
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at', 'employee_acknowledged_at')

    def get_employee_name(self, obj):
        return obj.employee.full_name if obj.employee else None

    def get_manager_name(self, obj):
        return obj.manager.full_name if obj.manager else None


class EthicsIntakeSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = EthicsIntake
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at', 'reference_code')


# ─── ViewSets ───────────────────────────────────────────────────────────────

class ERCaseViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = ERCaseSerializer
    permission_codename = 'employee_relations.manage_cases'
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['case_type', 'severity', 'status', 'subject_employee', 'assigned_to']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'updated_at', 'severity', 'sla_resolution_due']

    def get_queryset(self):
        return ERCase.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('subject_employee', 'complainant', 'assigned_to')

    @action(detail=True, methods=['post'], url_path='close')
    def close(self, request, pk=None):
        """Close an ER case."""
        case = self.get_object()
        case.status = 'closed'
        case.closed_at = timezone.now()
        if 'outcome_summary' in request.data:
            case.outcome_summary = request.data['outcome_summary']
        case.save()
        return Response(self.get_serializer(case).data)

    @action(detail=True, methods=['post'], url_path='escalate')
    def escalate(self, request, pk=None):
        """Escalate an ER case to critical severity."""
        case = self.get_object()
        case.severity = 'critical'
        if 'description' in request.data:
            case.description = request.data['description']
        case.save()
        return Response(self.get_serializer(case).data)


class ERCaseNoteViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = ERCaseNoteSerializer
    permission_codename = 'employee_relations.manage_case_notes'
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['case', 'note_type']
    search_fields = ['content']
    ordering_fields = ['created_at']

    def get_queryset(self):
        # ERCaseNote has no direct tenant FK; filter via the parent case
        return ERCaseNote.objects.filter(
            case__tenant_id=self.request.tenant_id
        ).select_related('case', 'author')

    def perform_create(self, serializer):
        # Skip TenantViewSetMixin.perform_create (no tenant field on ERCaseNote)
        serializer.save(author=self.request.user)


class DisciplinaryActionViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = DisciplinaryActionSerializer
    permission_codename = 'employee_relations.manage_disciplinary'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['employee', 'action_type', 'status']
    ordering_fields = ['effective_date', 'created_at', 'expiry_date']

    def get_queryset(self):
        return DisciplinaryAction.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('employee', 'case', 'issued_by')

    @action(detail=True, methods=['post'], url_path='acknowledge')
    def acknowledge(self, request, pk=None):
        """Record employee acknowledgement of a disciplinary action."""
        action_obj = self.get_object()
        action_obj.status = 'acknowledged'
        action_obj.acknowledged_at = timezone.now()
        action_obj.save(update_fields=['status', 'acknowledged_at'])
        return Response(self.get_serializer(action_obj).data)


class PImprovementPlanViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = PImprovementPlanSerializer
    permission_codename = 'employee_relations.manage_pips'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['employee', 'manager', 'status']
    ordering_fields = ['start_date', 'end_date', 'review_date', 'created_at']

    def get_queryset(self):
        return PImprovementPlan.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('employee', 'manager', 'hr_partner', 'related_er_case')

    @action(detail=True, methods=['post'], url_path='acknowledge')
    def acknowledge(self, request, pk=None):
        """Record employee acknowledgement of their PIP."""
        pip = self.get_object()
        pip.employee_acknowledged_at = timezone.now()
        pip.save(update_fields=['employee_acknowledged_at'])
        return Response(self.get_serializer(pip).data)


class EthicsIntakeViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = EthicsIntakeSerializer
    permission_codename = 'employee_relations.manage_ethics'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['category', 'status', 'is_anonymous']
    ordering_fields = ['created_at', 'updated_at', 'status']

    def get_queryset(self):
        return EthicsIntake.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('reporter_employee', 'assigned_to', 'related_er_case')
