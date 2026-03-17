"""Engagement module API — Surveys, Recognition, eNPS."""

from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import F
from django.core.cache import cache

from config.base_api import TenantViewSetMixin, TenantSerializerMixin
from .models import (
    Survey, SurveyResponse, RecognitionEntry,
    StayInterview, LifecycleSurveyTrigger, ManagerActionPlan, ManagerActionItem,
)


# --- Serializers ---

class SurveySerializer(TenantSerializerMixin, serializers.ModelSerializer):
    response_count = serializers.SerializerMethodField()

    class Meta:
        model = Survey
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']

    def get_response_count(self, obj):
        return obj.responses.count()


class SurveyResponseSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = SurveyResponse
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'submitted_at']


class RecognitionEntrySerializer(TenantSerializerMixin, serializers.ModelSerializer):
    from_name = serializers.CharField(source='from_employee.full_name', read_only=True)
    to_name = serializers.CharField(source='to_employee.full_name', read_only=True)

    class Meta:
        model = RecognitionEntry
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at', 'likes_count']


# --- Views ---

class SurveyViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = Survey.objects.all()
    serializer_class = SurveySerializer
    filterset_fields = ['type', 'status']

    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        survey = self.get_object()
        responses = survey.responses.all()
        total = responses.count()
        if survey.type == 'enps' and total > 0:
            scores = list(responses.exclude(nps_score__isnull=True).values_list('nps_score', flat=True))
            promoters = sum(1 for s in scores if s >= 9) / len(scores) * 100 if scores else 0
            detractors = sum(1 for s in scores if s <= 6) / len(scores) * 100 if scores else 0
            enps = round(promoters - detractors, 1)
            return Response({'data': {'total_responses': total, 'enps_score': enps,
                                      'promoters_pct': round(promoters, 1), 'detractors_pct': round(detractors, 1)}})
        return Response({'data': {'total_responses': total, 'responses': SurveyResponseSerializer(responses, many=True).data}})

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        survey = self.get_object()
        employee = getattr(request.user, 'employee_profile', None)
        if SurveyResponse.objects.filter(survey=survey, employee=employee).exists():
            return Response({'error': 'Already submitted'}, status=status.HTTP_400_BAD_REQUEST)
        resp = SurveyResponse.objects.create(
            tenant=survey.tenant, survey=survey, employee=employee,
            answers=request.data.get('answers', {}), nps_score=request.data.get('nps_score'))
        return Response({'data': SurveyResponseSerializer(resp).data}, status=status.HTTP_201_CREATED)


class RecognitionViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = RecognitionEntry.objects.select_related('from_employee', 'to_employee').all()
    serializer_class = RecognitionEntrySerializer
    filterset_fields = ['category']
    ordering_fields = ['created_at', 'likes_count']

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        entry = self.get_object()
        user = request.user
        # Deduplicate: each user may only like once per entry
        like_key = f'recognition_like_{entry.pk}_{user.pk}'
        if cache.get(like_key):
            return Response(
                {'data': {'likes_count': entry.likes_count}, 'meta': {'already_liked': True}},
                status=status.HTTP_200_OK,
            )
        cache.set(like_key, True, timeout=None)  # Permanent until cache cleared
        RecognitionEntry.objects.filter(pk=entry.pk).update(likes_count=F('likes_count') + 1)
        entry.refresh_from_db(fields=['likes_count'])
        return Response({'data': {'likes_count': entry.likes_count}})


# =============================================================================
# P1 Upgrades — Stay Interviews, Lifecycle Triggers, Manager Action Plans
# =============================================================================

class StayInterviewSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    interviewer_name = serializers.CharField(source='interviewer.full_name', read_only=True, allow_null=True)

    class Meta:
        model = StayInterview
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']


class LifecycleSurveyTriggerSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    survey_title = serializers.CharField(source='survey.title', read_only=True)

    class Meta:
        model = LifecycleSurveyTrigger
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']


class ManagerActionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManagerActionItem
        fields = '__all__'
        read_only_fields = ['id']


class ManagerActionPlanSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    manager_name = serializers.CharField(source='manager.full_name', read_only=True)
    items = ManagerActionItemSerializer(many=True, read_only=True)

    class Meta:
        model = ManagerActionPlan
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']


class StayInterviewViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = StayInterview.objects.select_related('employee', 'interviewer').all()
    serializer_class = StayInterviewSerializer
    filterset_fields = ['employee', 'status']
    ordering_fields = ['scheduled_date', 'created_at']


class LifecycleSurveyTriggerViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = LifecycleSurveyTrigger.objects.select_related('survey').all()
    serializer_class = LifecycleSurveyTriggerSerializer
    filterset_fields = ['trigger_event', 'is_active']


class ManagerActionPlanViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = ManagerActionPlan.objects.select_related('manager', 'survey').prefetch_related('items').all()
    serializer_class = ManagerActionPlanSerializer
    filterset_fields = ['manager', 'status']
    ordering_fields = ['due_date', 'created_at']

    @action(detail=True, methods=['get'])
    def items(self, request, pk=None):
        plan = self.get_object()
        return Response({'data': ManagerActionItemSerializer(plan.items.all(), many=True).data})


class ManagerActionItemViewSet(viewsets.ModelViewSet):
    from rest_framework.permissions import IsAuthenticated
    permission_classes = [IsAuthenticated]
    serializer_class = ManagerActionItemSerializer
    filterset_fields = ['plan', 'status', 'assigned_to']

    def get_queryset(self):
        return ManagerActionItem.objects.filter(
            plan__tenant_id=self.request.tenant_id
        )

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        from django.utils import timezone
        item = self.get_object()
        item.status = 'completed'
        item.completed_at = timezone.now()
        item.save(update_fields=['status', 'completed_at'])
        return Response({'data': ManagerActionItemSerializer(item).data})
