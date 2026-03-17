"""
MarketplaceOS — apps.marketplace_messaging

Messaging and communications layer.  Supports:
  - Booking-linked threads (provider ↔ buyer)
  - Pre-booking enquiry threads
  - System/platform notifications
  - Safe-messaging rule application (integrates with trust_marketplace)

Models:
    MessageThread       — Conversation container
    Message             — Individual message (text/file)
    MessageAttachment   — File attachment on a message
    SystemNotification  — In-app notification for a user
"""
import uuid
from django.db import models
from django.conf import settings


class MessageThread(models.Model):
    """Conversation thread between two users, optionally linked to a booking."""

    class ThreadType(models.TextChoices):
        PRE_BOOKING = "pre_booking", "Pre-Booking Enquiry"
        BOOKING = "booking", "Booking Communication"
        SUPPORT = "support", "Support Ticket"
        GENERAL = "general", "General"

    class ThreadStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"
        LOCKED = "locked", "Locked (by admin)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread_type = models.CharField(max_length=15, choices=ThreadType.choices, default=ThreadType.GENERAL)
    status = models.CharField(max_length=10, choices=ThreadStatus.choices, default=ThreadStatus.ACTIVE)
    participant_a = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="threads_as_a",
    )
    participant_b = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="threads_as_b",
    )
    booking = models.ForeignKey(
        "bookings.Booking", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="message_threads",
    )
    subject = models.CharField(max_length=300, blank=True, default="")
    unread_a = models.IntegerField(default=0, help_text="Unread count for participant_a.")
    unread_b = models.IntegerField(default=0, help_text="Unread count for participant_b.")
    last_message_at = models.DateTimeField(null=True, blank=True)
    is_flagged = models.BooleanField(default=False, help_text="Flagged by safe-messaging rule.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_message_thread"
        ordering = ["-last_message_at"]

    def __str__(self):
        return f"Thread {self.id} — {self.participant_a} ↔ {self.participant_b}"

    def get_unread_count(self, user):
        if user == self.participant_a:
            return self.unread_a
        if user == self.participant_b:
            return self.unread_b
        return 0

    def mark_read(self, user):
        if user == self.participant_a:
            self.unread_a = 0
        elif user == self.participant_b:
            self.unread_b = 0
        self.save(update_fields=["unread_a", "unread_b"])


class Message(models.Model):
    """Individual message within a thread."""

    class MessageType(models.TextChoices):
        TEXT = "text", "Text"
        FILE = "file", "File"
        SYSTEM = "system", "System / Automated"

    class MessageStatus(models.TextChoices):
        SENT = "sent", "Sent"
        DELIVERED = "delivered", "Delivered"
        READ = "read", "Read"
        FILTERED = "filtered", "Filtered by Safe-Messaging"
        DELETED = "deleted", "Deleted"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread = models.ForeignKey(MessageThread, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="sent_messages",
    )
    message_type = models.CharField(max_length=10, choices=MessageType.choices, default=MessageType.TEXT)
    status = models.CharField(max_length=10, choices=MessageStatus.choices, default=MessageStatus.SENT)
    body = models.TextField(blank=True, default="")
    filtered_body = models.TextField(blank=True, default="",
                                      help_text="Body after safe-messaging redaction.")
    is_flagged = models.BooleanField(default=False)
    flag_reason = models.CharField(max_length=200, blank=True, default="")
    read_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "mp_message"
        ordering = ["sent_at"]

    def __str__(self):
        return f"Message {self.id} in thread {self.thread_id}"


class MessageAttachment(models.Model):
    """File attachment on a message."""

    class AttachmentType(models.TextChoices):
        DOCUMENT = "document", "Document"
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"
        AUDIO = "audio", "Audio"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="attachments")
    file_url = models.URLField()
    original_filename = models.CharField(max_length=300)
    attachment_type = models.CharField(max_length=10, choices=AttachmentType.choices, default=AttachmentType.OTHER)
    file_size_bytes = models.IntegerField(null=True, blank=True)
    is_scanned = models.BooleanField(default=False)
    is_safe = models.BooleanField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_message_attachment"

    def __str__(self):
        return f"Attachment {self.original_filename}"


class SystemNotification(models.Model):
    """In-app notification for a user."""

    class NotificationType(models.TextChoices):
        BOOKING_CONFIRMED = "booking_confirmed", "Booking Confirmed"
        BOOKING_CANCELLED = "booking_cancelled", "Booking Cancelled"
        BOOKING_REMINDER = "booking_reminder", "Booking Reminder"
        SESSION_STARTING = "session_starting", "Session Starting Soon"
        REVIEW_RECEIVED = "review_received", "New Review Received"
        PAYOUT_PROCESSED = "payout_processed", "Payout Processed"
        DISPUTE_OPENED = "dispute_opened", "Dispute Opened"
        DISPUTE_RESOLVED = "dispute_resolved", "Dispute Resolved"
        MESSAGE_RECEIVED = "message_received", "New Message"
        PROFILE_APPROVED = "profile_approved", "Profile Approved"
        PROFILE_SUSPENDED = "profile_suspended", "Profile Suspended"
        ENTERPRISE_APPROVAL = "enterprise_approval", "Budget Approval Required"
        COURSE_ENROLLED = "course_enrolled", "Course Enrollment Confirmed"
        ASSESSMENT_READY = "assessment_ready", "Assessment Ready"
        ASSESSMENT_RESULT = "assessment_result", "Assessment Result Ready"
        PROMO_CODE = "promo_code", "Promo Code Available"
        GENERAL = "general", "General"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications",
    )
    notification_type = models.CharField(max_length=25, choices=NotificationType.choices)
    title = models.CharField(max_length=200)
    body = models.TextField()
    action_url = models.CharField(max_length=500, blank=True, default="")
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "mp_system_notification"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notification to {self.recipient_id}: {self.title}"
