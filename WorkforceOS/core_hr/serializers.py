"""Core HR serializers — Company, Branch, Department, Position, Employee, Documents."""

from rest_framework import serializers
from config.base_api import TenantSerializerMixin
from .models import Company, Branch, Department, Position, Employee, JobHistory, EmployeeDocument, Announcement


class CompanySerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']


class BranchSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = Branch
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']


class DepartmentSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.name', read_only=True, allow_null=True)
    head_name = serializers.CharField(source='head.full_name', read_only=True, allow_null=True)
    employee_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']

    def get_employee_count(self, obj):
        return obj.employees.filter(status__in=['active', 'probation']).count()


class PositionSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True, allow_null=True)

    class Meta:
        model = Position
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']


class EmployeeListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    department_name = serializers.CharField(source='department.name', read_only=True, allow_null=True)
    position_title = serializers.CharField(source='position.title', read_only=True, allow_null=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True, allow_null=True)
    manager_name = serializers.CharField(source='manager.full_name', read_only=True, allow_null=True)

    class Meta:
        model = Employee
        fields = ['id', 'employee_number', 'first_name', 'last_name', 'photo_url',
                  'work_email', 'mobile_phone', 'department_name', 'position_title',
                  'branch_name', 'manager_name', 'hire_date', 'status', 'contract_type']


class EmployeeDetailSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    """Full serializer for detail view / create / update."""
    department_name = serializers.CharField(source='department.name', read_only=True, allow_null=True)
    position_title = serializers.CharField(source='position.title', read_only=True, allow_null=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True, allow_null=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    manager_name = serializers.CharField(source='manager.full_name', read_only=True, allow_null=True)

    class Meta:
        model = Employee
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'employee_number', 'created_at', 'updated_at', 'created_by']


class JobHistorySerializer(serializers.ModelSerializer):
    prev_position_title = serializers.CharField(source='prev_position.title', read_only=True, allow_null=True)
    new_position_title = serializers.CharField(source='new_position.title', read_only=True, allow_null=True)
    prev_department_name = serializers.CharField(source='prev_department.name', read_only=True, allow_null=True)
    new_department_name = serializers.CharField(source='new_department.name', read_only=True, allow_null=True)

    class Meta:
        model = JobHistory
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']


class JobChangeSerializer(serializers.Serializer):
    """Input serializer for job change actions."""
    change_type = serializers.ChoiceField(choices=['promotion', 'transfer', 'redesignation', 'demotion'])
    effective_date = serializers.DateField()
    new_position_id = serializers.UUIDField(required=False)
    new_department_id = serializers.UUIDField(required=False)
    new_branch_id = serializers.UUIDField(required=False)
    new_manager_id = serializers.UUIDField(required=False)
    new_grade = serializers.CharField(required=False, allow_blank=True)
    reason = serializers.CharField(required=False, allow_blank=True)


class EmployeeDocumentSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = EmployeeDocument
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at', 'uploaded_by']


class AnnouncementSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.full_name', read_only=True, allow_null=True)

    class Meta:
        model = Announcement
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']
