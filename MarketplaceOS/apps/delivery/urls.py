from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SessionViewSet, SessionNoteViewSet, SessionDeliverableViewSet,
    SessionFeedbackViewSet, SessionActionPlanViewSet, SessionAssignmentViewSet,
    MockInterviewRubricViewSet, AsyncReviewViewSet,
)

router = DefaultRouter()
router.register("sessions", SessionViewSet, basename="session")
router.register("session-notes", SessionNoteViewSet, basename="session-note")
router.register("session-deliverables", SessionDeliverableViewSet, basename="session-deliverable")
router.register("session-feedback", SessionFeedbackViewSet, basename="session-feedback")
router.register("session-action-plans", SessionActionPlanViewSet, basename="session-action-plan")
router.register("session-assignments", SessionAssignmentViewSet, basename="session-assignment")
router.register("mock-interview-rubrics", MockInterviewRubricViewSet, basename="mock-interview-rubric")
router.register("async-reviews", AsyncReviewViewSet, basename="async-review")

urlpatterns = [path("", include(router.urls))]
