from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ERGViewSet,
    ERGMembershipViewSet,
    CommunityEventViewSet,
    EventRSVPViewSet,
    RecognitionProgramViewSet,
    RecognitionNominationViewSet,
)

router = DefaultRouter()
router.register('experience/ergs', ERGViewSet, basename='ergs')
router.register('experience/erg-memberships', ERGMembershipViewSet, basename='erg-memberships')
router.register('experience/events', CommunityEventViewSet, basename='community-events')
router.register('experience/event-rsvps', EventRSVPViewSet, basename='event-rsvps')
router.register('experience/recognition-programs', RecognitionProgramViewSet, basename='recognition-programs')
router.register('experience/nominations', RecognitionNominationViewSet, basename='recognition-nominations')

urlpatterns = [
    path('', include(router.urls)),
]
