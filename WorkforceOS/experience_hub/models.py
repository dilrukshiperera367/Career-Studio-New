"""
Experience Hub models.
Covers: ERG, ERGMembership, CommunityEvent, EventRSVP,
        RecognitionProgram, RecognitionNomination.
"""

import uuid
from django.db import models
from django.conf import settings


class ERG(models.Model):
    """Employee Resource Group."""

    CATEGORY_CHOICES = [
        ('diversity', 'Diversity'),
        ('wellness', 'Wellness'),
        ('professional', 'Professional'),
        ('social', 'Social'),
        ('volunteering', 'Volunteering'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE, related_name='ergs'
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    mission = models.TextField(blank=True)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    lead = models.ForeignKey(
        'core_hr.Employee', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='led_ergs'
    )
    is_active = models.BooleanField(default=True)
    member_count = models.IntegerField(default=0)
    logo_url = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'experience_hub'
        db_table = 'ergs'

    def __str__(self):
        return self.name


class ERGMembership(models.Model):
    """Employee membership in an ERG."""

    ROLE_CHOICES = [
        ('member', 'Member'),
        ('lead', 'Lead'),
        ('co_lead', 'Co-Lead'),
        ('coordinator', 'Coordinator'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE, related_name='erg_memberships'
    )
    erg = models.ForeignKey(ERG, on_delete=models.CASCADE, related_name='memberships')
    employee = models.ForeignKey(
        'core_hr.Employee', on_delete=models.CASCADE, related_name='erg_memberships'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = 'experience_hub'
        db_table = 'erg_memberships'
        unique_together = ['erg', 'employee']

    def __str__(self):
        return f"{self.employee} — {self.erg.name} ({self.role})"


class CommunityEvent(models.Model):
    """ERG/company community event."""

    EVENT_TYPE_CHOICES = [
        ('webinar', 'Webinar'),
        ('workshop', 'Workshop'),
        ('social', 'Social'),
        ('volunteering', 'Volunteering'),
        ('celebration', 'Celebration'),
        ('training', 'Training'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE, related_name='community_events'
    )
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES)
    organizer = models.ForeignKey(
        'core_hr.Employee', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='organised_events'
    )
    erg = models.ForeignKey(
        ERG, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='events'
    )
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    location = models.CharField(max_length=300, blank=True)
    is_virtual = models.BooleanField(default=False)
    meeting_url = models.CharField(max_length=500, blank=True)
    max_attendees = models.IntegerField(null=True, blank=True)
    rsvp_deadline = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    attendees_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'experience_hub'
        db_table = 'community_events'
        ordering = ['-start_datetime']

    def __str__(self):
        return self.title


class EventRSVP(models.Model):
    """Employee RSVP to a community event."""

    STATUS_CHOICES = [
        ('attending', 'Attending'),
        ('not_attending', 'Not Attending'),
        ('maybe', 'Maybe'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE, related_name='event_rsvps'
    )
    event = models.ForeignKey(
        CommunityEvent, on_delete=models.CASCADE, related_name='rsvps'
    )
    employee = models.ForeignKey(
        'core_hr.Employee', on_delete=models.CASCADE, related_name='event_rsvps'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='attending')
    registered_at = models.DateTimeField(auto_now_add=True)
    attended = models.BooleanField(null=True)

    class Meta:
        app_label = 'experience_hub'
        db_table = 'event_rsvps'
        unique_together = ['event', 'employee']

    def __str__(self):
        return f"{self.employee} — {self.event.title} ({self.status})"


class RecognitionProgram(models.Model):
    """Configurable recognition program (spot awards, peer kudos, etc.)."""

    PROGRAM_TYPE_CHOICES = [
        ('spot_award', 'Spot Award'),
        ('peer_kudos', 'Peer Kudos'),
        ('milestone', 'Milestone'),
        ('manager_recognition', 'Manager Recognition'),
        ('anniversary', 'Anniversary'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE, related_name='recognition_programs'
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    program_type = models.CharField(
        max_length=30, choices=PROGRAM_TYPE_CHOICES, default='peer_kudos'
    )
    point_value = models.IntegerField(default=0)
    badge_icon = models.CharField(max_length=10, blank=True)
    is_active = models.BooleanField(default=True)
    requires_approval = models.BooleanField(default=False)
    max_per_month_per_giver = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'experience_hub'
        db_table = 'recognition_programs'

    def __str__(self):
        return self.name


class RecognitionNomination(models.Model):
    """Nomination/award under a recognition program."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE, related_name='recognition_nominations'
    )
    program = models.ForeignKey(
        RecognitionProgram, on_delete=models.CASCADE, related_name='nominations'
    )
    nominator = models.ForeignKey(
        'core_hr.Employee', on_delete=models.CASCADE, related_name='given_nominations'
    )
    nominee = models.ForeignKey(
        'core_hr.Employee', on_delete=models.CASCADE, related_name='received_nominations'
    )
    reason = models.TextField()
    is_public = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='approved')
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='approved_nominations'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    points_awarded = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'experience_hub'
        db_table = 'recognition_nominations'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.nominator} nominated {self.nominee} — {self.program.name}"
