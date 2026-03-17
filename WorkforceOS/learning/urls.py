from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CourseViewSet, CourseEnrollmentViewSet, CertificationViewSet,
    SkillPathwayViewSet, PathwayStepViewSet,
    MentorshipProgramViewSet, MentorshipMatchViewSet,
    LXPRecommendationViewSet,
)

router = DefaultRouter()
router.register('courses', CourseViewSet)
router.register('enrollments', CourseEnrollmentViewSet)
router.register('certifications', CertificationViewSet)
# P1 upgrades
router.register('skill-pathways', SkillPathwayViewSet, basename='skill-pathway')
router.register('pathway-steps', PathwayStepViewSet, basename='pathway-step')
router.register('mentorship-programs', MentorshipProgramViewSet, basename='mentorship-program')
router.register('mentorship-matches', MentorshipMatchViewSet, basename='mentorship-match')
router.register('lxp-recommendations', LXPRecommendationViewSet, basename='lxp-recommendation')

urlpatterns = [
    path('', include(router.urls)),
]
