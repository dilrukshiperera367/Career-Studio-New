"""Messaging views — Threads, messages."""
from django.db import models
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from .models import MessageThread, Message
from .serializers import (
    MessageThreadSerializer, MessageSerializer,
    MessageCreateSerializer, ThreadCreateSerializer,
)


class ThreadListView(generics.ListAPIView):
    serializer_class = MessageThreadSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return MessageThread.objects.filter(
            models.Q(participant_one=user) | models.Q(participant_two=user)
        ).order_by("-last_message_at")


class ThreadCreateView(APIView):
    """Create a new message thread."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ThreadCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        recipient_id = serializer.validated_data["recipient_id"]
        try:
            recipient = User.objects.get(id=recipient_id)
        except User.DoesNotExist:
            return Response({"detail": "Recipient not found."}, status=status.HTTP_404_NOT_FOUND)

        thread = MessageThread.objects.create(
            participant_one=request.user,
            participant_two=recipient,
            subject=serializer.validated_data.get("subject", ""),
            last_message_at=timezone.now(),
        )
        if job_id := serializer.validated_data.get("job_id"):
            thread.job_id = job_id
            thread.save(update_fields=["job_id"])

        Message.objects.create(
            thread=thread, sender=request.user,
            body=serializer.validated_data["body"],
        )
        return Response(
            MessageThreadSerializer(thread, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ThreadDetailView(generics.RetrieveAPIView):
    serializer_class = MessageThreadSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return MessageThread.objects.filter(
            models.Q(participant_one=user) | models.Q(participant_two=user)
        )


class MessageListView(generics.ListAPIView):
    """Messages within a thread."""
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Message.objects.filter(thread_id=self.kwargs["thread_id"]).order_by("created_at")


class SendMessageView(APIView):
    """Send a message to an existing thread."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, thread_id):
        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            thread = MessageThread.objects.get(pk=thread_id)
        except MessageThread.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if request.user not in (thread.participant_one, thread.participant_two):
            return Response(status=status.HTTP_403_FORBIDDEN)

        msg = Message.objects.create(
            thread=thread, sender=request.user,
            body=serializer.validated_data["body"],
            attachment=serializer.validated_data.get("attachment"),
        )
        thread.last_message_at = timezone.now()
        thread.save(update_fields=["last_message_at"])
        return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)


class MarkThreadReadView(APIView):
    """Mark all messages in a thread as read."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, thread_id):
        Message.objects.filter(
            thread_id=thread_id, is_read=False,
        ).exclude(sender=request.user).update(is_read=True, read_at=timezone.now())
        return Response({"detail": "Messages marked as read."})
