"""Notifications views — List, read, preferences, job alerts."""
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification, NotificationPreference, JobAlert
from .serializers import NotificationSerializer, NotificationPreferenceSerializer, JobAlertSerializer


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user).order_by("-created_at")
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        unread_only = self.request.query_params.get("unread")
        if unread_only == "true":
            qs = qs.filter(is_read=False)
        return qs


class NotificationMarkReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        updated = Notification.objects.filter(
            pk=pk, user=request.user, is_read=False,
        ).update(is_read=True, read_at=timezone.now())
        if updated:
            return Response({"detail": "Marked as read."})
        return Response({"detail": "Not found or already read."}, status=status.HTTP_404_NOT_FOUND)


class NotificationDeleteView(APIView):
    """Delete a single notification."""
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        deleted, _ = Notification.objects.filter(pk=pk, user=request.user).delete()
        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_404_NOT_FOUND)


class NotificationMarkAllReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        count = Notification.objects.filter(
            user=request.user, is_read=False,
        ).update(is_read=True, read_at=timezone.now())
        return Response({"detail": f"{count} notifications marked as read."})


class NotificationClearAllView(APIView):
    """Delete all read notifications for the user."""
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        count, _ = Notification.objects.filter(user=request.user, is_read=True).delete()
        return Response({"deleted": count})


class UnreadCountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({"unread_count": count})


class NotificationPreferenceView(generics.RetrieveUpdateAPIView):
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        prefs, _ = NotificationPreference.objects.get_or_create(user=self.request.user)
        return prefs


# ── Job Alerts ────────────────────────────────────────────────────────────

class JobAlertListCreateView(generics.ListCreateAPIView):
    serializer_class = JobAlertSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return JobAlert.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class JobAlertDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = JobAlertSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return JobAlert.objects.filter(user=self.request.user)


class JobAlertToggleView(APIView):
    """Toggle active/inactive state of a job alert."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            alert = JobAlert.objects.get(pk=pk, user=request.user)
        except JobAlert.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        alert.is_active = not alert.is_active
        alert.save(update_fields=["is_active"])
        return Response({"is_active": alert.is_active})
