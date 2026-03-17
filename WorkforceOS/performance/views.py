"""Performance API views + serializers + URLs."""

import logging
from datetime import date

from django.db.models import Avg
from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response

from config.base_api import TenantViewSetMixin, TenantSerializerMixin, AuditMixin
from platform_core.services import emit_timeline_event
from .models import (
    ReviewCycle, PerformanceReview, Goal, Feedback,
    TalentReview, NineBoxPlacement, SuccessionPlan, SuccessionCandidate, PromotionReadiness,
)

logger = logging.getLogger('hrm')


# --- Serializers ---

class ReviewCycleSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    review_count = serializers.SerializerMethodField()
    completion_rate = serializers.SerializerMethodField()

    class Meta:
        model = ReviewCycle
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']

    def get_review_count(self, obj):
        return obj.reviews.count()

    def get_completion_rate(self, obj):
        total = obj.reviews.count()
        if not total:
            return 0
        done = obj.reviews.filter(status__in=['manager_submitted', 'calibrated', 'finalized']).count()
        return round((done / total) * 100)


class PerformanceReviewSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    reviewer_name = serializers.CharField(source='reviewer.full_name', read_only=True, allow_null=True)
    cycle_name = serializers.CharField(source='cycle.name', read_only=True)

    class Meta:
        model = PerformanceReview
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']


class GoalSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    sub_goal_count = serializers.SerializerMethodField()

    class Meta:
        model = Goal
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']

    def get_sub_goal_count(self, obj):
        return obj.sub_goals.count()


class FeedbackSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    from_name = serializers.CharField(source='from_employee.full_name', read_only=True)
    to_name = serializers.CharField(source='to_employee.full_name', read_only=True)

    class Meta:
        model = Feedback
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']


# --- Input Serializers ---

class SelfReviewSubmitSerializer(serializers.Serializer):
    self_rating = serializers.DecimalField(max_digits=3, decimal_places=1, min_value=1, max_value=5)
    self_comments = serializers.CharField(required=False, allow_blank=True)
    strengths = serializers.CharField(required=False, allow_blank=True)
    improvements = serializers.CharField(required=False, allow_blank=True)


class ManagerRatingSerializer(serializers.Serializer):
    manager_rating = serializers.DecimalField(max_digits=3, decimal_places=1, min_value=1, max_value=5)
    manager_comments = serializers.CharField(required=False, allow_blank=True)
    strengths = serializers.CharField(required=False, allow_blank=True)
    improvements = serializers.CharField(required=False, allow_blank=True)


class CalibrationSerializer(serializers.Serializer):
    """Bulk calibration input: list of {review_id, calibrated_rating, comment}."""
    adjustments = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
    )


class GoalProgressSerializer(serializers.Serializer):
    current_value = serializers.DecimalField(max_digits=12, decimal_places=2)
    progress = serializers.IntegerField(min_value=0, max_value=100)
    status = serializers.ChoiceField(choices=['active', 'completed', 'cancelled'], required=False)


# --- Views ---

class ReviewCycleViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = ReviewCycle.objects.all()
    serializer_class = ReviewCycleSerializer
    filterset_fields = ['status', 'type']
    search_fields = ['name']
    ordering_fields = ['start_date', 'end_date', 'created_at']

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Move cycle from draft → active, creating PerformanceReview records for all active employees."""
        from core_hr.models import Employee
        cycle = self.get_object()
        if cycle.status != 'draft':
            return Response({'error': f'Cannot activate cycle in status "{cycle.status}"'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Create review records for all active employees in this tenant
        employees = Employee.objects.filter(
            tenant_id=cycle.tenant_id,
            status__in=['active', 'probation']
        )
        created_count = 0
        for emp in employees:
            _, created = PerformanceReview.objects.get_or_create(
                cycle=cycle,
                employee=emp,
                defaults={
                    'tenant_id': cycle.tenant_id,
                    'reviewer': emp.manager,
                    'status': 'pending',
                }
            )
            if created:
                created_count += 1

        cycle.status = 'active'
        cycle.save()

        logger.info('Review cycle %s activated — %d review records created', cycle.id, created_count)
        return Response({
            'data': ReviewCycleSerializer(cycle).data,
            'meta': {'message': 'Cycle activated', 'reviews_created': created_count}
        })

    @action(detail=True, methods=['post'])
    def close_self_review(self, request, pk=None):
        """Advance cycle from active → in_review (self-review phase closed)."""
        cycle = self.get_object()
        if cycle.status != 'active':
            return Response({'error': 'Cycle must be active to close self-review phase'},
                            status=status.HTTP_400_BAD_REQUEST)
        cycle.status = 'in_review'
        cycle.self_review_deadline = date.today()
        cycle.save()
        return Response({'data': ReviewCycleSerializer(cycle).data,
                         'meta': {'message': 'Self-review phase closed — manager reviews now open'}})

    @action(detail=True, methods=['post'])
    def start_calibration(self, request, pk=None):
        """Advance cycle → calibration status."""
        cycle = self.get_object()
        if cycle.status != 'in_review':
            return Response({'error': 'Cycle must be in_review to start calibration'},
                            status=status.HTTP_400_BAD_REQUEST)
        cycle.status = 'calibration'
        cycle.save()
        return Response({'data': ReviewCycleSerializer(cycle).data,
                         'meta': {'message': 'Calibration phase started'}})

    @action(detail=True, methods=['post'])
    def finalize(self, request, pk=None):
        """Finalize the cycle — lock all calibrated reviews."""
        cycle = self.get_object()
        if cycle.status not in ('calibration', 'in_review'):
            return Response({'error': f'Cannot finalize cycle in status "{cycle.status}"'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Promote calibrated_rating → final_rating for all reviews
        finalized = 0
        for review in cycle.reviews.all():
            if review.status in ('calibrated', 'manager_submitted'):
                review.final_rating = review.calibrated_rating or review.manager_rating
                review.status = 'finalized'
                review.save(update_fields=['final_rating', 'status'])
                finalized += 1

        cycle.status = 'finalized'
        cycle.save()
        return Response({'data': ReviewCycleSerializer(cycle).data,
                         'meta': {'message': 'Cycle finalized', 'reviews_finalized': finalized}})

    @action(detail=True, methods=['post'])
    def calibrate(self, request, pk=None):
        """
        Bulk calibration: adjust multiple review ratings.
        Body: {"adjustments": [{"review_id": "...", "calibrated_rating": 3.5, "comment": "..."}]}
        """
        cycle = self.get_object()
        if cycle.status not in ('calibration', 'in_review'):
            return Response({'error': 'Calibration only allowed during calibration or in_review phase'},
                            status=status.HTTP_400_BAD_REQUEST)

        ser = CalibrationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        updated = []
        errors = []
        for adj in ser.validated_data['adjustments']:
            review_id = adj.get('review_id')
            calibrated_rating = adj.get('calibrated_rating')
            if not review_id or calibrated_rating is None:
                errors.append({'review_id': review_id, 'error': 'review_id and calibrated_rating required'})
                continue

            try:
                review = cycle.reviews.get(id=review_id)
                review.calibrated_rating = calibrated_rating
                review.status = 'calibrated'
                review.calibrated_by = request.user
                if adj.get('comment'):
                    meta = review.metadata or {}
                    meta['calibration_comment'] = adj['comment']
                    review.metadata = meta
                review.save(update_fields=['calibrated_rating', 'status', 'calibrated_by', 'metadata'])
                updated.append(str(review.id))
            except PerformanceReview.DoesNotExist:
                errors.append({'review_id': review_id, 'error': 'Not found in this cycle'})

        return Response({
            'meta': {'updated': len(updated), 'errors': len(errors)},
            'data': {'updated_ids': updated, 'errors': errors},
        })

    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Rating distribution and average for a cycle."""
        cycle = self.get_object()
        reviews = cycle.reviews.all()
        total = reviews.count()
        avg = reviews.aggregate(avg=Avg('final_rating'))['avg']

        distribution = {}
        for i in [1, 2, 3, 4, 5]:
            count = reviews.filter(final_rating__gte=i, final_rating__lt=i + 1).count()
            distribution[str(i)] = count

        return Response({
            'data': {
                'total_reviews': total,
                'average_rating': round(float(avg), 2) if avg else None,
                'distribution': distribution,
                'status_breakdown': {
                    s: reviews.filter(status=s).count()
                    for s in ['pending', 'self_submitted', 'manager_submitted', 'calibrated', 'finalized']
                },
            }
        })


