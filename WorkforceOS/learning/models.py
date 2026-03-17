"""
Phase 2 models for Learning & Development — Courses, Enrollments, Certifications.
"""

import uuid
from django.db import models
from django.conf import settings


class Course(models.Model):
    """Training course / learning program."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='courses')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, default='general', choices=[
        ('compliance', 'Compliance'), ('technical', 'Technical'), ('soft_skills', 'Soft Skills'),
        ('leadership', 'Leadership'), ('onboarding', 'Onboarding'), ('general', 'General'),
    ])
    provider = models.CharField(max_length=100, blank=True, help_text="Internal or external provider name")
    duration_hours = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    format = models.CharField(max_length=30, default='online', choices=[
        ('online', 'Online'), ('classroom', 'Classroom'), ('blended', 'Blended'),
        ('self_paced', 'Self-Paced'), ('workshop', 'Workshop'),
    ])
    max_enrollments = models.IntegerField(null=True, blank=True)
    mandatory_for = models.JSONField(default=dict, blank=True,
        help_text='{"departments":[],"positions":[],"all":false}')
    content_url = models.URLField(max_length=500, blank=True)
    status = models.CharField(max_length=20, default='active', choices=[
        ('draft', 'Draft'), ('active', 'Active'), ('archived', 'Archived'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'courses'
        ordering = ['title']

    def __str__(self):
        return self.title


class CourseEnrollment(models.Model):
    """Employee enrollment in a course."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='course_enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='course_enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    progress = models.IntegerField(default=0, help_text="0-100")
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, default='enrolled', choices=[
        ('enrolled', 'Enrolled'), ('in_progress', 'In Progress'),
        ('completed', 'Completed'), ('dropped', 'Dropped'),
    ])

    class Meta:
        db_table = 'course_enrollments'
        constraints = [
            models.UniqueConstraint(fields=['course', 'employee'], name='unique_enrollment')
        ]

    def __str__(self):
        return f"{self.employee} → {self.course.title} ({self.status})"


class Certification(models.Model):
    """Employee certification with expiry tracking."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='certifications')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='certifications')
    name = models.CharField(max_length=255)
    issuing_body = models.CharField(max_length=255, blank=True)
    credential_id = models.CharField(max_length=255, blank=True)
    issued_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    verification_url = models.URLField(max_length=500, blank=True)
    status = models.CharField(max_length=20, default='active', choices=[
        ('active', 'Active'), ('expired', 'Expired'), ('revoked', 'Revoked'),
    ])
    reminder_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'certifications'
        ordering = ['-issued_date']

    def __str__(self):
        return f"{self.name} — {self.employee}"


# ---------------------------------------------------------------------------
# P1 Upgrades — Skill Pathways, Mentorship, LXP Recommendations
# ---------------------------------------------------------------------------

class SkillPathway(models.Model):
    """A curated learning pathway targeting one or more skills."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='skill_pathways')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    target_skills = models.JSONField(default=list, blank=True,
        help_text="List of skill definition IDs this pathway develops")
    target_roles = models.JSONField(default=list, blank=True,
        help_text="List of position IDs this pathway prepares for")
    estimated_hours = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    status = models.CharField(max_length=20, default='active', choices=[
        ('draft', 'Draft'), ('active', 'Active'), ('archived', 'Archived'),
    ])
    created_by = models.ForeignKey(
        'core_hr.Employee', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='created_pathways',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'skill_pathways'
        ordering = ['title']

    def __str__(self):
        return self.title


class PathwayStep(models.Model):
    """An ordered step (course) within a SkillPathway."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pathway = models.ForeignKey(SkillPathway, on_delete=models.CASCADE, related_name='steps')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='pathway_steps')
    order = models.PositiveIntegerField(default=1)
    is_required = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'pathway_steps'
        ordering = ['pathway', 'order']
        unique_together = [('pathway', 'order')]

    def __str__(self):
        return f"{self.pathway.title} — Step {self.order}: {self.course.title}"


class MentorshipProgram(models.Model):
    """A structured mentorship programme within a tenant."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='mentorship_programs')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    program_type = models.CharField(max_length=30, default='one_on_one', choices=[
        ('one_on_one', 'One-on-One'), ('group', 'Group'), ('peer', 'Peer'),
        ('reverse', 'Reverse Mentorship'),
    ])
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    max_matches = models.IntegerField(null=True, blank=True)
    matching_criteria = models.JSONField(default=dict, blank=True,
        help_text='{"skills":[],"departments":[],"seniority_gap":0}')
    status = models.CharField(max_length=20, default='active', choices=[
        ('draft', 'Draft'), ('active', 'Active'), ('completed', 'Completed'), ('cancelled', 'Cancelled'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mentorship_programs'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class MentorshipMatch(models.Model):
    """A mentor–mentee pairing within a MentorshipProgram."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    program = models.ForeignKey(MentorshipProgram, on_delete=models.CASCADE, related_name='matches')
    mentor = models.ForeignKey(
        'core_hr.Employee', on_delete=models.CASCADE, related_name='mentor_matches',
    )
    mentee = models.ForeignKey(
        'core_hr.Employee', on_delete=models.CASCADE, related_name='mentee_matches',
    )
    matched_at = models.DateTimeField(auto_now_add=True)
    goals = models.TextField(blank=True)
    meeting_frequency = models.CharField(max_length=30, default='monthly', choices=[
        ('weekly', 'Weekly'), ('biweekly', 'Bi-Weekly'),
        ('monthly', 'Monthly'), ('adhoc', 'Ad-Hoc'),
    ])
    status = models.CharField(max_length=20, default='active', choices=[
        ('pending', 'Pending'), ('active', 'Active'),
        ('completed', 'Completed'), ('cancelled', 'Cancelled'),
    ])
    ended_at = models.DateTimeField(null=True, blank=True)
    feedback = models.TextField(blank=True)

    class Meta:
        db_table = 'mentorship_matches'
        ordering = ['-matched_at']

    def __str__(self):
        return f"{self.mentor} → {self.mentee} ({self.program.name})"


class LXPRecommendation(models.Model):
    """AI/LXP-generated learning recommendation for an employee."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='lxp_recommendations')
    employee = models.ForeignKey(
        'core_hr.Employee', on_delete=models.CASCADE, related_name='lxp_recommendations',
    )
    course = models.ForeignKey(
        Course, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='lxp_recommendations',
    )
    pathway = models.ForeignKey(
        SkillPathway, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='lxp_recommendations',
    )
    reason = models.CharField(max_length=50, default='skill_gap', choices=[
        ('skill_gap', 'Skill Gap'), ('career_goal', 'Career Goal'),
        ('role_transition', 'Role Transition'), ('mandatory', 'Mandatory'),
        ('peer_completion', 'Peer Completion'), ('manager_assigned', 'Manager Assigned'),
    ])
    reason_detail = models.TextField(blank=True)
    score = models.FloatField(default=0.0, help_text="Relevance score 0.0–1.0")
    is_dismissed = models.BooleanField(default=False)
    is_enrolled = models.BooleanField(default=False)
    generated_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'lxp_recommendations'
        ordering = ['-score', '-generated_at']

    def __str__(self):
        target = self.course or self.pathway
        return f"Rec for {self.employee}: {target} ({self.reason})"
