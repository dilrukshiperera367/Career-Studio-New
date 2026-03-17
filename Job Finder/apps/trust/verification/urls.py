from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'employer-verification', views.EmployerVerificationViewSet, basename='employer-verify')
router.register(r'recruiter-verification', views.RecruiterVerificationViewSet, basename='recruiter-verify')
router.register(r'fraud-reports', views.FraudReportViewSet, basename='fraud-report')
router.register(r'trust-scores', views.TrustScoreViewSet, basename='trust-score')

urlpatterns = [
    path('', include(router.urls)),
]
