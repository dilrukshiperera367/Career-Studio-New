from django.urls import path
from . import views

urlpatterns = [
    path("", views.CampusEventListView.as_view(), name="event-list"),
    path("manage/", views.CampusEventManageView.as_view(), name="event-manage"),
    path("<uuid:pk>/", views.CampusEventDetailView.as_view(), name="event-detail"),
    path("<uuid:event_id>/register/", views.EventRegistrationView.as_view(), name="event-register"),
    path("<uuid:event_id>/feedback/", views.EventFeedbackCreateView.as_view(), name="event-feedback"),
    path("my-registrations/", views.MyEventRegistrationsView.as_view(), name="my-event-registrations"),
]
