from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    ERCaseViewSet,
    ERCaseNoteViewSet,
    DisciplinaryActionViewSet,
    PImprovementPlanViewSet,
    EthicsIntakeViewSet,
)

router = DefaultRouter()
router.register(r'er/cases', ERCaseViewSet, basename='er-cases')
router.register(r'er/case-notes', ERCaseNoteViewSet, basename='er-case-notes')
router.register(r'er/disciplinary', DisciplinaryActionViewSet, basename='disciplinary-actions')
router.register(r'er/pips', PImprovementPlanViewSet, basename='pips')
router.register(r'er/ethics', EthicsIntakeViewSet, basename='ethics-intakes')

urlpatterns = [
    path('', include(router.urls)),
]
