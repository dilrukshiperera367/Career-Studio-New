"""
MarketplaceOS — apps.bookings

Booking, Scheduling & Session Management.

Models:
    Booking                  — Core booking record linking buyer → service → provider
    BookingIntakeResponse    — Pre-session questionnaire answers
    BookingReminder          — Scheduled reminder records
    RecurringPlan            — Recurring session plan
    GroupSessionBooking      — Attendance record for a group/cohort booking
    WaitlistEntry            — Waitlist for full sessions
"""
import uuid
from django.db import models
from django.conf import settings


class Booking(models.Model):
    """
    Core booking record.  One booking = one purchased service slot.
    Supports 1:1 sessions, async reviews, group sessions, recurring plans,
    instant booking, request-to-book, and employer-sponsored bookings.
    """

    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", "Pending Payment"
        PENDING_APPROVAL = "pending_approval", "Pending Provider Approval"
        CONFIRMED = "confirmed", "Confirmed"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED_BUYER = "cancelled_buyer", "Cancelled by Buyer"
        CANCELLED_PROVIDER = "cancelled_provider", "Cancelled by Provider"
        NO_SHOW_BUYER = "no_show_buyer", "No-Show (Buyer)"
        NO_SHOW_PROVIDER = "no_show_provider", "No-Show (Provider)"
        REFUNDED = "refunded", "Refunded"
        DISPUTED = "disputed", "Disputed"

    class BookingMode(models.TextChoices):
        INSTANT = "instant", "Instant Booking"
        REQUEST = "request", "Request to Book"
        APPROVAL = "approval", "Approval Required"
        ENTERPRISE = "enterprise", "Enterprise / Sponsored"

    class DeliveryMode(models.TextChoices):
        VIDEO = "video", "Live Video"
        AUDIO = "audio", "Audio Call"
        CHAT = "chat", "Chat"
        ASYNC = "async", "Async Written / Review"
        GROUP = "group", "Group / Cohort"
        IN_PERSON = "in_person", "In Person"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=20, unique=True, db_index=True,
                                  help_text="Human-readable booking reference e.g. MP-00123456")

    # Parties
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="bookings_as_buyer",
    )
    provider = models.ForeignKey(
        "providers.Provider", on_delete=models.PROTECT,
        related_name="bookings",
    )
    service = models.ForeignKey(
        "services_catalog.Service", on_delete=models.PROTECT,
        related_name="bookings", null=True, blank=True,
    )

    # Enterprise sponsorship
    enterprise_account = models.ForeignKey(
        "enterprise_marketplace.EnterpriseAccount", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="bookings",
        help_text="Set if this booking is employer-sponsored.",
    )
    sponsored_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="sponsored_bookings",
        help_text="Manager who approved the sponsored booking.",
    )

    # Timing
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    timezone = models.CharField(max_length=50, default="Asia/Colombo")
    duration_minutes = models.IntegerField(default=60)

    # Delivery
    delivery_mode = models.CharField(max_length=15, choices=DeliveryMode.choices, default=DeliveryMode.VIDEO)
    booking_mode = models.CharField(max_length=15, choices=BookingMode.choices, default=BookingMode.INSTANT)
    video_link = models.URLField(blank=True, default="",
                                  help_text="Auto-generated meeting link.")
    meeting_provider = models.CharField(max_length=50, blank=True, default="",
                                         help_text="e.g. zoom, google_meet, internal")

    # Status
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.PENDING_PAYMENT)
    status_changed_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True, default="")
    cancellation_fee_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Content
    buyer_notes = models.TextField(blank=True, default="",
                                    help_text="Notes from buyer at booking time.")
    provider_notes = models.TextField(blank=True, default="")
    session_agenda = models.TextField(blank=True, default="")
    internal_notes = models.TextField(blank=True, default="",
                                       help_text="Platform internal notes — not visible to parties.")

    # Pricing snapshot (captured at booking time)
    price_lkr = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=5, default="LKR")
    is_free = models.BooleanField(default=False)

    # Recurring plan link
    recurring_plan = models.ForeignKey(
        "RecurringPlan", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="bookings",
    )

    # Reminders sent
    reminder_24h_sent = models.BooleanField(default=False)
    reminder_1h_sent = models.BooleanField(default=False)

    # Review flag
    review_requested = models.BooleanField(default=False)
    review_submitted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mp_booking"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["buyer", "status"]),
            models.Index(fields=["provider", "status"]),
            models.Index(fields=["start_time"]),
        ]

    def __str__(self):
        return f"{self.reference} — {self.status}"

    def save(self, *args, **kwargs):
        if not self.reference:
            import random
            import string
            self.reference = "MP-" + "".join(random.choices(string.digits, k=8))
        super().save(*args, **kwargs)


