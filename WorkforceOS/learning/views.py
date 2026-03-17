"""Learning & Development API — Courses, Enrollments, Certifications."""

from rest_framework import viewsets, serializers, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from config.base_api import TenantViewSetMixin, TenantSerializerMixin
from .models import (
    Course, CourseEnrollment, Certification,
    SkillPathway, PathwayStep, MentorshipProgram, MentorshipMatch, LXPRecommendation,
)


# --- Serializers ---

class CourseSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    enrollment_count = serializers.SerializerMethodField()
    completion_rate = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']

    def get_enrollment_count(self, obj):
        return obj.enrollments.count()

    def get_completion_rate(self, obj):
        total = obj.enrollments.count()
        if total == 0:
            return 0
        completed = obj.enrollments.filter(status='completed').count()
        return round(completed / total * 100, 1)


class CourseEnrollmentSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)

    class Meta:
        model = CourseEnrollment
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'enrolled_at']


class CertificationSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = Certification
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']

    def get_is_expired(self, obj):
        if obj.expiry_date:
            return obj.expiry_date < timezone.now().date()
        return False


# --- Views ---

class CourseViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['category', 'format', 'status']
    search_fields = ['title', 'description']

    @action(detail=True, methods=['post'])
    def enroll(self, request, pk=None):
        course = self.get_object()
        employee_id = request.data.get('employee_id')
        if not employee_id:
            return Response({'error': 'employee_id required'}, status=status.HTTP_400_BAD_REQUEST)
        enrollment, created = CourseEnrollment.objects.get_or_create(
            tenant=course.tenant, course=course, employee_id=employee_id)
        if not created:
            return Response({'error': 'Already enrolled'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'data': CourseEnrollmentSerializer(enrollment).data}, status=status.HTTP_201_CREATED)


class CourseEnrollmentViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = CourseEnrollment.objects.select_related('course', 'employee').all()
    serializer_class = CourseEnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['course', 'employee', 'status']

    @action(detail=False, methods=['get'], url_path='mine')
    def mine(self, request):
        """Return enrollments for the currently authenticated user's employee record."""
        qs = self.get_queryset().filter(employee__user=request.user)
        serializer = self.get_serializer(qs, many=True)
        return Response({'data': serializer.data})

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        enrollment = self.get_object()
        enrollment.status = 'completed'
        enrollment.completed_at = timezone.now()
        enrollment.progress = 100
        enrollment.score = request.data.get('score')
        enrollment.save()
        return Response({'data': CourseEnrollmentSerializer(enrollment).data})

    @action(detail=True, methods=['post'], url_path='update-progress')
    def update_progress(self, request, pk=None):
        enrollment = self.get_object()
        enrollment.progress = request.data.get('progress', enrollment.progress)
        if enrollment.progress > 0 and enrollment.status == 'enrolled':
            enrollment.status = 'in_progress'
            enrollment.started_at = enrollment.started_at or timezone.now()
        enrollment.save()
        return Response({'data': CourseEnrollmentSerializer(enrollment).data})


class CertificationViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = Certification.objects.select_related('employee').all()
    serializer_class = CertificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['employee', 'status']
    search_fields = ['name', 'issuing_body']

    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        from datetime import timedelta
        threshold = timezone.now().date() + timedelta(days=30)
        expiring = self.get_queryset().filter(
            expiry_date__lte=threshold, expiry_date__gte=timezone.now().date(), status='active')
        return Response({'data': CertificationSerializer(expiring, many=True).data})


# =============================================================================
# P1 Upgrades — Skill Pathways, Mentorship, LXP Recommendations
# =============================================================================

class SkillPathwaySerializer(TenantSerializerMixin, serializers.ModelSerializer):
    step_count = serializers.SerializerMethodField()

    class Meta:
        model = SkillPathway
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']

    def get_step_count(self, obj):
        return obj.steps.count()


class PathwayStepSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model = PathwayStep
        fields = '__all__'
        read_only_fields = ['id']


class MentorshipProgramSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    match_count = serializers.SerializerMethodField()

    class Meta:
        model = MentorshipProgram
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']

    def get_match_count(self, obj):
        return obj.matches.count()


class MentorshipMatchSerializer(serializers.ModelSerializer):
    mentor_name = serializers.CharField(source='mentor.full_name', read_only=True)
    mentee_name = serializers.CharField(source='mentee.full_name', read_only=True)

    class Meta:
        model = MentorshipMatch
        fields = '__all__'
        read_only_fields = ['id', 'matched_at']


class LXPRecommendationSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)

    class Meta:
        model = LXPRecommendation
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'generated_at']


class SkillPathwayViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = SkillPathway.objects.prefetch_related('steps').all()
    serializer_class = SkillPathwaySerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status']
    search_fields = ['title']

    @action(detail=True, methods=['get'])
    def steps(self, request, pk=None):
        pathway = self.get_object()
        return Response({'data': PathwayStepSerializer(pathway.steps.order_by('order'), many=True).data})


class PathwayStepViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PathwayStepSerializer
    filterset_fields = ['pathway', 'is_required']
    ordering_fields = ['order']

    def get_queryset(self):
        return PathwayStep.objects.select_related('pathway', 'course').filter(
            pathway__tenant_id=self.request.tenant_id
        )


class MentorshipProgramViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = MentorshipProgram.objects.all()
    serializer_class = MentorshipProgramSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'program_type']
    search_fields = ['name']

    @action(detail=True, methods=['get'])
    def matches(self, request, pk=None):
        program = self.get_object()
        matches = program.matches.select_related('mentor', 'mentee').all()
        return Response({'data': MentorshipMatchSerializer(matches, many=True).data})


class MentorshipMatchViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MentorshipMatchSerializer
    filterset_fields = ['program', 'mentor', 'mentee', 'status']

    def get_queryset(self):
        return MentorshipMatch.objects.select_related('program', 'mentor', 'mentee').filter(
            program__tenant_id=self.request.tenant_id
        )

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        match = self.get_object()
        match.status = 'completed'
        match.ended_at = timezone.now()
        match.feedback = request.data.get('feedback', '')
        match.save(update_fields=['status', 'ended_at', 'feedback'])
        return Response({'data': MentorshipMatchSerializer(match).data})


class LXPRecommendationViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = LXPRecommendation.objects.select_related('employee', 'course', 'pathway').all()
    serializer_class = LXPRecommendationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['employee', 'reason', 'is_dismissed', 'is_enrolled']
    ordering_fields = ['score', 'generated_at']

    @action(detail=False, methods=['get'])
    def mine(self, request):
        """Active recommendations for the current user's employee record."""
        qs = self.get_queryset().filter(
            employee__user=request.user, is_dismissed=False
        ).order_by('-score')
        return Response({'data': LXPRecommendationSerializer(qs, many=True).data,
                         'meta': {'count': qs.count()}})

    @action(detail=True, methods=['post'])
    def dismiss(self, request, pk=None):
        rec = self.get_object()
        rec.is_dismissed = True
        rec.save(update_fields=['is_dismissed'])
        return Response({'data': LXPRecommendationSerializer(rec).data})
