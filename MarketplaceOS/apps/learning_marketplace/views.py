from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone as tz
from .models import Course, CourseEnrollment, CourseCompletion, CohortProgram, CohortEnrollment, CourseLearningPath
from .serializers import (
    CourseSerializer, CourseListSerializer, CourseEnrollmentSerializer,
    CourseCompletionSerializer, CohortProgramSerializer, CohortEnrollmentSerializer,
    CourseLearningPathSerializer,
)


class CourseViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = ["course_type", "status", "difficulty_level", "is_free", "is_featured", "certificate_awarded"]
    search_fields = ["title", "short_description", "tags", "skills_covered"]
    ordering_fields = ["created_at", "price_lkr", "average_rating", "total_enrollments"]

    def get_serializer_class(self):
        if self.action == "list":
            return CourseListSerializer
        return CourseSerializer

    def get_queryset(self):
        return Course.objects.filter(status="active").select_related("provider")

    @action(detail=False, methods=["get"])
    def featured(self, request):
        courses = Course.objects.filter(status="active", is_featured=True)[:12]
        return Response(CourseListSerializer(courses, many=True).data)

    @action(detail=True, methods=["post"])
    def enroll(self, request, pk=None):
        course = self.get_object()
        if CourseEnrollment.objects.filter(course=course, learner=request.user).exists():
            return Response({"detail": "Already enrolled."}, status=400)
        enrollment = CourseEnrollment.objects.create(course=course, learner=request.user)
        course.total_enrollments += 1
        course.save(update_fields=["total_enrollments"])
        return Response(CourseEnrollmentSerializer(enrollment).data, status=201)


class CourseEnrollmentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CourseEnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CourseEnrollment.objects.filter(learner=self.request.user)

    @action(detail=True, methods=["post"])
    def update_progress(self, request, pk=None):
        enrollment = self.get_object()
        pct = request.data.get("progress_pct", enrollment.progress_pct)
        enrollment.progress_pct = min(100, max(0, int(pct)))
        enrollment.last_accessed_at = tz.now()
        if enrollment.progress_pct == 100:
            enrollment.status = CourseEnrollment.EnrollmentStatus.COMPLETED
        enrollment.save(update_fields=["progress_pct", "last_accessed_at", "status"])
        return Response(CourseEnrollmentSerializer(enrollment).data)


class CohortProgramViewSet(viewsets.ModelViewSet):
    serializer_class = CohortProgramSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = ["status", "course"]

    def get_queryset(self):
        return CohortProgram.objects.filter(status__in=["open", "in_progress"])

    @action(detail=True, methods=["post"])
    def join(self, request, pk=None):
        cohort = self.get_object()
        if CohortEnrollment.objects.filter(cohort=cohort, participant=request.user).exists():
            return Response({"detail": "Already enrolled."}, status=400)
        enrolled_count = cohort.enrollments.filter(status="active").count()
        if cohort.max_participants and enrolled_count >= cohort.max_participants:
            enrollment = CohortEnrollment.objects.create(cohort=cohort, participant=request.user, status="waitlisted")
        else:
            enrollment = CohortEnrollment.objects.create(cohort=cohort, participant=request.user)
        return Response(CohortEnrollmentSerializer(enrollment).data, status=201)


class CourseLearningPathViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CourseLearningPath.objects.filter(is_active=True)
    serializer_class = CourseLearningPathSerializer
    permission_classes = [permissions.AllowAny]
