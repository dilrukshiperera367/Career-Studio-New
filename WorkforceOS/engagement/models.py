"""
Phase 2 models for Engagement module — Surveys, eNPS, Recognition.
"""

import uuid
from django.db import models
from django.conf import settings


class Survey(models.Model):
    """Pulse survey or engagement survey."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='engagement_surveys')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    type = models.CharField(max_length=30, default='pulse', choices=[
        ('pulse', 'Pulse Survey'), ('engagement', 'Engagement Survey'),
        ('enps', 'eNPS Survey'), ('exit', 'Exit Survey'), ('onboarding', 'Onboarding Survey'),
    ])
    questions = models.JSONField(default=list,
        help_text='[{"id":"q1","text":"...","type":"rating|text|choice|nps","options":["..."]}]')
    status = models.CharField(max_length=20, default='draft', choices=[
        ('draft', 'Draft'), ('active', 'Active'), ('closed', 'Closed'),
    ])
    target_audience = models.JSONField(default=dict, blank=True,
        help_text='{"departments":[],"branches":[],"all":true}')
    anonymous = models.BooleanField(default=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'surveys'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.type})"


class SurveyResponse(models.Model):
    """Individual survey response."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='survey_responses')
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='responses')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE,
                                 related_name='survey_responses', null=True, blank=True)
    answers = models.JSONField(default=dict, help_text='{"q1": 4, "q2": "Great culture"}')
    nps_score = models.IntegerField(null=True, blank=True, help_text="0-10 eNPS score")
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'survey_responses'
        constraints = [
            models.UniqueConstraint(fields=['survey', 'employee'], name='unique_survey_response')
        ]


class RecognitionEntry(models.Model):
    """Peer recognition / kudos wall entry."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='recognition_entries')
    from_employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='recognition_given')
    to_employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='recognition_received')
    category = models.CharField(max_length=50, default='kudos', choices=[
        ('kudos', 'Kudos'), ('shoutout', 'Shoutout'), ('award', 'Award'),
        ('milestone', 'Milestone'), ('innovation', 'Innovation'),
    ])
    message = models.TextField()
    badges = models.JSONField(default=list, blank=True, help_text='["teamwork","leadership","innovation"]')
    likes_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'recognition_entries'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.from_employee} → {self.to_employee}: {self.category}"


# ---------------------------------------------------------------------------
# P1 Upgrades — Stay Interviews, Lifecycle Survey Triggers, Manager Action Plans
# ---------------------------------------------------------------------------

class StayInterview(models.Model):
    """Structured stay interview record to understand retention drivers."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='stay_interviews')
    employee = models.ForeignKey(
        'core_hr.Employee', on_delete=models.CASCADE, related_name='stay_interviews',
    )
    interviewer = models.ForeignKey(
        'core_hr.Employee', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='conducted_stay_interviews',
    )
    scheduled_date = models.DateField(null=True, blank=True)
    conducted_date = models.DateField(null=True, blank=True)
    stay_factors = models.JSONField(default=list, blank=True,
        help_text='["growth","team","compensation","flexibility"]')
    leave_risks = models.JSONField(default=list, blank=True,
        help_text='["limited_growth","commute","workload"]')
    key_notes = models.TextField(blank=True)
    follow_up_actions = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='scheduled', choices=[
        ('scheduled', 'Scheduled'), ('completed', 'Completed'), ('cancelled', 'Cancelled'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'stay_interviews'
        ordering = ['-scheduled_date']

    def __str__(self):
        return f"Stay Interview: {self.employee} ({self.status})"


class LifecycleSurveyTrigger(models.Model):
    """Auto-trigger rules that send surveys at key employee lifecycle moments."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='lifecycle_survey_triggers')
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='lifecycle_triggers')
    trigger_event = models.CharField(max_length=50, choices=[
        ('hire', 'On Hire'), ('onboarding_complete', 'Onboarding Complete'),
        ('probation_end', 'Probation End'), ('anniversary', 'Work Anniversary'),
        ('promotion', 'Promotion'), ('transfer', 'Transfer'),
        ('manager_change', 'Manager Change'), ('offboarding_start', 'Offboarding Start'),
        ('exit', 'Exit'),
    ])
    delay_days = models.IntegerField(default=0,
        help_text="Days after trigger event before sending survey")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lifecycle_survey_triggers'
        ordering = ['trigger_event']

    def __str__(self):
        return f"{self.survey.title} on {self.trigger_event} (+{self.delay_days}d)"


class ManagerActionPlan(models.Model):
    """Action plan created by a manager in response to team engagement results."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='manager_action_plans')
    manager = models.ForeignKey(
        'core_hr.Employee', on_delete=models.CASCADE, related_name='action_plans',
    )
    survey = models.ForeignKey(
        Survey, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='action_plans',
    )
    title = models.CharField(max_length=255)
    focus_area = models.CharField(max_length=100, blank=True,
        help_text="e.g. 'Communication', 'Recognition', 'Work-Life Balance'")
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='draft', choices=[
        ('draft', 'Draft'), ('active', 'Active'), ('completed', 'Completed'),
    ])
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'manager_action_plans'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.manager}: {self.title}"


class ManagerActionItem(models.Model):
    """A single action item within a ManagerActionPlan."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(ManagerActionPlan, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=500)
    assigned_to = models.ForeignKey(
        'core_hr.Employee', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='action_items',
    )
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pending'), ('in_progress', 'In Progress'),
        ('completed', 'Completed'), ('cancelled', 'Cancelled'),
    ])
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'manager_action_items'
        ordering = ['due_date']

    def __str__(self):
        return f"{self.plan}: {self.description[:60]}"
