from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MessageThreadViewSet, SystemNotificationViewSet

router = DefaultRouter()
router.register(r"message-threads", MessageThreadViewSet, basename="message-thread")
router.register(r"notifications", SystemNotificationViewSet, basename="notification")

urlpatterns = [
    path("", include(router.urls)),
]
