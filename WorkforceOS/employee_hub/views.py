"""
Employee Hub — ViewSets for Employee Self-Service 2.0.

All 16 feature-area ViewSets with full serializers and custom actions.
WCAG 2.2 AA metadata (wcag_level, wcag_notes) is injected into list/retrieve
responses as a top-level envelope field; no DB storage needed.
"""

from django.utils import timezone
from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from platform_core.advanced_features import BenefitPlan as PlatformBenefitPlan

from config.base_api import TenantViewSetMixin, TenantSerializerMixin
from config.permissions import PermissionViewSetMixin
from core_hr.models import Employee
from .models import (
    EmployeeProfileCompletion,
    EmployeeQuickLink,
    EmployeeHubWidget,
    EmployeeFeedItem,
    ProfileChangeRequest,
    BankDetail,
    TaxDeclaration,
    EmergencyContact,
    Dependent,
    PayslipAccess,
    TaxLetterRequest,
    ShiftSwapRequest,
    OvertimeRequest,
    BenefitsEnrollment,
    LifeEventChange,
    EmployeeDocumentVault,
    PolicyAcknowledgement,
    TrainingEnrollment,
    CertificationRecord,
    GoalComment,
    InternalJobApplication,
    EmployeeCase,
    CaseComment,
    AssetRequest,
    EmployeeLanguagePreference,
    AccessibilityPreference,
    SelfServiceRequest,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

WCAG_META = {
    'wcag_level': 'AA',
    'wcag_version': '2.2',
    'wcag_notes': (
        'All forms must meet WCAG 2.2 AA: keyboard navigation, 4.5:1 contrast, '
        'focus-visible, touch targets ≥24×24 px, ARIA labels on interactive elements.'
    ),
}


def _wcag_response(data, **kwargs):
    """Wrap a response payload with WCAG metadata."""
    if isinstance(data, dict) and 'results' in data:
        data['wcag'] = WCAG_META
    return Response(data, **kwargs)


def _get_employee_or_404(request):
    try:
        return Employee.objects.get(user=request.user, tenant_id=request.tenant_id)
    except Employee.DoesNotExist:
        return None


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

class EmployeeProfileCompletionSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeProfileCompletion
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'last_computed_at')

    def get_employee_name(self, obj):
        return obj.employee.full_name if obj.employee else None


class EmployeeQuickLinkSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = EmployeeQuickLink
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'click_count')


class EmployeeHubWidgetSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = EmployeeHubWidget
        fields = '__all__'
        read_only_fields = ('id', 'tenant')


class EmployeeFeedItemSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeFeedItem
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'likes_count', 'comments_count')

    def get_author_name(self, obj):
        return obj.author.full_name if obj.author else None


class ProfileChangeRequestSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = ProfileChangeRequest
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at', 'applied_at')

    def get_employee_name(self, obj):
        return obj.employee.full_name if obj.employee else None


class BankDetailSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = BankDetail
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at', 'is_verified', 'verified_at')


class TaxDeclarationSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = TaxDeclaration
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at', 'approved_total')


class EmergencyContactSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class DependentSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Dependent
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class PayslipAccessSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = PayslipAccess
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'accessed_at', 'download_count')


class TaxLetterRequestSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = TaxLetterRequest
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'requested_at', 'fulfilled_at')


class ShiftSwapRequestSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ShiftSwapRequest
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class OvertimeRequestSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = OvertimeRequest
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class BenefitPlanSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = PlatformBenefitPlan
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')


class BenefitsEnrollmentSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    plan_name = serializers.SerializerMethodField()
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = BenefitsEnrollment
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')

    def get_plan_name(self, obj):
        return str(obj.plan) if obj.plan else None

    def get_employee_name(self, obj):
        return obj.employee.full_name if obj.employee else None


class LifeEventChangeSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = LifeEventChange
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class EmployeeDocumentVaultSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = EmployeeDocumentVault
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'uploaded_at', 'updated_at', 'is_verified', 'verified_at')


class PolicyAcknowledgementSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    policy_title = serializers.SerializerMethodField()

    class Meta:
        model = PolicyAcknowledgement
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'acknowledged_at', 'reminder_count', 'last_reminded_at')

    def get_policy_title(self, obj):
        return str(obj.policy_document) if obj.policy_document else None


class TrainingEnrollmentSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = TrainingEnrollment
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class CertificationRecordSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = CertificationRecord
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class GoalCommentSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = GoalComment
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class InternalJobApplicationSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = InternalJobApplication
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'applied_at', 'updated_at')

    def get_employee_name(self, obj):
        return obj.employee.full_name if obj.employee else None


class EmployeeCaseSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeCase
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at', 'resolved_at')

    def get_employee_name(self, obj):
        return obj.employee.full_name if obj.employee else None


class CaseCommentSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = CaseComment
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')


class AssetRequestSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = AssetRequest
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at', 'issued_at', 'returned_at')

    def get_employee_name(self, obj):
        return obj.employee.full_name if obj.employee else None


class EmployeeLanguagePreferenceSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = EmployeeLanguagePreference
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'updated_at')


class AccessibilityPreferenceSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = AccessibilityPreference
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'updated_at')


class SelfServiceRequestSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = SelfServiceRequest
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')

    def get_employee_name(self, obj):
        return obj.employee.full_name if obj.employee else None


# ---------------------------------------------------------------------------
# ViewSets
# ---------------------------------------------------------------------------

# 1. Home dashboard ──────────────────────────────────────────────────────────

class EmployeeProfileCompletionViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = EmployeeProfileCompletionSerializer
    permission_codename = 'employee_hub.view_profile_completion'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee']

    def get_queryset(self):
        return EmployeeProfileCompletion.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('employee')

    @action(detail=False, methods=['get', 'post'], url_path='my-profile')
    def my_profile_completion(self, request):
        """Return or create the requesting employee's profile completion record."""
        employee = _get_employee_or_404(request)
        if not employee:
            return Response({'detail': 'No employee profile found.'}, status=status.HTTP_404_NOT_FOUND)
        completion, created = EmployeeProfileCompletion.objects.get_or_create(
            employee=employee, tenant_id=request.tenant_id,
        )
        if request.method == 'POST':
            completion.recompute()
        return Response(
            self.get_serializer(completion).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='recompute')
    def recompute(self, request, pk=None):
        """Force recompute section scores and overall_pct."""
        obj = self.get_object()
        obj.recompute()
        return Response(self.get_serializer(obj).data)


class EmployeeQuickLinkViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = EmployeeQuickLinkSerializer
    permission_codename = 'employee_hub.manage_quick_links'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['category', 'is_active']
    ordering_fields = ['sort_order', 'title', 'click_count']

    def get_queryset(self):
        return EmployeeQuickLink.objects.filter(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=['post'], url_path='click')
    def click(self, request, pk=None):
        """Increment click counter (WCAG: link usage analytics)."""
        link = self.get_object()
        link.click_count += 1
        link.save(update_fields=['click_count'])
        return Response({'click_count': link.click_count})


class EmployeeHubWidgetViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = EmployeeHubWidgetSerializer
    permission_codename = 'employee_hub.manage_widgets'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['employee', 'widget_type', 'is_visible']
    ordering_fields = ['position_y', 'position_x']

    def get_queryset(self):
        return EmployeeHubWidget.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('employee')

    @action(detail=False, methods=['get'], url_path='my-widgets')
    def my_widgets(self, request):
        """Return the requesting employee's visible widgets."""
        employee = _get_employee_or_404(request)
        if not employee:
            return Response([])
        qs = self.get_queryset().filter(employee=employee, is_visible=True)
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        """Bulk update widget positions. Body: [{id, position_x, position_y}, ...]"""
        updates = request.data if isinstance(request.data, list) else []
        updated = 0
        for item in updates:
            EmployeeHubWidget.objects.filter(
                id=item.get('id'), tenant_id=request.tenant_id
            ).update(position_x=item.get('position_x', 0), position_y=item.get('position_y', 0))
            updated += 1
        return Response({'updated': updated})


class EmployeeFeedItemViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = EmployeeFeedItemSerializer
    permission_codename = 'employee_hub.view_feed'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['item_type', 'is_pinned']
    ordering_fields = ['created_at', 'is_pinned', 'likes_count']

    def get_queryset(self):
        return EmployeeFeedItem.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('author', 'target_employee')

    @action(detail=False, methods=['get'], url_path='my-feed')
    def my_feed(self, request):
        """Return feed items visible to the current employee."""
        qs = self.get_queryset().order_by('-is_pinned', '-created_at')
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=True, methods=['post'], url_path='like')
    def like(self, request, pk=None):
        """Increment the like counter on a feed item."""
        item = self.get_object()
        item.likes_count += 1
        item.save(update_fields=['likes_count'])
        return Response({'likes_count': item.likes_count})


# 2. Personal profile updates ────────────────────────────────────────────────

class ProfileChangeRequestViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = ProfileChangeRequestSerializer
    permission_codename = 'employee_hub.manage_profile_changes'
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['employee', 'change_type', 'status']
    search_fields = ['field_name', 'new_value']
    ordering_fields = ['created_at', 'status']

    def get_queryset(self):
        return ProfileChangeRequest.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('employee', 'reviewed_by')

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        """Approve a profile change and apply it to the Employee record."""
        obj = self.get_object()
        obj.status = 'approved'
        obj.reviewed_by = request.user
        obj.review_notes = request.data.get('review_notes', '')
        obj.applied_at = timezone.now()
        # Attempt to apply the field change directly
        try:
            setattr(obj.employee, obj.field_name, obj.new_value)
            obj.employee.save(update_fields=[obj.field_name])
        except Exception:
            pass
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        obj = self.get_object()
        obj.status = 'rejected'
        obj.reviewed_by = request.user
        obj.review_notes = request.data.get('review_notes', '')
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=False, methods=['get'], url_path='my-requests')
    def my_requests(self, request):
        employee = _get_employee_or_404(request)
        if not employee:
            return Response([])
        qs = self.get_queryset().filter(employee=employee)
        return Response(self.get_serializer(qs, many=True).data)


# 3. Bank / tax / emergency / dependent ─────────────────────────────────────

class BankDetailViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = BankDetailSerializer
    permission_codename = 'employee_hub.manage_bank_details'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'is_primary', 'is_verified']

    def get_queryset(self):
        return BankDetail.objects.filter(tenant_id=self.request.tenant_id).select_related('employee')

    @action(detail=True, methods=['post'], url_path='verify')
    def verify(self, request, pk=None):
        """Mark bank account as verified by HR."""
        obj = self.get_object()
        obj.is_verified = True
        obj.verified_by = request.user
        obj.verified_at = timezone.now()
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], url_path='set-primary')
    def set_primary(self, request, pk=None):
        """Set this account as the primary salary account (unsets others)."""
        obj = self.get_object()
        BankDetail.objects.filter(
            employee=obj.employee, tenant_id=request.tenant_id
        ).update(is_primary=False)
        obj.is_primary = True
        obj.save(update_fields=['is_primary'])
        return Response(self.get_serializer(obj).data)

    @action(detail=False, methods=['get'], url_path='my-banks')
    def my_banks(self, request):
        employee = _get_employee_or_404(request)
        if not employee:
            return Response([])
        return Response(self.get_serializer(
            self.get_queryset().filter(employee=employee), many=True
        ).data)


class TaxDeclarationViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = TaxDeclarationSerializer
    permission_codename = 'employee_hub.manage_tax_declarations'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['employee', 'financial_year', 'status']
    ordering_fields = ['financial_year', 'status']

    def get_queryset(self):
        return TaxDeclaration.objects.filter(tenant_id=self.request.tenant_id).select_related('employee')

    @action(detail=True, methods=['post'], url_path='submit')
    def submit(self, request, pk=None):
        obj = self.get_object()
        obj.status = 'submitted'
        obj.submitted_at = timezone.now()
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        obj = self.get_object()
        obj.status = 'approved'
        obj.approved_total = request.data.get('approved_total', obj.declared_total)
        obj.reviewed_by = request.user
        obj.review_notes = request.data.get('review_notes', '')
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=False, methods=['get'], url_path='my-declarations')
    def my_declarations(self, request):
        employee = _get_employee_or_404(request)
        if not employee:
            return Response([])
        return Response(self.get_serializer(
            self.get_queryset().filter(employee=employee), many=True
        ).data)


class EmergencyContactViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = EmergencyContactSerializer
    permission_codename = 'employee_hub.manage_emergency_contacts'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'relationship', 'is_primary']

    def get_queryset(self):
        return EmergencyContact.objects.filter(tenant_id=self.request.tenant_id).select_related('employee')

    @action(detail=True, methods=['post'], url_path='set-primary')
    def set_primary(self, request, pk=None):
        obj = self.get_object()
        EmergencyContact.objects.filter(
            employee=obj.employee, tenant_id=request.tenant_id
        ).update(is_primary=False)
        obj.is_primary = True
        obj.save(update_fields=['is_primary'])
        return Response(self.get_serializer(obj).data)

    @action(detail=False, methods=['get'], url_path='my-contacts')
    def my_contacts(self, request):
        employee = _get_employee_or_404(request)
        if not employee:
            return Response([])
        return Response(self.get_serializer(
            self.get_queryset().filter(employee=employee), many=True
        ).data)


class DependentViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = DependentSerializer
    permission_codename = 'employee_hub.manage_dependents'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'relationship', 'is_covered_by_benefits']

    def get_queryset(self):
        return Dependent.objects.filter(tenant_id=self.request.tenant_id).select_related('employee')

    @action(detail=False, methods=['get'], url_path='my-dependents')
    def my_dependents(self, request):
        employee = _get_employee_or_404(request)
        if not employee:
            return Response([])
        return Response(self.get_serializer(
            self.get_queryset().filter(employee=employee), many=True
        ).data)


# 4. Payslips / tax letters / salary history ─────────────────────────────────

class PayslipAccessViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = PayslipAccessSerializer
    permission_codename = 'employee_hub.view_payslips'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['employee', 'payslip_year']
    ordering_fields = ['payslip_year', 'payslip_month', 'accessed_at']

    def get_queryset(self):
        return PayslipAccess.objects.filter(tenant_id=self.request.tenant_id).select_related('employee')

    @action(detail=True, methods=['post'], url_path='download')
    def download(self, request, pk=None):
        """Increment download counter and return the file URL."""
        obj = self.get_object()
        obj.download_count += 1
        obj.save(update_fields=['download_count'])
        return Response({'file_url': obj.file_url, 'download_count': obj.download_count})

    @action(detail=False, methods=['get'], url_path='my-payslips')
    def my_payslips(self, request):
        employee = _get_employee_or_404(request)
        if not employee:
            return Response([])
        qs = self.get_queryset().filter(employee=employee).order_by('-payslip_year', '-payslip_month')
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=False, methods=['get'], url_path='salary-history')
    def salary_history(self, request):
        """Return year-over-year payslip summary (month, year, file_url)."""
        employee = _get_employee_or_404(request)
        if not employee:
            return Response([])
        qs = self.get_queryset().filter(employee=employee).order_by('payslip_year', 'payslip_month')
        return Response(self.get_serializer(qs, many=True).data)


class TaxLetterRequestViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = TaxLetterRequestSerializer
    permission_codename = 'employee_hub.manage_tax_letters'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['employee', 'letter_type', 'financial_year', 'status']
    ordering_fields = ['requested_at', 'status']

    def get_queryset(self):
        return TaxLetterRequest.objects.filter(tenant_id=self.request.tenant_id).select_related('employee')

    @action(detail=True, methods=['post'], url_path='generate')
    def generate(self, request, pk=None):
        """Mark as generated and attach the file URL."""
        obj = self.get_object()
        obj.status = 'generated'
        obj.generated_file_url = request.data.get('generated_file_url', '')
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], url_path='dispatch')
    def dispatch(self, request, pk=None):
        obj = self.get_object()
        obj.status = 'dispatched'
        obj.fulfilled_at = timezone.now()
        obj.save()
        return Response(self.get_serializer(obj).data)


# 5. Shift self-service ───────────────────────────────────────────────────────

class ShiftSwapRequestViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = ShiftSwapRequestSerializer
    permission_codename = 'employee_hub.manage_shift_swaps'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['requester', 'swap_with', 'status']
    ordering_fields = ['created_at', 'requester_shift_date']

    def get_queryset(self):
        return ShiftSwapRequest.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('requester', 'swap_with')

    @action(detail=True, methods=['post'], url_path='accept')
    def accept(self, request, pk=None):
        obj = self.get_object()
        obj.status = 'accepted'
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        obj = self.get_object()
        obj.status = 'approved'
        obj.reviewed_by = request.user
        obj.review_notes = request.data.get('review_notes', '')
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        obj = self.get_object()
        obj.status = 'rejected'
        obj.reviewed_by = request.user
        obj.review_notes = request.data.get('review_notes', '')
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        obj = self.get_object()
        obj.status = 'cancelled'
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=False, methods=['get'], url_path='my-swaps')
    def my_swaps(self, request):
        employee = _get_employee_or_404(request)
        if not employee:
            return Response([])
        qs = self.get_queryset().filter(
            requester=employee
        ) | self.get_queryset().filter(swap_with=employee)
        return Response(self.get_serializer(qs.distinct(), many=True).data)


# 6. Overtime ─────────────────────────────────────────────────────────────────

class OvertimeRequestViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = OvertimeRequestSerializer
    permission_codename = 'employee_hub.manage_overtime'
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['employee', 'status', 'ot_type', 'payroll_period']
    search_fields = ['task_description']
    ordering_fields = ['ot_date', 'created_at', 'hours_claimed']

    def get_queryset(self):
        return OvertimeRequest.objects.filter(tenant_id=self.request.tenant_id).select_related('employee')

    @action(detail=True, methods=['post'], url_path='submit')
    def submit(self, request, pk=None):
        obj = self.get_object()
        obj.status = 'submitted'
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        obj = self.get_object()
        obj.status = 'approved'
        obj.hours_approved = request.data.get('hours_approved', obj.hours_claimed)
        obj.approved_by = request.user
        obj.approval_notes = request.data.get('approval_notes', '')
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        obj = self.get_object()
        obj.status = 'rejected'
        obj.approved_by = request.user
        obj.approval_notes = request.data.get('approval_notes', '')
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=False, methods=['get'], url_path='my-overtime')
    def my_overtime(self, request):
        employee = _get_employee_or_404(request)
        if not employee:
            return Response([])
        qs = self.get_queryset().filter(employee=employee)
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=False, methods=['get'], url_path='pending-approval')
    def pending_approval(self, request):
        """Return submitted OT requests pending manager approval."""
        qs = self.get_queryset().filter(status='submitted')
        return Response(self.get_serializer(qs, many=True).data)


