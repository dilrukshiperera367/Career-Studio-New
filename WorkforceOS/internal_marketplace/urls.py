from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    InternalJobPostingViewSet,
    InternalApplicationViewSet,
    GigProjectViewSet,
    GigParticipationViewSet,
    MobilityProfileViewSet,
    SkillMatchSuggestionViewSet,
)

router = DefaultRouter()
router.register(r'marketplace/postings', InternalJobPostingViewSet, basename='internal-postings')
router.register(r'marketplace/applications', InternalApplicationViewSet, basename='internal-applications')
router.register(r'marketplace/gigs', GigProjectViewSet, basename='gig-projects')
router.register(r'marketplace/gig-participations', GigParticipationViewSet, basename='gig-participations')
router.register(r'marketplace/mobility', MobilityProfileViewSet, basename='mobility-profiles')
router.register(r'marketplace/suggestions', SkillMatchSuggestionViewSet, basename='skill-suggestions')

urlpatterns = [
    path('', include(router.urls)),
]
