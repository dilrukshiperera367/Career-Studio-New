from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WorkflowDefinitionViewSet, WorkflowExecutionViewSet

router = DefaultRouter()
router.register('definitions', WorkflowDefinitionViewSet)
router.register('executions', WorkflowExecutionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
