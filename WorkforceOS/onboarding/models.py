"""
Onboarding models — Templates, instances, tasks, and assets.
"""

import uuid
from django.db import models
from django.conf import settings


class OnboardingTemplate(models.Model):
    """Reusable onboarding checklist template."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='onboarding_templates')
    name = models.CharField(max_length=100)
    applicable_to = models.JSONField(default=dict, blank=True,
                                      help_text='{"departments": [], "positions": [], "contract_types": []}')
    tasks = models.JSONField(default=list,
                             help_text='[{"title":"...", "category":"hr|it|manager|employee", "assignee_role":"...", "due_offset_days": 7, "description":"...", "is_required": true}]')
    status = models.CharField(max_length=20, default='active', choices=[
        ('active', 'Active'), ('inactive', 'Inactive'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'onboarding_templates'

    def __str__(self):
        return self.name


class OnboardingInstance(models.Model):
    """Active onboarding process for a specific employee."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='onboarding_instances')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='onboarding_instances')
    template = models.ForeignKey(OnboardingTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default='in_progress', choices=[
        ('in_progress', 'In Progress'), ('completed', 'Completed'), ('cancelled', 'Cancelled'),
    ])
    start_date = models.DateField()
    target_completion = models.DateField(null=True, blank=True)
    completion_pct = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'onboarding_instances'

    def __str__(self):
        return f"Onboarding: {self.employee} ({self.completion_pct}%)"

    def recalculate_progress(self):
        """Recalculate completion percentage based on task statuses."""
        total = self.tasks.count()
        if total == 0:
            self.completion_pct = 0
        else:
            completed = self.tasks.filter(status='completed').count()
            self.completion_pct = int((completed / total) * 100)
        self.save(update_fields=['completion_pct', 'updated_at'])


class OnboardingTask(models.Model):
    """Individual task in an onboarding checklist."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='onboarding_tasks')
    instance = models.ForeignKey(OnboardingInstance, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=30, choices=[
        ('hr', 'HR'), ('it', 'IT'), ('manager', 'Manager'),
        ('employee', 'Employee'), ('facilities', 'Facilities'),
    ])
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='assigned_onboarding_tasks')
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pending'), ('in_progress', 'In Progress'),
        ('completed', 'Completed'), ('skipped', 'Skipped'),
    ])
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'onboarding_tasks'
        ordering = ['sort_order', 'created_at']

    def __str__(self):
        return f"{self.title} ({self.status})"


class Asset(models.Model):
    """Company asset tracking (laptops, phones, keys, etc.)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='assets')
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=[
        ('laptop', 'Laptop'), ('phone', 'Phone'), ('id_card', 'ID Card'),
        ('key', 'Key'), ('uniform', 'Uniform'), ('vehicle', 'Vehicle'),
        ('furniture', 'Furniture'), ('other', 'Other'),
    ])
    serial_number = models.CharField(max_length=100, blank=True)
    assigned_to = models.ForeignKey('core_hr.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='assets')
    assigned_date = models.DateField(null=True, blank=True)
    return_date = models.DateField(null=True, blank=True)
    condition = models.CharField(max_length=20, default='good', choices=[
        ('new', 'New'), ('good', 'Good'), ('fair', 'Fair'), ('damaged', 'Damaged'),
    ])
    status = models.CharField(max_length=20, default='available', choices=[
        ('available', 'Available'), ('assigned', 'Assigned'),
        ('returned', 'Returned'), ('damaged', 'Damaged'), ('disposed', 'Disposed'),
    ])
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'assets'

    def __str__(self):
        return f"{self.name} ({self.serial_number or self.category})"


# ============ PREBOARDING, BUDDY & 30/60/90-DAY PLAN (P1 upgrade) ============

class PreboardingPortal(models.Model):
    """Pre-hire portal access and task tracking before the start date."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='preboarding_portals')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='preboarding_portal')
    token = models.CharField(max_length=64, unique=True, help_text="Secure access token for portal link")
    welcome_message = models.TextField(blank=True)
    documents_to_complete = models.JSONField(default=list, blank=True,
        help_text='[{"title":"Tax Form", "url":"..."}]')
    tasks_completed = models.JSONField(default=list, blank=True,
        help_text='["tax_form", "bank_details", "policy_acknowledgement"]')
    portal_opened_at = models.DateTimeField(null=True, blank=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pending'), ('active', 'Active'), ('completed', 'Completed'), ('expired', 'Expired'),
    ])
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'preboarding_portals'

    def __str__(self):
        return f"Preboarding: {self.employee}"


class BuddyAssignment(models.Model):
    """Assigns an onboarding buddy to a new employee."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='buddy_assignments')
    new_employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='buddy_assignments_as_new')
    buddy = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='buddy_assignments_as_buddy')
    onboarding_instance = models.ForeignKey(OnboardingInstance, on_delete=models.SET_NULL, null=True, blank=True, related_name='buddy_assignments')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    meeting_frequency = models.CharField(max_length=20, default='weekly', choices=[
        ('daily', 'Daily'), ('weekly', 'Weekly'), ('biweekly', 'Bi-Weekly'), ('monthly', 'Monthly'),
    ])
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='active', choices=[
        ('active', 'Active'), ('completed', 'Completed'), ('cancelled', 'Cancelled'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'buddy_assignments'
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'new_employee', 'buddy'], name='unique_buddy_assignment')
        ]

    def __str__(self):
        return f"{self.new_employee} ← Buddy: {self.buddy}"


class MilestonePlan(models.Model):
    """30/60/90-day (or custom) milestone plan for a new employee."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='milestone_plans')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='milestone_plans')
    onboarding_instance = models.ForeignKey(OnboardingInstance, on_delete=models.SET_NULL, null=True, blank=True, related_name='milestone_plans')
    name = models.CharField(max_length=100, default='30-60-90 Day Plan')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    status = models.CharField(max_length=20, default='active', choices=[
        ('draft', 'Draft'), ('active', 'Active'), ('completed', 'Completed'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'milestone_plans'

    def __str__(self):
        return f"{self.name} — {self.employee}"


class MilestonePlanItem(models.Model):
    """Individual milestone item within a plan."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(MilestonePlan, on_delete=models.CASCADE, related_name='items')
    phase = models.CharField(max_length=20, default='30_day', choices=[
        ('preboarding', 'Pre-boarding'), ('first_week', 'First Week'),
        ('30_day', '30 Day'), ('60_day', '60 Day'), ('90_day', '90 Day'), ('custom', 'Custom'),
    ])
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    success_criteria = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    owner = models.ForeignKey('core_hr.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pending'), ('in_progress', 'In Progress'),
        ('completed', 'Completed'), ('skipped', 'Skipped'),
    ])
    completed_at = models.DateTimeField(null=True, blank=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = 'milestone_plan_items'
        ordering = ['phase', 'sort_order']

    def __str__(self):
        return f"[{self.phase}] {self.title}"
