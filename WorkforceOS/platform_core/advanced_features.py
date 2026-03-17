"""
Advanced Features — Knowledge Base, Benefits, Skill Matrix, Grievance models.
Covers T224-T232 from Phase 3.
"""

import uuid
from django.db import models
from django.conf import settings


# ======================== KNOWLEDGE BASE ========================

class KBCategory(models.Model):
    """Knowledge base article category."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='kb_categories')
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    icon = models.CharField(max_length=10, default='📖')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    sort_order = models.IntegerField(default=0)
    article_count = models.IntegerField(default=0)

    class Meta:
        app_label = 'platform_core'
        db_table = 'kb_categories'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return f"{self.icon} {self.name}"


class KBArticle(models.Model):
    """Knowledge base article."""
    STATUS_CHOICES = [('draft', 'Draft'), ('published', 'Published'), ('archived', 'Archived')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='kb_articles')
    category = models.ForeignKey(KBCategory, on_delete=models.SET_NULL, null=True, related_name='articles')
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=300)
    content = models.TextField(help_text="Markdown/HTML content")
    excerpt = models.CharField(max_length=500, blank=True)
    tags = models.JSONField(default=list)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_pinned = models.BooleanField(default=False)
    view_count = models.IntegerField(default=0)
    helpful_count = models.IntegerField(default=0)
    not_helpful_count = models.IntegerField(default=0)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'platform_core'
        db_table = 'kb_articles'
        ordering = ['-is_pinned', '-updated_at']

    def __str__(self):
        return self.title


# ======================== BENEFITS ========================

class BenefitPlan(models.Model):
    """Company benefit plan (insurance, retirement, wellness, etc.)."""
    PLAN_TYPES = [
        ('health', 'Health Insurance'), ('dental', 'Dental'), ('vision', 'Vision'),
        ('life', 'Life Insurance'), ('retirement', 'Retirement'), ('wellness', 'Wellness'),
        ('education', 'Education Allowance'), ('transport', 'Transport'), ('meal', 'Meal'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='benefit_plans')
    name = models.CharField(max_length=200)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES)
    description = models.TextField(blank=True)
    provider = models.CharField(max_length=200, blank=True)
    coverage_details = models.JSONField(default=dict, help_text="Plan-specific coverage info")
    employer_contribution = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    employee_contribution = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    enrollment_window_start = models.DateField(null=True, blank=True)
    enrollment_window_end = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'platform_core'
        db_table = 'benefit_plans'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_plan_type_display()})"


class BenefitEnrollment(models.Model):
    """Employee enrollment in a benefit plan."""
    STATUS_CHOICES = [('pending', 'Pending'), ('active', 'Active'), ('cancelled', 'Cancelled'), ('expired', 'Expired')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='benefit_enrollments')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='benefit_enrollments')
    plan = models.ForeignKey(BenefitPlan, on_delete=models.CASCADE, related_name='enrollments')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    coverage_tier = models.CharField(max_length=50, blank=True, help_text="e.g. Employee Only, Employee+Spouse, Family")
    dependents = models.JSONField(default=list, help_text="List of dependent details")
    effective_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    payroll_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'platform_core'
        db_table = 'benefit_enrollments'
        unique_together = ['employee', 'plan']


# ======================== SKILL MATRIX ========================

class SkillDefinition(models.Model):
    """Skill that can be assigned proficiency levels."""
    CATEGORIES = [
        ('technical', 'Technical'), ('soft', 'Soft Skills'), ('leadership', 'Leadership'),
        ('domain', 'Domain Knowledge'), ('language', 'Language'), ('certification', 'Certification'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='skills')
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORIES)
    description = models.TextField(blank=True)
    proficiency_levels = models.JSONField(default=list, help_text="""
        [{"level":1,"name":"Beginner"},{"level":2,"name":"Intermediate"},
         {"level":3,"name":"Advanced"},{"level":4,"name":"Expert"}]
    """)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = 'platform_core'
        db_table = 'skill_definitions'
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} ({self.category})"


class EmployeeSkill(models.Model):
    """Employee's proficiency in a specific skill."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='skills')
    skill = models.ForeignKey(SkillDefinition, on_delete=models.CASCADE, related_name='employee_skills')
    proficiency_level = models.IntegerField(default=1)
    target_level = models.IntegerField(null=True, blank=True, help_text="Desired proficiency")
    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    notes = models.TextField(blank=True)
    last_assessed = models.DateField(null=True, blank=True)

    class Meta:
        app_label = 'platform_core'
        db_table = 'employee_skills'
        unique_together = ['employee', 'skill']


# ======================== GRIEVANCE ========================

class GrievanceCase(models.Model):
    """Confidential grievance/complaint case."""
    SEVERITY_CHOICES = [('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')]
    STATUS_CHOICES = [
        ('submitted', 'Submitted'), ('under_review', 'Under Review'),
        ('investigation', 'Investigation'), ('resolved', 'Resolved'), ('closed', 'Closed'),
    ]
    CATEGORIES = [
        ('harassment', 'Harassment'), ('discrimination', 'Discrimination'),
        ('workplace_safety', 'Workplace Safety'), ('policy_violation', 'Policy Violation'),
        ('compensation', 'Compensation'), ('management', 'Management'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='grievances')
    case_number = models.CharField(max_length=20, unique=True)
    submitted_by = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='submitted_grievances')
    category = models.CharField(max_length=30, choices=CATEGORIES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='medium')
    subject = models.CharField(max_length=300)
    description = models.TextField()
    is_anonymous = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='assigned_grievances')
    resolution = models.TextField(blank=True)
    resolution_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'platform_core'
        db_table = 'grievance_cases'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.case_number}: {self.subject}"
