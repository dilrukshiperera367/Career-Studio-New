"""Platform Core API — Timeline, Notifications, Approvals, Webhooks, Audit, KB, Benefits, Skills, Grievances."""

from rest_framework import viewsets, serializers, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from config.base_api import TenantViewSetMixin, TenantSerializerMixin
from .models import TimelineEvent, Notification, ApprovalRequest, WebhookSubscription, AuditLog
from .advanced_features import (
    KBCategory, KBArticle, BenefitPlan, BenefitEnrollment,
    SkillDefinition, EmployeeSkill, GrievanceCase,
)


# --- Serializers ---

class TimelineEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = TimelineEvent
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']

    def get_actor_name(self, obj):
        return obj.actor.full_name if obj.actor else 'System'


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']


class ApprovalRequestSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    requester_name = serializers.CharField(source='requester.full_name', read_only=True)
    approver_name = serializers.CharField(source='approver.full_name', read_only=True)

    class Meta:
        model = ApprovalRequest
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']


class WebhookSubscriptionSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = WebhookSubscription
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']
        extra_kwargs = {'secret': {'write_only': True}}


class AuditLogSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True, allow_null=True)

    class Meta:
        model = AuditLog
        fields = '__all__'
        read_only_fields = '__all__'


# --- Views ---

class TimelineViewSet(TenantViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = TimelineEvent.objects.select_related('actor').all()
    serializer_class = TimelineEventSerializer
    filterset_fields = ['employee', 'category']
    ordering_fields = ['created_at']


class NotificationViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        notif = self.get_object()
        notif.is_read = True
        notif.read_at = timezone.now()
        notif.save()
        return Response({'data': NotificationSerializer(notif).data})

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        return Response({'meta': {'message': 'All notifications marked as read'}})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({'data': {'count': count}})


class ApprovalViewSet(TenantViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = ApprovalRequest.objects.select_related('requester', 'approver').all()
    serializer_class = ApprovalRequestSerializer
    filterset_fields = ['status', 'entity_type']

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(approver=self.request.user)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        approval = self.get_object()
        approval.status = 'approved'
        approval.decided_at = timezone.now()
        approval.comments = request.data.get('comments', '')
        approval.save()
        return Response({'data': ApprovalRequestSerializer(approval).data})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        approval = self.get_object()
        approval.status = 'rejected'
        approval.decided_at = timezone.now()
        approval.comments = request.data.get('comments', '')
        approval.save()
        return Response({'data': ApprovalRequestSerializer(approval).data})

    @action(detail=False, methods=['get'])
    def pending(self, request):
        pending = self.get_queryset().filter(status='pending')
        return Response({'data': ApprovalRequestSerializer(pending, many=True).data})


class WebhookViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = WebhookSubscription.objects.all()
    serializer_class = WebhookSubscriptionSerializer


class AuditLogViewSet(TenantViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related('user').all()
    serializer_class = AuditLogSerializer
    filterset_fields = ['entity_type', 'action', 'user']
    ordering_fields = ['created_at']


# ──────────────────────────────────────────────────────────────────────────────
# Knowledge Base  (#96 — models without API)
# ──────────────────────────────────────────────────────────────────────────────

class KBCategorySerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = KBCategory
        fields = ['id', 'name', 'slug', 'icon', 'parent', 'sort_order', 'article_count']
        read_only_fields = ['id']


class KBArticleSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.full_name', read_only=True, allow_null=True)

    class Meta:
        model = KBArticle
        fields = [
            'id', 'category', 'title', 'slug', 'content', 'excerpt', 'tags',
            'status', 'is_pinned', 'view_count', 'helpful_count', 'not_helpful_count',
            'author', 'author_name', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'view_count', 'helpful_count', 'not_helpful_count', 'created_at', 'updated_at']


class KBCategoryViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = KBCategory.objects.all()
    serializer_class = KBCategorySerializer
    filterset_fields = ['parent']
    ordering_fields = ['sort_order', 'name']


class KBArticleViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = KBArticle.objects.select_related('category', 'author').all()
    serializer_class = KBArticleSerializer
    filterset_fields = ['category', 'status', 'is_pinned']
    search_fields = ['title', 'excerpt', 'tags']
    ordering_fields = ['created_at', 'updated_at', 'view_count']

    @action(detail=True, methods=['post'])
    def helpful(self, request, pk=None):
        article = self.get_object()
        article.helpful_count += 1
        article.save(update_fields=['helpful_count'])
        return Response({'data': {'helpful_count': article.helpful_count}})

    @action(detail=True, methods=['post'])
    def not_helpful(self, request, pk=None):
        article = self.get_object()
        article.not_helpful_count += 1
        article.save(update_fields=['not_helpful_count'])
        return Response({'data': {'not_helpful_count': article.not_helpful_count}})


# ──────────────────────────────────────────────────────────────────────────────
# Benefits  (#96)
# ──────────────────────────────────────────────────────────────────────────────

class BenefitPlanSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = BenefitPlan
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class BenefitEnrollmentSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = BenefitEnrollment
        fields = '__all__'
        read_only_fields = ['id', 'enrolled_at']

    def get_employee_name(self, obj):
        return str(obj.employee) if obj.employee else ''


class BenefitPlanViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = BenefitPlan.objects.all()
    serializer_class = BenefitPlanSerializer
    filterset_fields = ['plan_type', 'is_active']
    ordering_fields = ['name', 'created_at']


class BenefitEnrollmentViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = BenefitEnrollment.objects.select_related('employee', 'plan').all()
    serializer_class = BenefitEnrollmentSerializer
    filterset_fields = ['employee', 'plan', 'status']
    ordering_fields = ['enrolled_at', 'effective_date']

    def get_queryset(self):
        qs = super().get_queryset()
        employee_id = self.request.query_params.get('employee_id')
        if employee_id:
            qs = qs.filter(employee_id=employee_id)
        return qs


# ──────────────────────────────────────────────────────────────────────────────
# Skill Matrix  (#96)
# ──────────────────────────────────────────────────────────────────────────────

class SkillDefinitionSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = SkillDefinition
        fields = '__all__'
        read_only_fields = ['id']


class EmployeeSkillSerializer(serializers.ModelSerializer):
    skill_name = serializers.CharField(source='skill.name', read_only=True)
    skill_category = serializers.CharField(source='skill.category', read_only=True)

    class Meta:
        model = EmployeeSkill
        fields = '__all__'
        read_only_fields = ['id']


class SkillDefinitionViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = SkillDefinition.objects.all()
    serializer_class = SkillDefinitionSerializer
    filterset_fields = ['category', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['category', 'name']


class EmployeeSkillViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = EmployeeSkill.objects.select_related('employee', 'skill').all()
    serializer_class = EmployeeSkillSerializer
    filterset_fields = ['employee', 'skill', 'verified']
    ordering_fields = ['proficiency_level', 'last_assessed']

    def get_queryset(self):
        qs = super().get_queryset()
        employee_id = self.request.query_params.get('employee_id')
        if employee_id:
            qs = qs.filter(employee_id=employee_id)
        return qs


# ──────────────────────────────────────────────────────────────────────────────
# Grievances  (#96)
# ──────────────────────────────────────────────────────────────────────────────

class GrievanceCaseSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    submitted_by_name = serializers.SerializerMethodField()

    class Meta:
        model = GrievanceCase
        fields = '__all__'
        read_only_fields = ['id', 'case_number', 'created_at', 'updated_at']

    def get_submitted_by_name(self, obj):
        return str(obj.submitted_by) if obj.submitted_by else ''


class GrievanceCaseViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = GrievanceCase.objects.select_related('submitted_by', 'assigned_to').all()
    serializer_class = GrievanceCaseSerializer
    filterset_fields = ['category', 'severity', 'status']
    ordering_fields = ['created_at', 'severity']

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        case = self.get_object()
        user_id = request.data.get('user_id')
        if user_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                case.assigned_to = User.objects.get(pk=user_id)
                case.status = 'under_review'
                case.save(update_fields=['assigned_to', 'status'])
            except User.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'data': GrievanceCaseSerializer(case).data})

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        from django.utils import timezone as tz
        case = self.get_object()
        case.resolution = request.data.get('resolution', '')
        case.resolution_date = tz.now().date()
        case.status = 'resolved'
        case.save(update_fields=['resolution', 'resolution_date', 'status'])
        return Response({'data': GrievanceCaseSerializer(case).data})