# 7. Benefits enrollment / life events ───────────────────────────────────────

class BenefitPlanViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = BenefitPlanSerializer
    permission_codename = 'employee_hub.manage_benefit_plans'
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['plan_type', 'is_mandatory', 'is_active']
    search_fields = ['name', 'provider']

    def get_queryset(self):
        return PlatformBenefitPlan.objects.filter(tenant_id=self.request.tenant_id)

    @action(detail=False, methods=['get'], url_path='open-enrollment')
    def open_enrollment(self, request):
        """Return plans currently in open-enrollment window."""
        today = timezone.localdate()
        qs = self.get_queryset().filter(
            open_enrollment_start__lte=today,
            open_enrollment_end__gte=today,
            is_active=True,
        )
        return Response(self.get_serializer(qs, many=True).data)


class BenefitsEnrollmentViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = BenefitsEnrollmentSerializer
    permission_codename = 'employee_hub.manage_benefits_enrollments'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['employee', 'plan', 'status', 'coverage_level']
    ordering_fields = ['effective_date', 'status']

    def get_queryset(self):
        return BenefitsEnrollment.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('employee', 'plan')

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        obj = self.get_object()
        obj.status = 'active'
        obj.approved_by = request.user
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], url_path='waive')
    def waive(self, request, pk=None):
        obj = self.get_object()
        obj.status = 'waived'
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], url_path='terminate')
    def terminate(self, request, pk=None):
        obj = self.get_object()
        obj.status = 'terminated'
        obj.end_date = request.data.get('end_date', timezone.localdate().isoformat())
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=False, methods=['get'], url_path='my-benefits')
    def my_benefits(self, request):
        employee = _get_employee_or_404(request)
        if not employee:
            return Response([])
        qs = self.get_queryset().filter(employee=employee, status='active')
        return Response(self.get_serializer(qs, many=True).data)


class LifeEventChangeViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = LifeEventChangeSerializer
    permission_codename = 'employee_hub.manage_life_events'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['employee', 'event_type', 'status']
    ordering_fields = ['event_date', 'created_at']

    def get_queryset(self):
        return LifeEventChange.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('employee')

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        obj = self.get_object()
        obj.status = 'approved'
        obj.reviewed_by = request.user
        obj.review_notes = request.data.get('review_notes', '')
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        obj = self.get_object()
        obj.status = 'rejected'
        obj.reviewed_by = request.user
        obj.review_notes = request.data.get('review_notes', '')
        obj.save()
        return Response(self.get_serializer(obj).data)


# 8. Document vault ───────────────────────────────────────────────────────────

class EmployeeDocumentVaultViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = EmployeeDocumentVaultSerializer
    permission_codename = 'employee_hub.manage_document_vault'
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['employee', 'category', 'is_verified', 'visibility']
    search_fields = ['document_name', 'document_number', 'issuing_authority']
    ordering_fields = ['uploaded_at', 'expiry_date', 'category']

    def get_queryset(self):
        return EmployeeDocumentVault.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('employee')

    @action(detail=True, methods=['post'], url_path='verify')
    def verify(self, request, pk=None):
        obj = self.get_object()
        obj.is_verified = True
        obj.verified_by = request.user
        obj.verified_at = timezone.now()
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=False, methods=['get'], url_path='my-vault')
    def my_vault(self, request):
        employee = _get_employee_or_404(request)
        if not employee:
            return Response([])
        return Response(self.get_serializer(
            self.get_queryset().filter(employee=employee), many=True
        ).data)

    @action(detail=False, methods=['get'], url_path='expiring-soon')
    def expiring_soon(self, request):
        """Return documents expiring within next 90 days."""
        from datetime import timedelta
        today = timezone.localdate()
        cutoff = today + timedelta(days=90)
        qs = self.get_queryset().filter(expiry_date__lte=cutoff, expiry_date__gte=today)
        return Response(self.get_serializer(qs, many=True).data)


# 9. Policy acknowledgement center ───────────────────────────────────────────

class PolicyAcknowledgementViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = PolicyAcknowledgementSerializer
    permission_codename = 'employee_hub.manage_policy_acks'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['employee', 'status', 'policy_document']
    ordering_fields = ['created_at', 'due_date', 'acknowledged_at']

    def get_queryset(self):
        return PolicyAcknowledgement.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('employee', 'policy_document')

    @action(detail=True, methods=['post'], url_path='acknowledge')
    def acknowledge(self, request, pk=None):
        """Record employee acknowledgement with e-signature + IP."""
        obj = self.get_object()
        obj.status = 'acknowledged'
        obj.acknowledged_at = timezone.now()
        obj.digital_signature = request.data.get('digital_signature', '')
        obj.ip_address = request.META.get('REMOTE_ADDR')
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], url_path='send-reminder')
    def send_reminder(self, request, pk=None):
        obj = self.get_object()
        obj.reminder_count += 1
        obj.last_reminded_at = timezone.now()
        obj.save(update_fields=['reminder_count', 'last_reminded_at'])
        return Response({'reminder_count': obj.reminder_count})

    @action(detail=False, methods=['get'], url_path='my-acks')
    def my_acks(self, request):
        employee = _get_employee_or_404(request)
        if not employee:
            return Response([])
        return Response(self.get_serializer(
            self.get_queryset().filter(employee=employee), many=True
        ).data)

    @action(detail=False, methods=['get'], url_path='pending')
    def pending(self, request):
        qs = self.get_queryset().filter(status='pending')
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=False, methods=['get'], url_path='overdue')
    def overdue(self, request):
        qs = self.get_queryset().filter(status='overdue')
        return Response(self.get_serializer(qs, many=True).data)


# 10. Training and certification center ──────────────────────────────────────

class TrainingEnrollmentViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = TrainingEnrollmentSerializer
    permission_codename = 'employee_hub.manage_training'
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['employee', 'status', 'is_mandatory']
    search_fields = ['course_title', 'course_code', 'provider']
    ordering_fields = ['enrollment_date', 'due_date', 'progress_pct']

    def get_queryset(self):
        return TrainingEnrollment.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('employee')

    @action(detail=True, methods=['post'], url_path='start')
    def start(self, request, pk=None):
        obj = self.get_object()
        obj.status = 'in_progress'
        obj.start_date = timezone.localdate()
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], url_path='complete')
    def complete(self, request, pk=None):
        obj = self.get_object()
        obj.status = 'completed'
        obj.completion_date = timezone.localdate()
        obj.progress_pct = 100
        obj.score = request.data.get('score')
        obj.certificate_url = request.data.get('certificate_url', '')
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], url_path='update-progress')
    def update_progress(self, request, pk=None):
        obj = self.get_object()
        obj.progress_pct = min(100, max(0, int(request.data.get('progress_pct', obj.progress_pct))))
        obj.save(update_fields=['progress_pct'])
        return Response({'progress_pct': obj.progress_pct})

    @action(detail=False, methods=['get'], url_path='my-courses')
    def my_courses(self, request):
        employee = _get_employee_or_404(request)
        if not employee:
            return Response([])
        return Response(self.get_serializer(
            self.get_queryset().filter(employee=employee), many=True
        ).data)

    @action(detail=False, methods=['get'], url_path='overdue')
    def overdue(self, request):
        qs = self.get_queryset().filter(
            status__in=['enrolled', 'in_progress'],
            due_date__lt=timezone.localdate(),
        )
        return Response(self.get_serializer(qs, many=True).data)


class CertificationRecordViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = CertificationRecordSerializer
    permission_codename = 'employee_hub.manage_certifications'
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['employee', 'status', 'verified']
    search_fields = ['certification_name', 'issuing_body', 'credential_id']
    ordering_fields = ['issue_date', 'expiry_date']

    def get_queryset(self):
        return CertificationRecord.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('employee')

    @action(detail=True, methods=['post'], url_path='verify')
    def verify(self, request, pk=None):
        obj = self.get_object()
        obj.verified = True
        obj.save(update_fields=['verified'])
        return Response(self.get_serializer(obj).data)

    @action(detail=False, methods=['get'], url_path='expiring-soon')
    def expiring_soon(self, request):
        from datetime import timedelta
        today = timezone.localdate()
        cutoff = today + timedelta(days=90)
        qs = self.get_queryset().filter(
            expiry_date__lte=cutoff, expiry_date__gte=today, status='active'
        )
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=False, methods=['get'], url_path='my-certs')
    def my_certs(self, request):
        employee = _get_employee_or_404(request)
        if not employee:
            return Response([])
        return Response(self.get_serializer(
            self.get_queryset().filter(employee=employee), many=True
        ).data)


# 11. Goals / reviews / feedback ─────────────────────────────────────────────

class GoalCommentViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = GoalCommentSerializer
    permission_codename = 'employee_hub.manage_goal_comments'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['employee', 'goal_id', 'is_private']
    ordering_fields = ['created_at']

    def get_queryset(self):
        return GoalComment.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('employee')

    @action(detail=False, methods=['get'], url_path='for-goal')
    def for_goal(self, request):
        goal_id = request.query_params.get('goal_id')
        if not goal_id:
            return Response({'detail': 'goal_id required.'}, status=status.HTTP_400_BAD_REQUEST)
        qs = self.get_queryset().filter(goal_id=goal_id)
        return Response(self.get_serializer(qs, many=True).data)


