"""
Internal Marketplace — ViewSets for internal job postings, applications, gig projects,
gig participation, mobility profiles, and skill-match suggestions.
"""

from django.utils import timezone
from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from config.base_api import TenantViewSetMixin, TenantSerializerMixin
from config.permissions import PermissionViewSetMixin
from core_hr.models import Employee
from .models import (
    InternalJobPosting,
    InternalApplication,
    GigProject,
    GigParticipation,
    MobilityProfile,
    SkillMatchSuggestion,
)


# ─── Serializers ────────────────────────────────────────────────────────────

class InternalJobPostingSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    department_name = serializers.SerializerMethodField()
    hiring_manager_name = serializers.SerializerMethodField()

    class Meta:
        model = InternalJobPosting
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at', 'applications_count')

    def get_department_name(self, obj):
        return obj.department.name if obj.department else None

    def get_hiring_manager_name(self, obj):
        return obj.hiring_manager.full_name if obj.hiring_manager else None


class InternalApplicationSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    applicant_name = serializers.SerializerMethodField()
    posting_title = serializers.SerializerMethodField()

    class Meta:
        model = InternalApplication
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'applied_at', 'updated_at', 'skill_match_score')

    def get_applicant_name(self, obj):
        return obj.applicant.full_name if obj.applicant else None

    def get_posting_title(self, obj):
        return obj.posting.title if obj.posting else None


class GigProjectSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = GigProject
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at', 'participants_count')

    def get_owner_name(self, obj):
        return obj.owner.full_name if obj.owner else None


class GigParticipationSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    project_title = serializers.SerializerMethodField()

    class Meta:
        model = GigParticipation
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'joined_at')

    def get_employee_name(self, obj):
        return obj.employee.full_name if obj.employee else None

    def get_project_title(self, obj):
        return obj.project.title if obj.project else None


class MobilityProfileSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = MobilityProfile
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'updated_at')

    def get_employee_name(self, obj):
        return obj.employee.full_name if obj.employee else None


class SkillMatchSuggestionSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = SkillMatchSuggestion
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'generated_at', 'match_score', 'matching_skills', 'gap_skills')

    def get_employee_name(self, obj):
        return obj.employee.full_name if obj.employee else None


# ─── ViewSets ───────────────────────────────────────────────────────────────

class InternalJobPostingViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = InternalJobPostingSerializer
    permission_codename = 'internal_marketplace.manage_postings'
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['posting_type', 'department', 'status']
    search_fields = ['title', 'description']
    ordering_fields = ['open_date', 'close_date', 'created_at', 'applications_count']

    def get_queryset(self):
        return InternalJobPosting.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('department', 'position', 'hiring_manager')

    @action(detail=False, methods=['get'], url_path='open')
    def open_postings(self, request):
        """Return all currently open internal job postings."""
        qs = self.get_queryset().filter(status='open').order_by('-open_date')
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class InternalApplicationViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = InternalApplicationSerializer
    permission_codename = 'internal_marketplace.manage_applications'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['posting', 'applicant', 'status']
    ordering_fields = ['applied_at', 'updated_at', 'skill_match_score']

    def get_queryset(self):
        return InternalApplication.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('posting', 'applicant')

    @action(detail=False, methods=['get'], url_path='my-applications')
    def my_applications(self, request):
        """Return all internal applications submitted by the current employee."""
        try:
            employee = Employee.objects.get(user=request.user, tenant_id=request.tenant_id)
        except Employee.DoesNotExist:
            return Response([])

        qs = self.get_queryset().filter(applicant=employee).order_by('-applied_at')
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class GigProjectViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = GigProjectSerializer
    permission_codename = 'internal_marketplace.manage_gigs'
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'owner']
    search_fields = ['title', 'description']
    ordering_fields = ['start_date', 'end_date', 'created_at', 'participants_count']

    def get_queryset(self):
        return GigProject.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('owner')


class GigParticipationViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = GigParticipationSerializer
    permission_codename = 'internal_marketplace.manage_gig_participations'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['project', 'employee', 'status']
    ordering_fields = ['joined_at', 'hours_contributed']

    def get_queryset(self):
        return GigParticipation.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('project', 'employee')


class MobilityProfileViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = MobilityProfileSerializer
    permission_codename = 'internal_marketplace.manage_mobility'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['readiness']
    ordering_fields = ['updated_at']

    def get_queryset(self):
        return MobilityProfile.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('employee', 'target_role')

    @action(detail=False, methods=['get', 'patch'], url_path='my-profile')
    def my_profile(self, request):
        """Get or update the current employee's mobility profile."""
        try:
            employee = Employee.objects.get(user=request.user, tenant_id=request.tenant_id)
        except Employee.DoesNotExist:
            return Response({'detail': 'No employee profile found.'}, status=status.HTTP_404_NOT_FOUND)

        profile, created = MobilityProfile.objects.get_or_create(
            employee=employee,
            tenant_id=request.tenant_id,
        )
        if request.method == 'PATCH':
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        serializer = self.get_serializer(profile)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class SkillMatchSuggestionViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = SkillMatchSuggestionSerializer
    permission_codename = 'internal_marketplace.view_suggestions'
    http_method_names = ['get', 'head', 'options', 'post']
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['employee', 'suggestion_type', 'is_dismissed']
    ordering_fields = ['match_score', 'generated_at']

    def get_queryset(self):
        return SkillMatchSuggestion.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('employee')

    @action(detail=True, methods=['post'], url_path='dismiss')
    def dismiss(self, request, pk=None):
        """Dismiss a skill match suggestion for the current employee."""
        suggestion = self.get_object()
        suggestion.is_dismissed = True
        suggestion.save(update_fields=['is_dismissed'])
        return Response(self.get_serializer(suggestion).data)
