"""
Performance models — Review cycles, reviews, goals/OKRs, feedback.
"""

import uuid
from django.db import models
from django.conf import settings


class ReviewCycle(models.Model):
    """Performance review cycle (annual, quarterly, probation)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='review_cycles')
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=30, default='annual', choices=[
        ('annual', 'Annual'), ('semi_annual', 'Semi-Annual'),
        ('quarterly', 'Quarterly'), ('probation', 'Probation'),
    ])
    start_date = models.DateField()
    end_date = models.DateField()
    self_review_deadline = models.DateField(null=True, blank=True)
    manager_review_deadline = models.DateField(null=True, blank=True)
    calibration_deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, default='draft', choices=[
        ('draft', 'Draft'), ('active', 'Active'), ('in_review', 'In Review'),
        ('calibration', 'Calibration'), ('finalized', 'Finalized'),
    ])
    template_config = models.JSONField(default=dict, blank=True,
                                        help_text='Review template: competencies, rating scale, etc.')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'review_cycles'

    def __str__(self):
        return f"{self.name} ({self.type})"


class PerformanceReview(models.Model):
    """Individual performance review for an employee within a cycle."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='performance_reviews')
    cycle = models.ForeignKey(ReviewCycle, on_delete=models.CASCADE, related_name='reviews')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='performance_reviews')
    reviewer = models.ForeignKey('core_hr.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews_given')
    self_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    manager_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    final_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    self_comments = models.TextField(blank=True)
    manager_comments = models.TextField(blank=True)
    strengths = models.TextField(blank=True)
    improvements = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pending'), ('self_submitted', 'Self Submitted'),
        ('manager_submitted', 'Manager Submitted'), ('calibrated', 'Calibrated'),
        ('finalized', 'Finalized'),
    ])
    calibrated_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    calibrated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'performance_reviews'
        constraints = [
            models.UniqueConstraint(fields=['cycle', 'employee'], name='unique_review_per_cycle')
        ]

    def __str__(self):
        return f"{self.employee} — {self.cycle.name} (Rating: {self.final_rating or 'Pending'})"


class Goal(models.Model):
    """Goal / OKR — supports individual, team, department, and org-level goals."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='goals')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='goals')
    parent_goal = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sub_goals')
    cycle = models.ForeignKey(ReviewCycle, on_delete=models.SET_NULL, null=True, blank=True, related_name='goals')
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    type = models.CharField(max_length=20, default='individual', choices=[
        ('org', 'Organization'), ('department', 'Department'),
        ('team', 'Team'), ('individual', 'Individual'),
    ])
    metric_type = models.CharField(max_length=20, default='percentage', choices=[
        ('percentage', 'Percentage'), ('number', 'Number'),
        ('currency', 'Currency'), ('boolean', 'Yes/No'),
    ])
    target_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    current_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, default='active', choices=[
        ('active', 'Active'), ('completed', 'Completed'), ('cancelled', 'Cancelled'),
    ])
    progress = models.IntegerField(default=0, help_text="0-100 percentage")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'goals'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.progress}%)"


class Feedback(models.Model):
    """Continuous feedback / kudos between employees."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='feedbacks')
    from_employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='feedback_given')
    to_employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='feedback_received')
    type = models.CharField(max_length=20, default='kudos', choices=[
        ('kudos', 'Kudos'), ('feedback', 'Feedback'), ('coaching', 'Coaching'),
    ])
    message = models.TextField()
    is_public = models.BooleanField(default=True)
    tags = models.JSONField(default=list, blank=True, help_text='["teamwork", "innovation", "leadership"]')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'feedbacks'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.from_employee} → {self.to_employee}: {self.type}"


# ============ TALENT REVIEW & SUCCESSION (P1 upgrade) ============