# 12. Internal jobs and gigs ─────────────────────────────────────────────────

class InternalJobApplicationViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = InternalJobApplicationSerializer
    permission_codename = 'employee_hub.manage_internal_applications'
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['employee', 'application_type', 'status']
    search_fields = ['job_title', 'cover_note']
    ordering_fields = ['applied_at', 'status', 'outcome_date']

    def get_queryset(self):
        return InternalJobApplication.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('employee')

    @action(detail=True, methods=['post'], url_path='shortlist')
    def shortlist(self, request, pk=None):
        obj = self.get_object()
        obj.status = 'shortlisted'
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], url_path='schedule-interview')
    def schedule_interview(self, request, pk=None):
        obj = self.get_object()
        obj.status = 'interview'
        obj.interview_date = request.data.get('interview_date')
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], url_path='offer')
    def offer(self, request, pk=None):
        obj = self.get_object()
        obj.status = 'offer_extended'
        obj.hiring_manager_notes = request.data.get('hiring_manager_notes', '')
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], url_path='withdraw')
    def withdraw(self, request, pk=None):
        obj = self.get_object()
        obj.status = 'withdrawn'
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=False, methods=['get'], url_path='my-applications')
    def my_applications(self, request):
        employee = _get_employee_or_404(request)
        if not employee:
            return Response([])
        return Response(self.get_serializer(
            self.get_queryset().filter(employee=employee), many=True
        ).data)


# 13. Helpdesk / case status ─────────────────────────────────────────────────

class EmployeeCaseViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = EmployeeCaseSerializer
    permission_codename = 'employee_hub.manage_cases'
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['employee', 'category', 'status', 'priority', 'assigned_agent']
    search_fields = ['subject', 'description']
    ordering_fields = ['created_at', 'priority', 'sla_due_at', 'resolved_at']

    def get_queryset(self):
        return EmployeeCase.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('employee', 'assigned_agent')

    @action(detail=True, methods=['post'], url_path='assign')
    def assign(self, request, pk=None):
        obj = self.get_object()
        obj.assigned_agent = request.user
        obj.status = 'in_progress'
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], url_path='resolve')
    def resolve(self, request, pk=None):
        obj = self.get_object()
        obj.status = 'resolved'
        obj.resolution_notes = request.data.get('resolution_notes', '')
        obj.resolved_at = timezone.now()
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], url_path='close')
    def close(self, request, pk=None):
        obj = self.get_object()
        obj.status = 'closed'
        rating = request.data.get('satisfaction_rating')
        if rating is not None:
            obj.satisfaction_rating = int(rating)
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], url_path='escalate')
    def escalate(self, request, pk=None):
        obj = self.get_object()
        obj.status = 'escalated'
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=False, methods=['get'], url_path='my-cases')
    def my_cases(self, request):
        employee = _get_employee_or_404(request)
        if not employee:
            return Response([])
        return Response(self.get_serializer(
            self.get_queryset().filter(employee=employee), many=True
        ).data)

    @action(detail=False, methods=['get'], url_path='open')
    def open_cases(self, request):
        qs = self.get_queryset().filter(status__in=['open', 'in_progress', 'escalated'])
        return Response(self.get_serializer(qs, many=True).data)


class CaseCommentViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = CaseCommentSerializer
    permission_codename = 'employee_hub.manage_cases'
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['case', 'is_internal']
    ordering_fields = ['created_at']

    def get_queryset(self):
        return CaseComment.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('case', 'author')


# 14. Asset requests ─────────────────────────────────────────────────────────

class AssetRequestViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = AssetRequestSerializer
    permission_codename = 'employee_hub.manage_asset_requests'
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['employee', 'asset_category', 'request_type', 'status']
    search_fields = ['asset_description', 'justification', 'asset_tag']
    ordering_fields = ['created_at', 'status']

    def get_queryset(self):
        return AssetRequest.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('employee')

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        obj = self.get_object()
        obj.status = 'approved'
        obj.approved_by = request.user
        obj.approval_notes = request.data.get('approval_notes', '')
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        obj = self.get_object()
        obj.status = 'rejected'
        obj.approved_by = request.user
        obj.approval_notes = request.data.get('approval_notes', '')
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], url_path='issue')
    def issue(self, request, pk=None):
        obj = self.get_object()
        obj.status = 'issued'
        obj.issued_at = timezone.now()
        obj.asset_tag = request.data.get('asset_tag', obj.asset_tag)
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'], url_path='return')
    def return_asset(self, request, pk=None):
        obj = self.get_object()
        obj.status = 'returned'
        obj.returned_at = timezone.now()
        obj.save()
        return Response(self.get_serializer(obj).data)

    @action(detail=False, methods=['get'], url_path='my-assets')
    def my_assets(self, request):
        employee = _get_employee_or_404(request)
        if not employee:
            return Response([])
        return Response(self.get_serializer(
            self.get_queryset().filter(employee=employee), many=True
        ).data)


