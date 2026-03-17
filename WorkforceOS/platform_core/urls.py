"""Platform Core URL configuration."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .webhook_views import WebhookSubscriptionViewSet

router = DefaultRouter()
router.register(r'timeline', views.TimelineViewSet, basename='timeline')
router.register(r'notifications', views.NotificationViewSet, basename='notification')
router.register(r'approvals', views.ApprovalViewSet, basename='approval')
router.register(r'webhooks', views.WebhookViewSet, basename='webhook')
router.register(r'audit-logs', views.AuditLogViewSet, basename='audit-log')
router.register('webhook-subscriptions', WebhookSubscriptionViewSet, basename='webhook-subscription')

# Advanced features (#96 — models with no prior API exposure)
router.register(r'kb/categories', views.KBCategoryViewSet, basename='kb-category')
router.register(r'kb/articles', views.KBArticleViewSet, basename='kb-article')
router.register(r'benefits/plans', views.BenefitPlanViewSet, basename='benefit-plan')
router.register(r'benefits/enrollments', views.BenefitEnrollmentViewSet, basename='benefit-enrollment')
router.register(r'skills/definitions', views.SkillDefinitionViewSet, basename='skill-definition')
router.register(r'skills/employee-skills', views.EmployeeSkillViewSet, basename='employee-skill')
router.register(r'grievances', views.GrievanceCaseViewSet, basename='grievance')

urlpatterns = [path('', include(router.urls))]
