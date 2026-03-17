from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone as tz
from .models import (
    Session, SessionNote, SessionDeliverable, SessionFeedbackForm,
    SessionActionPlan, SessionMilestone, SessionAssignment,
    MockInterviewRubric, AsyncReviewDelivery,
)
from .serializers import (
    SessionSerializer, SessionNoteSerializer, SessionDeliverableSerializer,
    SessionFeedbackFormSerializer, SessionActionPlanSerializer,
    SessionMilestoneSerializer, SessionAssignmentSerializer,
    MockInterviewRubricSerializer, AsyncReviewDeliverySerializer,
)


class SessionViewSet(viewsets.ModelViewSet):
    serializer_class = SessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Session.objects.filter(
            booking__buyer=user
        ) | Session.objects.filter(booking__provider__user=user)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        session = self.get_object()
        session.status = Session.SessionStatus.IN_PROGRESS
        session.started_at = tz.now()
        session.save(update_fields=["status", "started_at"])
        return Response(SessionSerializer(session).data)

    @action(detail=True, methods=["post"])
    def end(self, request, pk=None):
        session = self.get_object()
        session.status = Session.SessionStatus.ENDED
        session.ended_at = tz.now()
        if session.started_at:
            delta = session.ended_at - session.started_at
            session.actual_duration_minutes = int(delta.total_seconds() / 60)
        session.save(update_fields=["status", "ended_at", "actual_duration_minutes"])
        return Response(SessionSerializer(session).data)

    @action(detail=True, methods=["post"])
    def update_notes(self, request, pk=None):
        session = self.get_object()
        session.shared_notes = request.data.get("shared_notes", session.shared_notes)
        session.post_session_summary = request.data.get("post_session_summary", session.post_session_summary)
        session.save(update_fields=["shared_notes", "post_session_summary", "updated_at"])
        return Response(SessionSerializer(session).data)


class SessionNoteViewSet(viewsets.ModelViewSet):
    serializer_class = SessionNoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return SessionNote.objects.filter(
            session__booking__buyer=user
        ) | SessionNote.objects.filter(session__booking__provider__user=user)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class SessionDeliverableViewSet(viewsets.ModelViewSet):
    serializer_class = SessionDeliverableSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return SessionDeliverable.objects.filter(
            session__booking__buyer=user
        ) | SessionDeliverable.objects.filter(session__booking__provider__user=user)

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


class SessionFeedbackViewSet(viewsets.ModelViewSet):
    serializer_class = SessionFeedbackFormSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SessionFeedbackForm.objects.filter(submitted_by=self.request.user)

    def perform_create(self, serializer):
        serializer.save(submitted_by=self.request.user)


class SessionActionPlanViewSet(viewsets.ModelViewSet):
    serializer_class = SessionActionPlanSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return SessionActionPlan.objects.filter(
            session__booking__buyer=user
        ) | SessionActionPlan.objects.filter(session__booking__provider__user=user)


class SessionAssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = SessionAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return SessionAssignment.objects.filter(
            session__booking__buyer=user
        ) | SessionAssignment.objects.filter(session__booking__provider__user=user)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        assignment = self.get_object()
        assignment.submission_url = request.data.get("submission_url", "")
        assignment.submission_notes = request.data.get("submission_notes", "")
        assignment.status = SessionAssignment.AssignmentStatus.SUBMITTED
        assignment.submitted_at = tz.now()
        assignment.save(update_fields=["submission_url", "submission_notes", "status", "submitted_at"])
        return Response(SessionAssignmentSerializer(assignment).data)


class MockInterviewRubricViewSet(viewsets.ModelViewSet):
    serializer_class = MockInterviewRubricSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MockInterviewRubric.objects.filter(session__booking__provider__user=self.request.user)


class AsyncReviewViewSet(viewsets.ModelViewSet):
    serializer_class = AsyncReviewDeliverySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return AsyncReviewDelivery.objects.filter(
            session__booking__buyer=user
        ) | AsyncReviewDelivery.objects.filter(session__booking__provider__user=user)

    @action(detail=True, methods=["post"])
    def deliver(self, request, pk=None):
        review = self.get_object()
        review.reviewed_document_url = request.data.get("reviewed_document_url", "")
        review.written_review = request.data.get("written_review", "")
        review.video_review_url = request.data.get("video_review_url", "")
        review.review_status = AsyncReviewDelivery.ReviewStatus.DELIVERED
        review.delivered_at = tz.now()
        review.save()
        return Response(AsyncReviewDeliverySerializer(review).data)
