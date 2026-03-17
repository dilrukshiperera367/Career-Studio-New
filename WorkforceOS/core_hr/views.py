"""Core HR API views — CRUD for org structure and employees."""

import csv
from django.db import models
from django.http import HttpResponse
from rest_framework import viewsets, serializers, status, filters
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from config.base_api import TenantViewSetMixin, AuditMixin, TenantSerializerMixin
from platform_core.services import emit_timeline_event
from .models import (
    Company, Branch, Department, Position, Employee, JobHistory, EmployeeDocument,
    Announcement, CriticalRole, InternalMobilityProfile,
)
from .serializers import (
    CompanySerializer, BranchSerializer, DepartmentSerializer, PositionSerializer,
    EmployeeListSerializer, EmployeeDetailSerializer,
    JobHistorySerializer, JobChangeSerializer,
    EmployeeDocumentSerializer, AnnouncementSerializer,
)
from .imports import bulk_import_employees


class CompanyViewSet(TenantViewSetMixin, AuditMixin, viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    filterset_fields = ['status']
    search_fields = ['name', 'legal_name']


class BranchViewSet(TenantViewSetMixin, AuditMixin, viewsets.ModelViewSet):
    queryset = Branch.objects.select_related('company').all()
    serializer_class = BranchSerializer
    filterset_fields = ['company', 'status', 'country']
    search_fields = ['name', 'code']


class DepartmentViewSet(TenantViewSetMixin, AuditMixin, viewsets.ModelViewSet):
    queryset = Department.objects.select_related('parent', 'head', 'company').all()
    serializer_class = DepartmentSerializer
    filterset_fields = ['company', 'parent', 'status']
    search_fields = ['name', 'code']

    @action(detail=True, methods=['get'])
    def org_chart(self, request, pk=None):
        """Get department sub-tree for org chart."""
        dept = self.get_object()
        descendants = dept.get_descendants()
        data = DepartmentSerializer([dept] + descendants, many=True).data
        return Response({'data': data})


class PositionViewSet(TenantViewSetMixin, AuditMixin, viewsets.ModelViewSet):
    queryset = Position.objects.select_related('department').all()
    serializer_class = PositionSerializer
    filterset_fields = ['department', 'grade', 'status']
    search_fields = ['title', 'code']


class EmployeeViewSet(TenantViewSetMixin, AuditMixin, viewsets.ModelViewSet):
    queryset = Employee.objects.select_related(
        'company', 'department', 'branch', 'position', 'manager'
    ).all()
    filterset_fields = ['company', 'department', 'branch', 'position', 'status',
                        'contract_type', 'employment_type', 'manager']
    search_fields = ['first_name', 'last_name', 'employee_number', 'work_email',
                     'nic_number', 'mobile_phone']
    ordering_fields = ['employee_number', 'first_name', 'last_name', 'hire_date', 'created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return EmployeeListSerializer
        return EmployeeDetailSerializer

    def perform_create(self, serializer):
        employee = serializer.save(
            tenant_id=self.request.tenant_id,
            created_by=self.request.user
        )
        # Create hire event in timeline
        emit_timeline_event(
            tenant_id=self.request.tenant_id,
            employee=employee,
            event_type='employee.created',
            category='hr',
            title=f'{employee.full_name} joined as {employee.position.title if employee.position else "Employee"}',
            actor=self.request.user,
        )
        # Create hire job history
        JobHistory.objects.create(
            tenant_id=self.request.tenant_id,
            employee=employee,
            change_type='hire',
            effective_date=employee.hire_date,
            new_position=employee.position,
            new_department=employee.department,
            new_branch=employee.branch,
            new_manager=employee.manager,
        )
        self._log_audit(self.request, 'employee.created', 'Employee', employee.id)

    @action(detail=True, methods=['post'], url_path='job-changes')
    def job_change(self, request, pk=None):
        """Record a promotion, transfer, redesignation, or demotion."""
        employee = self.get_object()
        serializer = JobChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Save previous state
        history = JobHistory(
            tenant_id=request.tenant_id,
            employee=employee,
            change_type=data['change_type'],
            effective_date=data['effective_date'],
            prev_position=employee.position,
            prev_department=employee.department,
            prev_branch=employee.branch,
            prev_manager=employee.manager,
            prev_grade=employee.position.grade if employee.position else '',
            reason=data.get('reason', ''),
            approved_by=request.user,
        )

        # Apply changes
        if 'new_position_id' in data:
            employee.position_id = data['new_position_id']
            history.new_position_id = data['new_position_id']
        if 'new_department_id' in data:
            employee.department_id = data['new_department_id']
            history.new_department_id = data['new_department_id']
        if 'new_branch_id' in data:
            employee.branch_id = data['new_branch_id']
            history.new_branch_id = data['new_branch_id']
        if 'new_manager_id' in data:
            employee.manager_id = data['new_manager_id']
            history.new_manager_id = data['new_manager_id']
        if data.get('new_grade'):
            history.new_grade = data['new_grade']

        employee.save()
        history.save()

        # Timeline event
        emit_timeline_event(
            tenant_id=request.tenant_id,
            employee=employee,
            event_type=f'employee.{data["change_type"]}',
            category='hr',
            title=f'{employee.full_name} — {data["change_type"].title()}',
            actor=request.user,
            source_object_type='JobHistory',
            source_object_id=history.id,
        )

        return Response({
            'data': JobHistorySerializer(history).data,
            'meta': {'message': f'{data["change_type"].title()} recorded successfully'}
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='job-history')
    def get_job_history(self, request, pk=None):
        employee = self.get_object()
        history = employee.job_history.all()
        return Response({'data': JobHistorySerializer(history, many=True).data})

    @action(detail=True, methods=['get'], url_path='direct-reports')
    def direct_reports(self, request, pk=None):
        employee = self.get_object()
        reports = Employee.objects.filter(manager=employee, status__in=['active', 'probation'])
        return Response({'data': EmployeeListSerializer(reports, many=True).data})

    @action(detail=True, methods=['get', 'post'], url_path='documents')
    def documents(self, request, pk=None):
        employee = self.get_object()
        if request.method == 'GET':
            docs = employee.documents.all()
            return Response({'data': EmployeeDocumentSerializer(docs, many=True).data})
        elif request.method == 'POST':
            serializer = EmployeeDocumentSerializer(data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            doc = serializer.save(
                tenant_id=request.tenant_id,
                employee=employee,
                uploaded_by=request.user,
            )
            return Response({'data': EmployeeDocumentSerializer(doc).data}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Full-text employee search."""
        q = request.query_params.get('q', '')
        if len(q) < 2:
            return Response({'data': []})
        qs = self.get_queryset().filter(
            status__in=['active', 'probation']
        ).filter(
            models.Q(first_name__icontains=q) |
            models.Q(last_name__icontains=q) |
            models.Q(employee_number__icontains=q) |
            models.Q(work_email__icontains=q)
        )[:25]
        return Response({'data': EmployeeListSerializer(qs, many=True).data})

    @action(detail=False, methods=['post'], url_path='bulk-import', parser_classes=[MultiPartParser])
    def bulk_import(self, request):
        """Endpoint to receive a CSV file and bulk-import employees."""
        if 'file' not in request.FILES:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        file_obj = request.FILES['file']
        if not file_obj.name.endswith('.csv'):
            return Response({'error': 'File must be a CSV'}, status=status.HTTP_400_BAD_REQUEST)

        result = bulk_import_employees(file_obj, request.tenant, request.user)

        if not result['success']:
            return Response({'error': 'Import failed', 'details': result['errors']}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'message': f"Successfully imported {result['count']} employees"}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='export')
    def export_csv(self, request):
        """Export all employees in the tenant to CSV."""
        qs = self.get_queryset().select_related('company', 'department', 'branch', 'position', 'manager')
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="employees_export.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'employee_number', 'first_name', 'last_name', 'work_email',
            'mobile_phone', 'gender', 'nationality', 'hire_date',
            'employment_type', 'contract_type', 'status',
            'company', 'department', 'branch', 'position', 'manager_email',
        ])
        for emp in qs:
            writer.writerow([
                emp.employee_number,
                emp.first_name,
                emp.last_name,
                emp.work_email,
                emp.mobile_phone or '',
                emp.gender or '',
                emp.nationality or '',
                emp.hire_date.isoformat() if emp.hire_date else '',
                emp.employment_type or '',
                emp.contract_type or '',
                emp.status,
                emp.company.name if emp.company else '',
                emp.department.name if emp.department else '',
                emp.branch.name if emp.branch else '',
                emp.position.title if emp.position else '',
                emp.manager.work_email if emp.manager else '',
            ])
        return response

    @action(detail=True, methods=['post'], url_path='photo', parser_classes=[MultiPartParser])
    def upload_photo(self, request, pk=None):
        """Upload or replace the employee profile photo.
        Expects multipart/form-data with key 'photo'.
        """
        employee = self.get_object()
        if 'photo' not in request.FILES:
            return Response({'error': 'No photo file provided'}, status=status.HTTP_400_BAD_REQUEST)

        photo_file = request.FILES['photo']
        allowed_types = ['image/jpeg', 'image/png', 'image/webp']
        if photo_file.content_type not in allowed_types:
            return Response(
                {'error': 'Photo must be JPEG, PNG, or WebP'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if photo_file.size > 5 * 1024 * 1024:  # 5 MB limit
            return Response({'error': 'Photo must be smaller than 5 MB'}, status=status.HTTP_400_BAD_REQUEST)

        # Try to upload to MinIO/S3 via django-storages; fall back to local media storage
        try:
            from django.core.files.storage import default_storage
            import os
            ext = photo_file.name.rsplit('.', 1)[-1].lower()
            dest_path = f'employee_photos/{request.tenant_id}/{employee.employee_number}.{ext}'
            # Delete old photo if it exists
            if default_storage.exists(dest_path):
                default_storage.delete(dest_path)
            saved_path = default_storage.save(dest_path, photo_file)
            photo_url = default_storage.url(saved_path)
        except Exception as exc:
            return Response(
                {'error': f'Photo upload failed: {exc}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        employee.photo_url = photo_url
        employee.save(update_fields=['photo_url'])
        emit_timeline_event(
            tenant_id=request.tenant_id,
            employee=employee,
            event_type='employee.photo_updated',
            category='hr',
            title=f'{employee.full_name} — Profile photo updated',
            actor=request.user,
        )
        return Response({'data': {'photo_url': photo_url}, 'meta': {'message': 'Photo uploaded successfully'}})

    @action(detail=True, methods=['post'], url_path='gdpr-delete', permission_classes=[IsAdminUser])
    def gdpr_delete(self, request, pk=None):
        """Anonymize employee PII for GDPR erasure."""
        import uuid as _uuid
        employee = self.get_object()
        anon_id = str(_uuid.uuid4())[:8]
        employee.first_name = 'DELETED'
        employee.last_name = anon_id
        employee.work_email = f'deleted-{anon_id}@gdpr.invalid'
        employee.personal_email = ''
        employee.mobile_phone = ''
        employee.home_phone = ''
        employee.address_current = {}
        employee.address_permanent = {}
        employee.status = 'terminated'
        employee.save()
        return Response({'detail': 'Employee data has been anonymized per GDPR request.'})


class AnnouncementViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = Announcement.objects.select_related('author').all()
    serializer_class = AnnouncementSerializer
    filterset_fields = ['is_published']
    search_fields = ['title', 'body']
    ordering_fields = ['published_at', 'created_at']


# =============================================================================
# P1 Upgrades — Critical Roles & Internal Mobility Profiles
# =============================================================================

class CriticalRoleSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    position_title = serializers.CharField(source='position.title', read_only=True)
    flagged_by_name = serializers.SerializerMethodField()

    class Meta:
        model = CriticalRole
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']

    def get_flagged_by_name(self, obj):
        return obj.flagged_by.get_full_name() if obj.flagged_by else None


class InternalMobilityProfileSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)

    class Meta:
        model = InternalMobilityProfile
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'last_updated']


class CriticalRoleViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = CriticalRole.objects.select_related('position', 'flagged_by').all()
    serializer_class = CriticalRoleSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['impact_if_vacant', 'position']
    search_fields = ['position__title', 'rationale']
    ordering_fields = ['created_at', 'review_date']

    def perform_create(self, serializer):
        serializer.save(flagged_by=self.request.user)


class InternalMobilityProfileViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = InternalMobilityProfile.objects.select_related('employee').prefetch_related('preferred_departments').all()
    serializer_class = InternalMobilityProfileSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['open_to_move', 'employee']
    ordering_fields = ['last_updated']
