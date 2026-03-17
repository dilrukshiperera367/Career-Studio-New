"""CampusOS — Campus Events models."""

import uuid
from django.db import models
from apps.shared.models import TimestampedModel


class CampusEvent(TimestampedModel):
    """Career fair, employer presentation, workshop, placement talk, etc."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campus = models.ForeignKey("campus.Campus", on_delete=models.CASCADE, related_name="events")

    EVENT_TYPE_CHOICES = [
        ("placement_talk", "Placement Talk"),
        ("career_fair", "Career Fair"),
        ("employer_presentation", "Employer Presentation"),
        ("workshop", "Workshop / Skill Session"),
        ("hackathon", "Hackathon"),
        ("mock_interview", "Mock Interview Day"),
        ("networking", "Networking Event"),
        ("alumni_connect", "Alumni Connect"),
        ("webinar", "Webinar"),
        ("other", "Other"),
    ]

    title = models.CharField(max_length=250)
    event_type = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES)
    description = models.TextField(blank=True)
    organizer = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, related_name="events_organized")

    # Schedule
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    timezone = models.CharField(max_length=50, default="Asia/Colombo")

    # Venue
    mode = models.CharField(
        max_length=15,
        choices=[("online", "Online"), ("offline", "Offline"), ("hybrid", "Hybrid")],
        default="offline",
    )
    venue_name = models.CharField(max_length=200, blank=True)
    venue_room = models.CharField(max_length=100, blank=True)
    meeting_link = models.URLField(blank=True)

    # Eligibility
    target_programs = models.ManyToManyField("campus.Program", blank=True)
    target_years = models.JSONField(default=list, help_text="e.g. [1, 2, 3]")
    max_capacity = models.PositiveIntegerField(null=True, blank=True)

    # Employer link
    employer = models.ForeignKey(
        "campus_employers.CampusEmployer", null=True, blank=True, on_delete=models.SET_NULL, related_name="events"
    )

    # Status
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("cancelled", "Cancelled"),
        ("completed", "Completed"),
    ]
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="draft")
    banner_image_url = models.URLField(blank=True)
    is_mandatory = models.BooleanField(default=False)
    registration_deadline = models.DateTimeField(null=True, blank=True)
    allow_walk_in = models.BooleanField(default=False)

    class Meta:
        ordering = ["start_datetime"]

    def __str__(self):
        return f"{self.title} [{self.get_event_type_display()}]"


class EventRegistration(TimestampedModel):
    """Student registers for an event."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(CampusEvent, on_delete=models.CASCADE, related_name="registrations")
    student = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="event_registrations")
    registration_number = models.CharField(max_length=20, blank=True)
    attended = models.BooleanField(default=False)
    check_in_at = models.DateTimeField(null=True, blank=True)
    qr_code_data = models.CharField(max_length=100, blank=True)
    waitlisted = models.BooleanField(default=False)

    class Meta:
        unique_together = [["event", "student"]]
        ordering = ["-created_at"]


class EventFeedback(TimestampedModel):
    """Post-event feedback from a student."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    registration = models.OneToOneField(EventRegistration, on_delete=models.CASCADE, related_name="feedback")
    overall_rating = models.PositiveSmallIntegerField()
    content_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    speaker_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    organisation_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    comments = models.TextField(blank=True)
    would_recommend = models.BooleanField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class EventSpeaker(TimestampedModel):
    """A speaker/panelist at an event."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(CampusEvent, on_delete=models.CASCADE, related_name="speakers")
    name = models.CharField(max_length=200)
    designation = models.CharField(max_length=200, blank=True)
    company = models.CharField(max_length=200, blank=True)
    bio = models.TextField(blank=True)
    linkedin_url = models.URLField(blank=True)
    photo_url = models.URLField(blank=True)
    is_alumni = models.BooleanField(default=False)
