from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'definitions', views.WorkflowDefinitionViewSet, basename='workflow-def')
router.register(r'instances', views.WorkflowInstanceViewSet, basename='workflow-instance')
router.register(r'tasks', views.WorkflowTaskViewSet, basename='workflow-task')

urlpatterns = [
    path('', include(router.urls)),
]
