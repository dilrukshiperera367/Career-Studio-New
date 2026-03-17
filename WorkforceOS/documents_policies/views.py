"""Documents & Policies API views + serializers."""

from django.utils import timezone
from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from config.base_api import TenantViewSetMixin, TenantSerializerMixin
from config.permissions import PermissionViewSetMixin
from core_hr.models import Employee
from .models import (
    DocumentTemplate, GeneratedDocument,
    PolicyDocument, PolicyAcknowledgement,
)


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

class DocumentTemplateSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = DocumentTemplate
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class GeneratedDocumentSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = GeneratedDocument
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'generated_at')


class PolicyDocumentSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = PolicyDocument
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class PolicyAcknowledgementSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = PolicyAcknowledgement
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')


# ---------------------------------------------------------------------------
# ViewSets
# ---------------------------------------------------------------------------

class DocumentTemplateViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = DocumentTemplate.objects.all()
    serializer_class = DocumentTemplateSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['template_type', 'is_active']
    search_fields = ['name']
    ordering_fields = ['name', 'created_at', 'updated_at']
    required_permissions = {
        'list': 'documents_policies.manage_templates',
        'retrieve': 'documents_policies.manage_templates',
        'create': 'documents_policies.manage_templates',
        'update': 'documents_policies.manage_templates',
        'partial_update': 'documents_policies.manage_templates',
        'destroy': 'documents_policies.manage_templates',
        'generate': 'documents_policies.manage_templates',
    }

    def get_queryset(self):
        return DocumentTemplate.objects.filter(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        """Generate a new document from this template for an employee."""
        template = self.get_object()

        employee_id = request.data.get('employee_id')
        if not employee_id:
            return Response(
                {'error': 'employee_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            employee = Employee.objects.get(id=employee_id, tenant_id=request.tenant_id)
        except Employee.DoesNotExist:
            return Response(
                {'error': 'Employee not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        variable_overrides = request.data.get('variables', {})

        # Build rendered content by substituting {{key}} placeholders
        content = template.content
        for key, value in variable_overrides.items():
            content = content.replace(f'{{{{{key}}}}}', str(value))

        doc = GeneratedDocument.objects.create(
            tenant_id=request.tenant_id,
            template=template,
            employee=employee,
            title=f"{template.name} — {employee.full_name}",
            content=content,
            status='draft',
            generated_by=request.user,
            variables_used=variable_overrides,
        )
        return Response(
            {'data': GeneratedDocumentSerializer(doc).data},
            status=status.HTTP_201_CREATED,
        )


class GeneratedDocumentViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = GeneratedDocument.objects.select_related('template', 'employee').all()
    serializer_class = GeneratedDocumentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['employee', 'status', 'e_sign_status']
    search_fields = ['title']
    ordering_fields = ['generated_at', 'title']
    required_permissions = {
        'list': 'documents_policies.manage_documents',
        'retrieve': 'documents_policies.manage_documents',
        'create': 'documents_policies.manage_documents',
        'update': 'documents_policies.manage_documents',
        'partial_update': 'documents_policies.manage_documents',
        'destroy': 'documents_policies.manage_documents',
    }

    def get_queryset(self):
        return GeneratedDocument.objects.select_related(
            'template', 'employee'
        ).filter(tenant_id=self.request.tenant_id)


class PolicyDocumentViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = PolicyDocument.objects.all()
    serializer_class = PolicyDocumentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'status', 'is_mandatory']
    search_fields = ['title']
    ordering_fields = ['title', 'effective_date', 'created_at']
    required_permissions = {
        'list': 'documents_policies.manage_policies',
        'retrieve': 'documents_policies.manage_policies',
        'create': 'documents_policies.manage_policies',
        'update': 'documents_policies.manage_policies',
        'partial_update': 'documents_policies.manage_policies',
        'destroy': 'documents_policies.manage_policies',
        'publish': 'documents_policies.manage_policies',
    }

    def get_queryset(self):
        return PolicyDocument.objects.filter(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish the policy document."""
        policy = self.get_object()
        policy.status = 'published'
        policy.save(update_fields=['status', 'updated_at'])
        return Response({'data': PolicyDocumentSerializer(policy).data})


class PolicyAcknowledgementViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = PolicyAcknowledgement.objects.select_related('policy', 'employee').all()
    serializer_class = PolicyAcknowledgementSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['policy', 'employee', 'is_acknowledged']
    ordering_fields = ['acknowledged_at', 'due_date']
    required_permissions = {
        'list': 'documents_policies.manage_acknowledgements',
        'retrieve': 'documents_policies.manage_acknowledgements',
        'create': 'documents_policies.manage_acknowledgements',
        'update': 'documents_policies.manage_acknowledgements',
        'partial_update': 'documents_policies.manage_acknowledgements',
        'destroy': 'documents_policies.manage_acknowledgements',
        'pending_for_me': 'documents_policies.manage_acknowledgements',
        'acknowledge': 'documents_policies.manage_acknowledgements',
    }

    def get_queryset(self):
        return PolicyAcknowledgement.objects.select_related(
            'policy', 'employee'
        ).filter(tenant_id=self.request.tenant_id)

    @action(detail=False, methods=['get'], url_path='pending-for-me')
    def pending_for_me(self, request):
        """Return unacknowledged policies for the current employee."""
        employee = getattr(request.user, 'employee_profile', None)
        if not employee:
            return Response({'data': []})
        qs = self.get_queryset().filter(employee=employee, is_acknowledged=False)
        return Response({'data': PolicyAcknowledgementSerializer(qs, many=True).data})

    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Mark this policy acknowledgement as acknowledged."""
        ack = self.get_object()
        ack.is_acknowledged = True
        ack.acknowledged_at = timezone.now()
        ip = (
            request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
            or request.META.get('REMOTE_ADDR')
        )
        ack.ip_address = ip or None
        ack.save(update_fields=['is_acknowledged', 'acknowledged_at', 'ip_address'])
        return Response({'data': PolicyAcknowledgementSerializer(ack).data})
