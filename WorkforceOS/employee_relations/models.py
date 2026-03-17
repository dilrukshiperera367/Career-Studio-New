"""
Employee Relations — ER cases, investigations, disciplinary actions, grievances, ethics intake.
"""

import uuid
from django.db import models
from django.conf import settings


class ERCase(models.Model):
    """Employee relations case (disciplinary, performance, investigation, ethics, grievance)."""
    CASE_TYPES = [
        ('disciplinary', 'Disciplinary'),
        ('performance_concern', 'Performance Concern'),
        ('harassment', 'Harassment'),
        ('discrimination', 'Discrimination'),
        ('policy_violation', 'Policy Violation'),
        ('ethics', 'Ethics / Whistleblower'),
        ('grievance', 'Grievance'),
        ('conflict', 'Workplace Conflict'),
        ('accommodation', 'Accommodation Request'),
        ('other', 'Other'),
    ]
    SEVERITY_CHOICES = [
        ('minor', 'Minor'), ('moderate', 'Moderate'), ('serious', 'Serious'), ('critical', 'Critical'),
    ]
    STATUS_CHOICES = [
        ('intake', 'Intake'),
        ('assigned', 'Assigned'),
        ('investigation', 'Under Investigation'),
        ('hearing', 'Hearing Scheduled'),
        ('pending_outcome', 'Pending Outcome'),
        ('outcome_issued', 'Outcome Issued'),
        ('appeal', 'Under Appeal'),
        ('closed', 'Closed'),
        ('withdrawn', 'Withdrawn'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='er_cases')
    case_number = models.CharField(max_length=30, unique=True)
    case_type = models.CharField(max_length=30, choices=CASE_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='moderate')
    subject_employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE,
                                          related_name='er_cases_as_subject')
    complainant = models.ForeignKey('core_hr.Employee', on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='er_cases_as_complainant')
    is_anonymous = models.BooleanField(default=False)
    title = models.CharField(max_length=400)
    description = models.TextField()
    incident_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='intake')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='assigned_er_cases')
    investigating_officer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                               null=True, blank=True, related_name='investigating_er_cases')
    sla_response_due = models.DateTimeField(null=True, blank=True)
    sla_resolution_due = models.DateTimeField(null=True, blank=True)
    response_given_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    outcome_summary = models.TextField(blank=True)
    is_confidential = models.BooleanField(default=True)
    tags = models.JSONField(default=list)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'employee_relations'
        db_table = 'er_cases'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.case_number}: {self.title} ({self.status})"


class ERCaseNote(models.Model):
    """Notes / updates added to an ER case during its lifecycle."""
    NOTE_TYPES = [
        ('update', 'Status Update'), ('interview', 'Interview Note'),
        ('evidence', 'Evidence Note'), ('decision', 'Decision Note'),
        ('communication', 'Communication Log'), ('legal', 'Legal Note'),
        ('internal', 'Internal Note'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case = models.ForeignKey(ERCase, on_delete=models.CASCADE, related_name='notes')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')
    note_type = models.CharField(max_length=20, choices=NOTE_TYPES, default='update')
    content = models.TextField()
    attachments = models.JSONField(default=list)
    is_confidential = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'employee_relations'
        db_table = 'er_case_notes'
        ordering = ['created_at']

    def __str__(self):
        return f"Note on {self.case.case_number} by {self.author}"


class DisciplinaryAction(models.Model):
    """Formal disciplinary action taken as an outcome of an ER case."""
    ACTION_TYPES = [
        ('verbal_warning', 'Verbal Warning'),
        ('written_warning', 'Written Warning'),
        ('final_warning', 'Final Written Warning'),
        ('suspension', 'Suspension'),
        ('demotion', 'Demotion'),
        ('termination_cause', 'Termination for Cause'),
        ('no_action', 'No Action Taken'),
        ('coaching_required', 'Coaching Required'),
    ]
    STATUS_CHOICES = [
        ('draft', 'Draft'), ('issued', 'Issued'), ('acknowledged', 'Employee Acknowledged'),
        ('appealed', 'Appealed'), ('overturned', 'Overturned'), ('closed', 'Closed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='disciplinary_actions')
    case = models.ForeignKey(ERCase, on_delete=models.CASCADE, related_name='disciplinary_actions')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='disciplinary_actions')
    action_type = models.CharField(max_length=25, choices=ACTION_TYPES)
    effective_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True, help_text='Date warning expires from record')
    suspension_days = models.IntegerField(null=True, blank=True)
    description = models.TextField()
    conditions = models.TextField(blank=True, help_text='Conditions attached to the action')
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    appeal_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'employee_relations'
        db_table = 'disciplinary_actions'
        ordering = ['-effective_date']

    def __str__(self):
        return f"{self.action_type}: {self.employee} ({self.effective_date})"


class PImprovementPlan(models.Model):
    """Performance Improvement Plan (PIP)."""
    STATUS_CHOICES = [
        ('draft', 'Draft'), ('active', 'Active'), ('completed_success', 'Completed — Successful'),
        ('completed_failure', 'Completed — Not Met'), ('withdrawn', 'Withdrawn'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='pips')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='pips')
    manager = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='managed_pips')
    hr_partner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name='+')
    title = models.CharField(max_length=300)
    performance_concerns = models.TextField()
    objectives = models.JSONField(default=list,
        help_text='[{"goal":"...","metric":"...","target":"...","deadline":"2024-03-01"}]')
    support_provided = models.TextField(blank=True)
    start_date = models.DateField()
    review_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='draft')
    outcome_notes = models.TextField(blank=True)
    check_in_notes = models.JSONField(default=list,
        help_text='[{"date":"2024-02-01","notes":"Progress noted","by":"manager_uuid"}]')
    employee_acknowledged_at = models.DateTimeField(null=True, blank=True)
    related_er_case = models.ForeignKey(ERCase, on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name='pips')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'employee_relations'
        db_table = 'performance_improvement_plans'
        ordering = ['-start_date']

    def __str__(self):
        return f"PIP: {self.employee} ({self.start_date} — {self.end_date})"


class EthicsIntake(models.Model):
    """Anonymous or named ethics/whistleblower report."""
    STATUS_CHOICES = [
        ('received', 'Received'), ('triaged', 'Triaged'), ('investigation', 'Under Investigation'),
        ('resolved', 'Resolved'), ('closed', 'Closed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='ethics_intakes')
    reference_code = models.CharField(max_length=20, unique=True,
                                       help_text='Short code given to reporter to track status anonymously')
    category = models.CharField(max_length=50, choices=[
        ('fraud', 'Fraud'), ('bribery', 'Bribery'), ('harassment', 'Harassment'),
        ('safety', 'Safety Violation'), ('data_privacy', 'Data Privacy'),
        ('conflict_interest', 'Conflict of Interest'), ('other', 'Other'),
    ])
    subject = models.CharField(max_length=400)
    description = models.TextField()
    is_anonymous = models.BooleanField(default=True)
    reporter_employee = models.ForeignKey('core_hr.Employee', on_delete=models.SET_NULL,
                                           null=True, blank=True, related_name='ethics_reports')
    attachments = models.JSONField(default=list)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='received')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='+')
    resolution = models.TextField(blank=True)
    related_er_case = models.ForeignKey(ERCase, on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name='ethics_intakes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'employee_relations'
        db_table = 'ethics_intakes'
        ordering = ['-created_at']

    def __str__(self):
        return f"Ethics #{self.reference_code}: {self.category} ({self.status})"
