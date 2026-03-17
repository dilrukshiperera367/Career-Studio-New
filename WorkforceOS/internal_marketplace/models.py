"""
Internal Talent Marketplace — internal job postings, gig projects, skill-based matching, mobility applications.
"""

import uuid
from django.db import models
from django.conf import settings


class InternalJobPosting(models.Model):
    """Internal job opening posted for current employees to apply."""
    POSTING_TYPES = [
        ('full_time', 'Full-Time Transfer'),
        ('part_time', 'Part-Time Role'),
        ('stretch', 'Stretch Assignment'),
        ('secondment', 'Secondment'),
        ('rotation', 'Rotation'),
        ('project', 'Project Role'),
    ]
    STATUS_CHOICES = [
        ('draft', 'Draft'), ('open', 'Open'), ('closed', 'Closed'), ('filled', 'Filled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='internal_postings')
    title = models.CharField(max_length=300)
    posting_type = models.CharField(max_length=20, choices=POSTING_TYPES, default='full_time')
    department = models.ForeignKey('core_hr.Department', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='internal_postings')
    position = models.ForeignKey('core_hr.Position', on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='internal_postings')
    hiring_manager = models.ForeignKey('core_hr.Employee', on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='managed_internal_postings')
    description = models.TextField()
    required_skills = models.JSONField(default=list,
        help_text='[{"skill_id":"uuid","min_proficiency":2}]')
    preferred_skills = models.JSONField(default=list)
    min_experience_years = models.IntegerField(default=0)
    min_tenure_months = models.IntegerField(default=0, help_text='Minimum months in current role')
    grade_range = models.JSONField(default=list, help_text='["G4","G5","G6"]')
    open_date = models.DateField()
    close_date = models.DateField(null=True, blank=True)
    target_start_date = models.DateField(null=True, blank=True)
    duration_months = models.IntegerField(null=True, blank=True, help_text='For fixed-term postings')
    is_visible_org_wide = models.BooleanField(default=True)
    visible_to_departments = models.JSONField(default=list, help_text='Restrict visibility; empty=all')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    applications_count = models.IntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'internal_marketplace'
        db_table = 'internal_job_postings'
        ordering = ['-open_date']

    def __str__(self):
        return f"{self.title} ({self.posting_type})"


class InternalApplication(models.Model):
    """Employee application to an internal job posting."""
    STATUS_CHOICES = [
        ('applied', 'Applied'), ('screening', 'Screening'), ('shortlisted', 'Shortlisted'),
        ('interview', 'Interview'), ('offered', 'Offered'), ('accepted', 'Accepted'),
        ('rejected', 'Rejected'), ('withdrawn', 'Withdrawn'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='internal_applications')
    posting = models.ForeignKey(InternalJobPosting, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='internal_applications')
    cover_note = models.TextField(blank=True)
    skill_match_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                             help_text='System-computed skill match %')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='applied')
    rejection_reason = models.TextField(blank=True)
    manager_endorsed = models.BooleanField(null=True, blank=True)
    manager_endorsement_note = models.TextField(blank=True)
    interview_notes = models.TextField(blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'internal_marketplace'
        db_table = 'internal_applications'
        unique_together = ['posting', 'applicant']
        ordering = ['-applied_at']

    def __str__(self):
        return f"{self.applicant} → {self.posting}"


class GigProject(models.Model):
    """Short-term gig/project opportunity for employees to contribute to."""
    STATUS_CHOICES = [
        ('draft', 'Draft'), ('open', 'Open'), ('in_progress', 'In Progress'),
        ('completed', 'Completed'), ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='gig_projects')
    title = models.CharField(max_length=300)
    description = models.TextField()
    owner = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='owned_gig_projects')
    required_skills = models.JSONField(default=list)
    team_size = models.IntegerField(default=1)
    estimated_hours = models.IntegerField(default=0)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    tags = models.JSONField(default=list)
    participants_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'internal_marketplace'
        db_table = 'gig_projects'
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.title} ({self.status})"


class GigParticipation(models.Model):
    """Employee participation in a gig project."""
    STATUS_CHOICES = [
        ('interested', 'Interested'), ('confirmed', 'Confirmed'),
        ('active', 'Active'), ('completed', 'Completed'), ('withdrew', 'Withdrew'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='gig_participations')
    project = models.ForeignKey(GigProject, on_delete=models.CASCADE, related_name='participations')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='gig_participations')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='interested')
    hours_contributed = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    completion_rating = models.IntegerField(null=True, blank=True, help_text='1-5 rating from project owner')
    feedback = models.TextField(blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'internal_marketplace'
        db_table = 'gig_participations'
        unique_together = ['project', 'employee']

    def __str__(self):
        return f"{self.employee} on {self.project}"


class MobilityProfile(models.Model):
    """Employee's internal mobility preferences and readiness."""
    READINESS_CHOICES = [
        ('not_looking', 'Not Looking'), ('open', 'Open to Opportunities'),
        ('actively_looking', 'Actively Looking'), ('ready_now', 'Ready to Move Now'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='mobility_profiles')
    employee = models.OneToOneField('core_hr.Employee', on_delete=models.CASCADE, related_name='mobility_profile')
    readiness = models.CharField(max_length=20, choices=READINESS_CHOICES, default='not_looking')
    preferred_roles = models.JSONField(default=list)
    preferred_departments = models.JSONField(default=list)
    preferred_locations = models.JSONField(default=list)
    open_to_relocation = models.BooleanField(default=False)
    open_to_international = models.BooleanField(default=False)
    career_aspirations = models.TextField(blank=True)
    target_role = models.ForeignKey('core_hr.Position', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='+')
    target_timeline_months = models.IntegerField(null=True, blank=True)
    is_visible_to_hr = models.BooleanField(default=True)
    is_visible_to_managers = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'internal_marketplace'
        db_table = 'mobility_profiles'

    def __str__(self):
        return f"Mobility: {self.employee} ({self.readiness})"


class SkillMatchSuggestion(models.Model):
    """AI-generated skill-based role/project suggestion for an employee."""
    SUGGESTION_TYPES = [('posting', 'Internal Posting'), ('gig', 'Gig Project'), ('learning', 'Learning Path')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='skill_match_suggestions')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='skill_suggestions')
    suggestion_type = models.CharField(max_length=20, choices=SUGGESTION_TYPES)
    object_id = models.UUIDField(help_text='FK to the suggested posting/gig/course UUID')
    match_score = models.DecimalField(max_digits=5, decimal_places=2)
    matching_skills = models.JSONField(default=list)
    gap_skills = models.JSONField(default=list)
    is_dismissed = models.BooleanField(default=False)
    is_acted_upon = models.BooleanField(default=False)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'internal_marketplace'
        db_table = 'skill_match_suggestions'
        ordering = ['-match_score']

    def __str__(self):
        return f"Suggestion ({self.suggestion_type}) {self.match_score}% for {self.employee}"