class PerformanceReviewViewSet(TenantViewSetMixin, AuditMixin, viewsets.ModelViewSet):
    queryset = PerformanceReview.objects.select_related('employee', 'reviewer', 'cycle').all()
    serializer_class = PerformanceReviewSerializer
    filterset_fields = ['cycle', 'employee', 'status']
    search_fields = ['employee__first_name', 'employee__last_name']
    ordering_fields = ['created_at', 'final_rating']

    @action(detail=False, methods=['get'])
    def my_reviews(self, request):
        """Reviews where the current user's linked employee record is the subject."""
        from core_hr.models import Employee
        try:
            emp = Employee.objects.get(tenant_id=request.tenant_id, user=request.user)
        except Employee.DoesNotExist:
            return Response({'data': [], 'meta': {'message': 'No employee record for current user'}})

        qs = self.get_queryset().filter(employee=emp).order_by('-created_at')
        ser = PerformanceReviewSerializer(qs, many=True)
        return Response({'data': ser.data})

    @action(detail=False, methods=['get'])
    def my_pending_reviews(self, request):
        """Reviews that the current user is the reviewer for, still in progress."""
        from core_hr.models import Employee
        try:
            emp = Employee.objects.get(tenant_id=request.tenant_id, user=request.user)
        except Employee.DoesNotExist:
            return Response({'data': []})

        qs = self.get_queryset().filter(
            reviewer=emp, status__in=['pending', 'self_submitted']
        ).order_by('cycle__end_date')
        ser = PerformanceReviewSerializer(qs, many=True)
        return Response({'data': ser.data, 'meta': {'count': qs.count()}})

    @action(detail=True, methods=['post'])
    def submit_self_review(self, request, pk=None):
        """
        Employee submits their own self-assessment.
        Body: {self_rating, self_comments, strengths, improvements}
        """
        review = self.get_object()

        # Verify the current user is the employee being reviewed
        from core_hr.models import Employee
        try:
            emp = Employee.objects.get(tenant_id=request.tenant_id, user=request.user)
        except Employee.DoesNotExist:
            return Response({'error': 'No employee record for this user'}, status=status.HTTP_403_FORBIDDEN)

        if review.employee_id != emp.id:
            return Response({'error': 'You can only submit your own self-review'},
                            status=status.HTTP_403_FORBIDDEN)

        if review.status not in ('pending',):
            return Response({'error': f'Self-review already submitted (status: {review.status})'},
                            status=status.HTTP_400_BAD_REQUEST)

        ser = SelfReviewSubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        review.self_rating = d['self_rating']
        review.self_comments = d.get('self_comments', '')
        review.strengths = d.get('strengths', '')
        review.improvements = d.get('improvements', '')
        review.status = 'self_submitted'
        review.save(update_fields=['self_rating', 'self_comments', 'strengths', 'improvements', 'status', 'updated_at'])

        emit_timeline_event(
            tenant_id=request.tenant_id,
            employee=emp,
            event_type='review.self_submitted',
            category='performance',
            title=f'Self-review submitted for {review.cycle.name}',
            actor_type='employee',
            actor_id=str(emp.id),
        )

        return Response({'data': PerformanceReviewSerializer(review).data,
                         'meta': {'message': 'Self-review submitted successfully'}})

    @action(detail=True, methods=['post'])
    def submit_rating(self, request, pk=None):
        """
        Manager submits their rating for an employee.
        Body: {manager_rating, manager_comments, strengths, improvements}
        """
        review = self.get_object()

        # Verify caller is the reviewer or a tenant admin
        from core_hr.models import Employee
        try:
            caller_emp = Employee.objects.get(tenant_id=request.tenant_id, user=request.user)
        except Employee.DoesNotExist:
            caller_emp = None

        is_reviewer = caller_emp and (review.reviewer_id == caller_emp.id)
        is_admin = request.user.is_staff or getattr(request.user, 'is_tenant_admin', False)
        if not (is_reviewer or is_admin):
            return Response({'error': 'Only the assigned reviewer or admin can submit manager rating'},
                            status=status.HTTP_403_FORBIDDEN)

        if review.status not in ('pending', 'self_submitted'):
            return Response({'error': f'Cannot submit manager rating in status "{review.status}"'},
                            status=status.HTTP_400_BAD_REQUEST)

        ser = ManagerRatingSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        review.manager_rating = d['manager_rating']
        review.manager_comments = d.get('manager_comments', '')
        if d.get('strengths'):
            review.strengths = d['strengths']
        if d.get('improvements'):
            review.improvements = d['improvements']
        review.status = 'manager_submitted'
        review.save(update_fields=['manager_rating', 'manager_comments', 'strengths', 'improvements', 'status', 'updated_at'])

        if caller_emp:
            emit_timeline_event(
                tenant_id=request.tenant_id,
                employee=review.employee,
                event_type='review.manager_submitted',
                category='performance',
                title=f'Manager review submitted for {review.cycle.name}',
                actor_type='employee',
                actor_id=str(caller_emp.id),
            )

        return Response({'data': PerformanceReviewSerializer(review).data,
                         'meta': {'message': 'Manager rating submitted successfully'}})

    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Employee acknowledges their finalized review."""
        review = self.get_object()
        if review.status != 'finalized':
            return Response({'error': 'Review must be finalized before acknowledgement'},
                            status=status.HTTP_400_BAD_REQUEST)

        meta = review.metadata or {}
        meta['acknowledged'] = True
        meta['acknowledged_at'] = date.today().isoformat()
        review.metadata = meta
        review.save(update_fields=['metadata'])
        return Response({'data': PerformanceReviewSerializer(review).data,
                         'meta': {'message': 'Review acknowledged'}})


class GoalViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = Goal.objects.select_related('employee').all()
    serializer_class = GoalSerializer
    filterset_fields = ['employee', 'cycle', 'type', 'status']
    ordering_fields = ['due_date', 'progress', 'created_at']

    @action(detail=False, methods=['get'])
    def my_goals(self, request):
        """Goals for the current user's employee record."""
        from core_hr.models import Employee
        try:
            emp = Employee.objects.get(tenant_id=request.tenant_id, user=request.user)
        except Employee.DoesNotExist:
            return Response({'data': []})
        qs = self.get_queryset().filter(employee=emp, status='active').order_by('-created_at')
        return Response({'data': GoalSerializer(qs, many=True).data, 'meta': {'count': qs.count()}})

    @action(detail=True, methods=['post'])
    def update_progress(self, request, pk=None):
        """
        Update goal progress.
        Body: {current_value, progress, status (optional)}
        """
        goal = self.get_object()
        ser = GoalProgressSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        goal.current_value = d['current_value']
        goal.progress = d['progress']
        if d.get('status'):
            goal.status = d['status']
        # Auto-complete if 100%
        if goal.progress >= 100 and goal.status == 'active':
            goal.status = 'completed'
        goal.save(update_fields=['current_value', 'progress', 'status', 'updated_at'])

        return Response({'data': GoalSerializer(goal).data,
                         'meta': {'message': 'Goal progress updated'}})

    @action(detail=True, methods=['get'])
    def sub_goals(self, request, pk=None):
        goal = self.get_object()
        children = goal.sub_goals.all()
        return Response({'data': GoalSerializer(children, many=True).data})


class FeedbackViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = Feedback.objects.select_related('from_employee', 'to_employee').all()
    serializer_class = FeedbackSerializer
    filterset_fields = ['from_employee', 'to_employee', 'type']

    @action(detail=False, methods=['get'])
    def my_feedback(self, request):
        """Feedback received by the current user's employee record."""
        from core_hr.models import Employee
        try:
            emp = Employee.objects.get(tenant_id=request.tenant_id, user=request.user)
        except Employee.DoesNotExist:
            return Response({'data': []})
        qs = self.get_queryset().filter(to_employee=emp).order_by('-created_at')
        return Response({'data': FeedbackSerializer(qs, many=True).data, 'meta': {'count': qs.count()}})


# =============================================================================
# P1 Upgrades — Talent Review, 9-Box, Succession, Promotion Readiness
# =============================================================================

class TalentReviewSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    placement_count = serializers.SerializerMethodField()

    class Meta:
        model = TalentReview
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']

    def get_placement_count(self, obj):
        return obj.placements.count()


class NineBoxPlacementSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)

    class Meta:
        model = NineBoxPlacement
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']


class SuccessionPlanSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    position_title = serializers.CharField(source='position.title', read_only=True)
    candidate_count = serializers.SerializerMethodField()

    class Meta:
        model = SuccessionPlan
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']

    def get_candidate_count(self, obj):
        return obj.candidates.count()


class SuccessionCandidateSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)

    class Meta:
        model = SuccessionCandidate
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class PromotionReadinessSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)

    class Meta:
        model = PromotionReadiness
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']


class TalentReviewViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = TalentReview.objects.select_related('cycle', 'facilitator').all()
    serializer_class = TalentReviewSerializer
    filterset_fields = ['status', 'cycle']
    search_fields = ['name']
    ordering_fields = ['review_date', 'created_at']

    @action(detail=True, methods=['get'])
    def nine_box(self, request, pk=None):
        """Return all 9-box placements for this talent review."""
        review = self.get_object()
        placements = review.placements.select_related('employee').all()
        return Response({'data': NineBoxPlacementSerializer(placements, many=True).data})

    @action(detail=True, methods=['post'])
    def finalize(self, request, pk=None):
        review = self.get_object()
        review.status = 'finalized'
        review.save(update_fields=['status', 'updated_at'])
        return Response({'data': TalentReviewSerializer(review).data,
                         'meta': {'message': 'Talent review finalized'}})


class NineBoxPlacementViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = NineBoxPlacement.objects.select_related('talent_review', 'employee').all()
    serializer_class = NineBoxPlacementSerializer
    filterset_fields = ['talent_review', 'employee', 'performance', 'potential']


class SuccessionPlanViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = SuccessionPlan.objects.select_related('position', 'current_holder').all()
    serializer_class = SuccessionPlanSerializer
    filterset_fields = ['position', 'review_year']
    ordering_fields = ['review_year', 'created_at']

    @action(detail=True, methods=['get'])
    def candidates(self, request, pk=None):
        plan = self.get_object()
        candidates = plan.candidates.select_related('employee').order_by('rank')
        return Response({'data': SuccessionCandidateSerializer(candidates, many=True).data})


class SuccessionCandidateViewSet(viewsets.ModelViewSet):
    """Nested under succession plans; no direct tenant FK so filter via plan."""
    from rest_framework.permissions import IsAuthenticated
    permission_classes = [IsAuthenticated]
    serializer_class = SuccessionCandidateSerializer
    filterset_fields = ['succession_plan', 'readiness']
    ordering_fields = ['rank', 'created_at']

    def get_queryset(self):
        return SuccessionCandidate.objects.select_related(
            'succession_plan', 'employee'
        ).filter(succession_plan__tenant_id=self.request.tenant_id)


class PromotionReadinessViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = PromotionReadiness.objects.select_related('employee', 'assessed_by', 'target_position').all()
    serializer_class = PromotionReadinessSerializer
    filterset_fields = ['employee', 'readiness_label']
    ordering_fields = ['assessment_date', 'created_at']

    @action(detail=False, methods=['get'])
    def ready_now(self, request):
        """Employees flagged as ready_now for promotion."""
        qs = self.get_queryset().filter(readiness_label='ready_now')
        return Response({'data': PromotionReadinessSerializer(qs, many=True).data,
                         'meta': {'count': qs.count()}})
