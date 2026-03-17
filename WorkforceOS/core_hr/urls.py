"""Core HR URL configuration."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'companies', views.CompanyViewSet, basename='company')
router.register(r'branches', views.BranchViewSet, basename='branch')
router.register(r'departments', views.DepartmentViewSet, basename='department')
router.register(r'positions', views.PositionViewSet, basename='position')
router.register(r'employees', views.EmployeeViewSet, basename='employee')
router.register(r'announcements', views.AnnouncementViewSet, basename='announcement')
router.register(r'critical-roles', views.CriticalRoleViewSet, basename='critical-role')
router.register(r'mobility-profiles', views.InternalMobilityProfileViewSet, basename='mobility-profile')

urlpatterns = [
    path('', include(router.urls)),
]
