from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
from .models import MessageThread, Message, SystemNotification
from .serializers import (
    MessageThreadSerializer, MessageSerializer, SystemNotificationSerializer,
)


class MessageThreadViewSet(viewsets.ModelViewSet):
    serializer_class = MessageThreadSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return MessageThread.objects.filter(
            Q(participant_a=user) | Q(participant_b=user)
        ).select_related("participant_a", "participant_b", "booking").order_by("-last_message_at")

    def perform_create(self, serializer):
        user = self.request.user
        # Prevent duplicate threads between same pair for same booking
        other = serializer.validated_data.get("participant_b") or serializer.validated_data.get("participant_a")
        booking = serializer.validated_data.get("booking")
        existing = None
        if booking:
            existing = MessageThread.objects.filter(
                Q(participant_a=user, participant_b=other) | Q(participant_a=other, participant_b=user),
                booking=booking,
            ).first()
        if existing:
            self._existing = existing
            return
        serializer.save(participant_a=user)
        self._existing = None

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        if hasattr(self, "_existing") and self._existing:
            out = self.get_serializer(self._existing)
            return Response(out.data, status=status.HTTP_200_OK)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=["get"], url_path="messages")
    def thread_messages(self, request, pk=None):
        thread = self.get_object()
        thread.mark_read(request.user)
        messages = thread.messages.select_related("sender").prefetch_related("attachments")
        serializer = MessageSerializer(messages, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="send")
    def send_message(self, request, pk=None):
        """Body: { body: "...", message_type: "text" }"""
        thread = self.get_object()
        if thread.status == MessageThread.ThreadStatus.LOCKED:
            return Response({"detail": "Thread is locked."}, status=status.HTTP_403_FORBIDDEN)

        body = request.data.get("body", "").strip()
        if not body:
            return Response({"detail": "Message body is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Apply safe messaging rules
        flagged = False
        flag_reason = ""
        filtered_body = body
        try:
            from apps.trust_marketplace.models import SafeMessagingRule
            import re
            rules = SafeMessagingRule.objects.filter(is_active=True)
            for rule in rules:
                if rule.pattern_regex and re.search(rule.pattern_regex, body, re.IGNORECASE):
                    flagged = True
                    flag_reason = f"Rule: {rule.name}"
                    if rule.action == "block":
                        thread.is_flagged = True
                        thread.save(update_fields=["is_flagged"])
                        return Response(
                            {"detail": "Message blocked by platform safety rules."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    elif rule.action == "flag":
                        pass  # log it but allow
                    elif rule.action == "warn":
                        filtered_body = "[Message contains off-platform contact info — removed for safety]"
        except Exception:
            pass

        msg = Message.objects.create(
            thread=thread,
            sender=request.user,
            body=body,
            filtered_body=filtered_body,
            is_flagged=flagged,
            flag_reason=flag_reason,
        )
        # Update thread metadata
        thread.last_message_at = msg.sent_at
        if request.user == thread.participant_a:
            thread.unread_b += 1
        else:
            thread.unread_a += 1
        thread.save(update_fields=["last_message_at", "unread_a", "unread_b"])

        serializer = MessageSerializer(msg, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        thread = self.get_object()
        thread.mark_read(request.user)
        return Response({"detail": "Thread marked as read."})


class SystemNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SystemNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SystemNotification.objects.filter(recipient=self.request.user)

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({"unread_count": count})

    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at"])
        serializer = self.get_serializer(notification)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        self.get_queryset().filter(is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        return Response({"detail": "All notifications marked as read."})
