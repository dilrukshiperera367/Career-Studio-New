import uuid
from django.utils import timezone
from rest_framework import generics, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend

from apps.shared.permissions import IsPlacementOfficer
from .models import CampusEvent, EventFeedback, EventRegistration
from .serializers import (
    CampusEventDetailSerializer,
    CampusEventListSerializer,
    EventFeedbackSerializer,
    EventRegistrationSerializer,
)


class CampusEventListView(generics.ListAPIView):
    serializer_class = CampusEventListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["event_type", "mode", "status"]
    search_fields = ["title", "description"]
    ordering_fields = ["start_datetime"]

    def get_queryset(self):
        return CampusEvent.objects.filter(campus=self.request.user.campus, status="published")


class CampusEventManageView(generics.ListCreateAPIView):
    """Placement officer create/list all events."""
    permission_classes = [permissions.IsAuthenticated, IsPlacementOfficer]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "event_type"]

    def get_serializer_class(self):
        return CampusEventDetailSerializer

    def get_queryset(self):
        return CampusEvent.objects.filter(campus=self.request.user.campus)

    def perform_create(self, serializer):
        serializer.save(campus=self.request.user.campus, organizer=self.request.user)


class CampusEventDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CampusEventDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsPlacementOfficer]

    def get_queryset(self):
        return CampusEvent.objects.filter(campus=self.request.user.campus)


class EventRegistrationView(generics.CreateAPIView):
    """Student registers for an event."""
    serializer_class = EventRegistrationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        event = CampusEvent.objects.get(id=self.kwargs["event_id"])
        reg_number = f"REG-{str(uuid.uuid4())[:8].upper()}"
        serializer.save(student=self.request.user, event=event, registration_number=reg_number)


class MyEventRegistrationsView(generics.ListAPIView):
    serializer_class = EventRegistrationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return EventRegistration.objects.filter(student=self.request.user).select_related("event")


class EventFeedbackCreateView(generics.CreateAPIView):
    serializer_class = EventFeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        registration = EventRegistration.objects.get(
            student=self.request.user, event_id=self.kwargs["event_id"]
        )
        serializer.save(registration=registration)
