"""Onboarding & Exit URL configuration."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'onboarding/templates', views.OnboardingTemplateViewSet, basename='onboarding-template')
router.register(r'onboarding/instances', views.OnboardingInstanceViewSet, basename='onboarding-instance')
router.register(r'onboarding/tasks', views.OnboardingTaskViewSet, basename='onboarding-task')
router.register(r'assets', views.AssetViewSet, basename='asset')
router.register(r'onboarding/exit-requests', views.ExitRequestViewSet, basename='exit-request')
router.register(r'onboarding/exit-checklist', views.ExitChecklistViewSet, basename='exit-checklist')
router.register(r'onboarding/exit-interviews', views.ExitInterviewViewSet, basename='exit-interview')
# P1 upgrades
router.register(r'onboarding/preboarding', views.PreboardingPortalViewSet, basename='preboarding-portal')
router.register(r'onboarding/buddy-assignments', views.BuddyAssignmentViewSet, basename='buddy-assignment')
router.register(r'onboarding/milestone-plans', views.MilestonePlanViewSet, basename='milestone-plan')
router.register(r'onboarding/milestone-items', views.MilestonePlanItemViewSet, basename='milestone-item')

urlpatterns = [path('', include(router.urls))]