class BookingIntakeResponse(models.Model):
    """
    Answers to pre-session intake questions.
    Each question/answer is stored as a key-value pair so intake forms
    can evolve without schema changes.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="intake_responses")
    question = models.CharField(max_length=500)
    answer = models.TextField(blank=True, default="")
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "mp_booking_intake"
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.booking.reference} — {self.question[:60]}"


class BookingReminder(models.Model):
    """Scheduled reminder record for a booking."""

    class ReminderType(models.TextChoices):
        H24 = "24h", "24 Hours Before"
        H1 = "1h", "1 Hour Before"
        CUSTOM = "custom", "Custom"
        POST_SESSION = "post_session", "Post-Session Follow-up"

    class Channel(models.TextChoices):
        EMAIL = "email", "Email"
        IN_APP = "in_app", "In-App Notification"
        SMS = "sms", "SMS"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="reminders")
    reminder_type = models.CharField(max_length=15, choices=ReminderType.choices)
    channel = models.CharField(max_length=10, choices=Channel.choices, default=Channel.EMAIL)
    scheduled_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    is_sent = models.BooleanField(default=False)
    recipient_email = models.EmailField(blank=True, default="")

    class Meta:
        db_table = "mp_booking_reminder"
        ordering = ["scheduled_at"]

    def __str__(self):
        return f"{self.booking.reference} — {self.reminder_type} ({self.channel})"


class RecurringPlan(models.Model):
    """
    A recurring session plan — e.g. monthly mentoring, weekly coaching.
    Individual bookings are created for each occurrence.
    """

    class Frequency(models.TextChoices):
        WEEKLY = "weekly", "Weekly"
        BIWEEKLY = "biweekly", "Every Two Weeks"
        MONTHLY = "monthly", "Monthly"
        CUSTOM = "custom", "Custom"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="recurring_plans",
    )
    provider = models.ForeignKey(
        "providers.Provider", on_delete=models.PROTECT,
        related_name="recurring_plans",
    )
    service = models.ForeignKey(
        "services_catalog.Service", on_delete=models.PROTECT,
        null=True, blank=True,
    )
    frequency = models.CharField(max_length=15, choices=Frequency.choices)
    day_of_week = models.IntegerField(null=True, blank=True,
                                       help_text="0=Mon … 6=Sun for weekly/biweekly plans.")
    preferred_time = models.TimeField(null=True, blank=True)
    timezone = models.CharField(max_length=50, default="Asia/Colombo")
    total_sessions = models.IntegerField(default=0,
                                          help_text="0 = unlimited / open-ended.")
    sessions_completed = models.IntegerField(default=0)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.ACTIVE)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_recurring_plan"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Recurring {self.frequency} — {self.buyer} → {self.provider}"


class GroupSessionBooking(models.Model):
    """
    Attendee record for a group/cohort session booking.
    The parent booking represents the group slot; each attendee has their own record.
    """

    class AttendanceStatus(models.TextChoices):
        REGISTERED = "registered", "Registered"
        ATTENDED = "attended", "Attended"
        ABSENT = "absent", "Absent"
        WAITLISTED = "waitlisted", "Waitlisted"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="group_attendees")
    attendee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="group_session_bookings",
    )
    attendance_status = models.CharField(
        max_length=15, choices=AttendanceStatus.choices, default=AttendanceStatus.REGISTERED,
    )
    registered_at = models.DateTimeField(auto_now_add=True)
    attended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "mp_group_session_booking"
        unique_together = [["booking", "attendee"]]

    def __str__(self):
        return f"{self.attendee} @ {self.booking.reference}"


class WaitlistEntry(models.Model):
    """Waitlist entry for a fully-booked session slot."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.ForeignKey(
        "services_catalog.Service", on_delete=models.CASCADE,
        related_name="waitlist",
    )
    provider = models.ForeignKey(
        "providers.Provider", on_delete=models.CASCADE,
        related_name="waitlist",
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="waitlist_entries",
    )
    preferred_time = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    notified = models.BooleanField(default=False)
    notified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_waitlist"
        ordering = ["created_at"]

    def __str__(self):
        return f"Waitlist: {self.buyer} for {self.service}"
