"""Messaging app — In-app messaging between seekers and employers."""
import uuid
from django.db import models
from django.conf import settings


class MessageThread(models.Model):
    """Conversation thread between two users (typically seeker ↔ employer)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey("jobs.JobListing", on_delete=models.SET_NULL, null=True, blank=True, related_name="message_threads")
    application = models.ForeignKey("applications.Application", on_delete=models.SET_NULL, null=True, blank=True)
    participant_one = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="threads_as_one")
    participant_two = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="threads_as_two")
    subject = models.CharField(max_length=200, blank=True, default="")
    is_archived_one = models.BooleanField(default=False)
    is_archived_two = models.BooleanField(default=False)
    last_message_at = models.DateTimeField(null=True, blank=True)
    # Message request inbox
    is_message_request = models.BooleanField(default=False,
                                              help_text="Thread is a message request (not yet accepted by recipient)")
    request_accepted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_message_threads"
        ordering = ["-last_message_at"]


class Message(models.Model):
    """Individual message within a thread."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread = models.ForeignKey(MessageThread, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    body = models.TextField()
    attachment = models.FileField(upload_to="message_attachments/", null=True, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    is_system_message = models.BooleanField(default=False)
    # Trust/Safety flags
    is_phishing_flagged = models.BooleanField(default=False)
    has_scam_signal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_messages"
        ordering = ["created_at"]


class VerifiedSenderBadge(models.Model):
    """Marks a user as a verified sender (recruiter or employer)."""
    class BadgeType(models.TextChoices):
        VERIFIED_RECRUITER = "verified_recruiter", "Verified Recruiter"
        VERIFIED_EMPLOYER = "verified_employer", "Verified Employer"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="verified_sender_badge")
    badge_type = models.CharField(max_length=20, choices=BadgeType.choices)
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                  related_name="badges_issued")
    issued_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "jf_verified_sender_badges"

    def __str__(self):
        return f"VerifiedSender: {self.user} [{self.badge_type}]"
