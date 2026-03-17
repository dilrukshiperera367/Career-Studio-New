from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SurveyViewSet, RecognitionViewSet,
    StayInterviewViewSet, LifecycleSurveyTriggerViewSet,
    ManagerActionPlanViewSet, ManagerActionItemViewSet,
)

router = DefaultRouter()
router.register('surveys', SurveyViewSet)
router.register('recognition', RecognitionViewSet)
router.register('stay-interviews', StayInterviewViewSet)
router.register('lifecycle-triggers', LifecycleSurveyTriggerViewSet)
router.register('action-plans', ManagerActionPlanViewSet)
router.register('action-items', ManagerActionItemViewSet, basename='action-item')

urlpatterns = [
    path('', include(router.urls)),
]