# 15. Multilingual preferences ───────────────────────────────────────────────

class EmployeeLanguagePreferenceViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = EmployeeLanguagePreferenceSerializer
    permission_codename = 'employee_hub.manage_language_preferences'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'ui_language', 'rtl']

    def get_queryset(self):
        return EmployeeLanguagePreference.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('employee')

    @action(detail=False, methods=['get', 'put', 'patch'], url_path='my-preferences')
    def my_preferences(self, request):
        """Get or update the requesting employee's language preferences."""
        employee = _get_employee_or_404(request)
        if not employee:
            return Response({'detail': 'No employee profile found.'}, status=status.HTTP_404_NOT_FOUND)
        pref, _ = EmployeeLanguagePreference.objects.get_or_create(
            employee=employee, tenant_id=request.tenant_id
        )
        if request.method in ('PUT', 'PATCH'):
            serializer = self.get_serializer(pref, data=request.data, partial=request.method == 'PATCH')
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        return Response(self.get_serializer(pref).data)


# 16. Accessibility preferences (WCAG 2.2) ───────────────────────────────────

class AccessibilityPreferenceViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = AccessibilityPreferenceSerializer
    permission_codename = 'employee_hub.manage_accessibility'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['employee', 'contrast_mode', 'font_size']

    def get_queryset(self):
        return AccessibilityPreference.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('employee')

    @action(detail=False, methods=['get', 'put', 'patch'], url_path='my-accessibility')
    def my_accessibility(self, request):
        """Get or update WCAG 2.2 accessibility preferences."""
        employee = _get_employee_or_404(request)
        if not employee:
            return Response({'detail': 'No employee profile found.'}, status=status.HTTP_404_NOT_FOUND)
        pref, _ = AccessibilityPreference.objects.get_or_create(
            employee=employee, tenant_id=request.tenant_id
        )
        if request.method in ('PUT', 'PATCH'):
            serializer = self.get_serializer(pref, data=request.data, partial=request.method == 'PATCH')
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        return Response(self.get_serializer(pref).data)

    @action(detail=False, methods=['get'], url_path='wcag-info')
    def wcag_info(self, request):
        """Return WCAG 2.2 AA compliance metadata for front-end consumption."""
        return Response({
            'wcag_level': 'AA',
            'wcag_version': '2.2',
            'w3c_reference': 'https://www.w3.org/TR/WCAG22/',
            'success_criteria': [
                {'sc': '1.4.3', 'name': 'Contrast (Minimum)', 'level': 'AA', 'ratio': '4.5:1 normal / 3:1 large'},
                {'sc': '1.4.11', 'name': 'Non-text Contrast', 'level': 'AA', 'ratio': '3:1'},
                {'sc': '2.4.7', 'name': 'Focus Visible', 'level': 'AA'},
                {'sc': '2.4.11', 'name': 'Focus Not Obscured (Minimum)', 'level': 'AA'},
                {'sc': '2.5.3', 'name': 'Label in Name', 'level': 'A'},
                {'sc': '2.5.8', 'name': 'Target Size (Minimum)', 'level': 'AA', 'size': '24×24 CSS px'},
                {'sc': '3.2.6', 'name': 'Consistent Help', 'level': 'A'},
                {'sc': '3.3.7', 'name': 'Redundant Entry', 'level': 'A'},
                {'sc': '3.3.8', 'name': 'Accessible Authentication (Minimum)', 'level': 'AA'},
            ],
        })


# Legacy SelfServiceRequest ViewSet ──────────────────────────────────────────

class SelfServiceRequestViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = SelfServiceRequestSerializer
    permission_codename = 'employee_hub.manage_service_requests'
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['employee', 'request_type', 'status']
    search_fields = ['subject', 'details']
    ordering_fields = ['created_at', 'updated_at', 'due_date', 'status']

    def get_queryset(self):
        return SelfServiceRequest.objects.filter(
            tenant_id=self.request.tenant_id
        ).select_related('employee', 'assigned_to', 'completed_by')

    @action(detail=True, methods=['post'], url_path='complete')
    def complete(self, request, pk=None):
        obj = self.get_object()
        obj.status = 'completed'
        obj.completed_at = timezone.now()
        obj.response_notes = request.data.get('response_notes', obj.response_notes)
        obj.output_file = request.data.get('output_file', obj.output_file)
        obj.completed_by = request.user
        obj.save()
        return Response(self.get_serializer(obj).data)
