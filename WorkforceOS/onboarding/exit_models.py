"""
Exit / Offboarding models — resignation, exit pipeline, exit interview.
Added as extension to the onboarding app.
"""

import uuid
from django.db import models
from django.conf import settings


class ExitRequest(models.Model):
    """Employee exit/resignation request with notice period tracking."""
    EXIT_TYPES = [
        ('resignation', 'Resignation'), ('termination', 'Termination'),
        ('retirement', 'Retirement'), ('contract_end', 'Contract End'),
        ('mutual', 'Mutual Separation'),
    ]
    STATUS_CHOICES = [
        ('submitted', 'Submitted'), ('accepted', 'Accepted'),
        ('notice_period', 'Notice Period'), ('handover', 'Handover'),
        ('exit_interview', 'Exit Interview'), ('settlement', 'Final Settlement'),
        ('completed', 'Completed'), ('withdrawn', 'Withdrawn'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='exit_requests')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='exit_requests')
    exit_type = models.CharField(max_length=30, choices=EXIT_TYPES)
    reason = models.TextField(blank=True)
    resignation_date = models.DateField()
    last_working_date = models.DateField(null=True, blank=True)
    notice_period_days = models.IntegerField(default=30)
    notice_served = models.BooleanField(default=False)
    notice_buyout = models.BooleanField(default=False, help_text="Employee buying out notice period")
    status = models.CharField(max_length=20, default='submitted', choices=STATUS_CHOICES)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='+')
    settlement_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    settlement_details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'exit_requests'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee} — {self.exit_type} ({self.status})"


class ExitChecklist(models.Model):
    """Checklist items for offboarding (asset return, access revoke, etc.)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exit_request = models.ForeignKey(ExitRequest, on_delete=models.CASCADE, related_name='checklist_items')
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=30, choices=[
        ('hr', 'HR'), ('it', 'IT'), ('finance', 'Finance'),
        ('manager', 'Manager'), ('facilities', 'Facilities'),
    ])
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                  null=True, blank=True, related_name='+')
    status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pending'), ('in_progress', 'In Progress'),
        ('completed', 'Completed'), ('skipped', 'Skipped'),
    ])
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = 'exit_checklist_items'
        ordering = ['sort_order']

    def __str__(self):
        return f"{self.title} ({self.status})"


class ExitInterview(models.Model):
    """Exit interview record with templated questions and responses."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exit_request = models.OneToOneField(ExitRequest, on_delete=models.CASCADE, related_name='exit_interview')
    conducted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                      null=True, blank=True, related_name='+')
    conducted_at = models.DateTimeField(null=True, blank=True)
    responses = models.JSONField(default=dict,
        help_text='{"reason_for_leaving":"...","would_recommend":true,"satisfaction_rating":3,"feedback":"..."}')
    overall_experience_rating = models.IntegerField(null=True, blank=True, help_text="1-5 rating")
    manager_rating = models.IntegerField(null=True, blank=True, help_text="1-5 rating")
    would_rejoin = models.BooleanField(null=True, blank=True)
    would_recommend = models.BooleanField(null=True, blank=True)
    additional_comments = models.TextField(blank=True)
    is_confidential = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'exit_interviews'

    def __str__(self):
        return f"Exit Interview — {self.exit_request.employee}"
