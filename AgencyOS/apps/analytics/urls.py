from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.AgencyAnalyticsView.as_view(), name="analytics-dashboard"),
]
