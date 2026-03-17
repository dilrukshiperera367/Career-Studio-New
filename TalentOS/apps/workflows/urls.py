"""URL configuration for workflow management API."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .webhook_views import WebhookSubscriptionViewSet

router = DefaultRouter()
router.register('webhook-subscriptions', WebhookSubscriptionViewSet, basename='webhook-subscription')

urlpatterns = [
    path("rules/", views.WorkflowRuleListCreateView.as_view(), name="workflow-rules"),
    path("rules/<uuid:pk>/", views.WorkflowRuleDetailView.as_view(), name="workflow-rule-detail"),
    path("rules/<uuid:pk>/toggle/", views.toggle_rule, name="workflow-rule-toggle"),
    path("executions/", views.WorkflowExecutionListView.as_view(), name="workflow-executions"),
    path("trigger/", views.trigger_workflow, name="workflow-trigger"),
    path("", include(router.urls)),
]
