from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TicketCategoryViewSet, TicketViewSet,
    ServiceCatalogItemViewSet, ServiceRequestViewSet,
    ChatbotIntakeViewSet, SLADashboardConfigViewSet,
)

router = DefaultRouter()
router.register('categories', TicketCategoryViewSet)
router.register('tickets', TicketViewSet)
router.register('service-catalog', ServiceCatalogItemViewSet)
router.register('service-requests', ServiceRequestViewSet)
router.register('chatbot-intakes', ChatbotIntakeViewSet)
router.register('sla-config', SLADashboardConfigViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