class TalentReview(models.Model):
    """Calibration session for assessing employee potential and performance."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='talent_reviews')
    cycle = models.ForeignKey(ReviewCycle, on_delete=models.SET_NULL, null=True, blank=True, related_name='talent_reviews')
    name = models.CharField(max_length=255)
    review_date = models.DateField(null=True, blank=True)
    facilitator = models.ForeignKey('core_hr.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    scope = models.JSONField(default=dict, blank=True,
        help_text='{"departments":[], "levels":[], "all":false}')
    status = models.CharField(max_length=20, default='draft', choices=[
        ('draft', 'Draft'), ('in_progress', 'In Progress'), ('finalized', 'Finalized'),
    ])
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'talent_reviews'

    def __str__(self):
        return self.name


class NineBoxPlacement(models.Model):
    """9-box grid placement for an employee in a talent review."""
    PERFORMANCE_AXIS = [
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'),
    ]
    POTENTIAL_AXIS = [
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='nine_box_placements')
    talent_review = models.ForeignKey(TalentReview, on_delete=models.CASCADE, related_name='placements')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='nine_box_placements')
    performance = models.CharField(max_length=10, choices=PERFORMANCE_AXIS, default='medium')
    potential = models.CharField(max_length=10, choices=POTENTIAL_AXIS, default='medium')
    box_label = models.CharField(max_length=50, blank=True,
        help_text="e.g. 'Star', 'Core Player', 'Growth Employee'")
    notes = models.TextField(blank=True)
    assessed_by = models.ForeignKey('core_hr.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'nine_box_placements'
        constraints = [
            models.UniqueConstraint(fields=['talent_review', 'employee'], name='unique_nine_box_per_review')
        ]

    def __str__(self):
        return f"{self.employee} — {self.performance}/{self.potential} ({self.talent_review})"


class SuccessionPlan(models.Model):
    """Succession plan for a critical position."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='succession_plans')
    position = models.ForeignKey('core_hr.Position', on_delete=models.CASCADE, related_name='succession_plans')
    current_holder = models.ForeignKey('core_hr.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='succession_plans_as_holder')
    review_year = models.IntegerField()
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'succession_plans'
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'position', 'review_year'], name='unique_succession_plan')
        ]

    def __str__(self):
        return f"Succession: {self.position} ({self.review_year})"


class SuccessionCandidate(models.Model):
    """A candidate in a succession plan with readiness rating."""
    READINESS_CHOICES = [
        ('ready_now', 'Ready Now'),
        ('ready_1_2y', 'Ready in 1-2 Years'),
        ('ready_3_5y', 'Ready in 3-5 Years'),
        ('developmental', 'Developmental'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    succession_plan = models.ForeignKey(SuccessionPlan, on_delete=models.CASCADE, related_name='candidates')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='succession_candidacies')
    readiness = models.CharField(max_length=20, choices=READINESS_CHOICES, default='developmental')
    rank = models.IntegerField(default=1, help_text="Priority ranking among candidates")
    development_actions = models.JSONField(default=list, blank=True,
        help_text='[{"action":"...", "target_date":"..."}]')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'succession_candidates'
        constraints = [
            models.UniqueConstraint(fields=['succession_plan', 'employee'], name='unique_succession_candidate')
        ]
        ordering = ['rank']

    def __str__(self):
        return f"{self.employee} — {self.readiness}"


class PromotionReadiness(models.Model):
    """Tracks an employee's promotion readiness assessment."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='promotion_readiness')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='promotion_readiness')
    assessed_by = models.ForeignKey('core_hr.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    target_position = models.ForeignKey('core_hr.Position', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    readiness_score = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True,
        help_text="0.0–10.0 readiness score")
    readiness_label = models.CharField(max_length=20, default='not_ready', choices=[
        ('ready_now', 'Ready Now'), ('ready_soon', 'Ready Soon'),
        ('developing', 'Developing'), ('not_ready', 'Not Ready'),
    ])
    strengths = models.TextField(blank=True)
    gaps = models.TextField(blank=True)
    development_plan = models.JSONField(default=list, blank=True)
    assessment_date = models.DateField()
    next_review_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'promotion_readiness'
        ordering = ['-assessment_date']
        indexes = [
            models.Index(fields=['tenant', 'employee'], name='idx_promo_emp'),
        ]

    def __str__(self):
        return f"{self.employee} — {self.readiness_label} ({self.assessment_date})"
