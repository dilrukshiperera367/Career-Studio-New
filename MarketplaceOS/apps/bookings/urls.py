from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookingViewSet, RecurringPlanViewSet, WaitlistViewSet

router = DefaultRouter()
router.register("bookings", BookingViewSet, basename="booking")
router.register("recurring-plans", RecurringPlanViewSet, basename="recurring-plan")
router.register("waitlist", WaitlistViewSet, basename="waitlist")

urlpatterns = [path("", include(router.urls))]
