"""
Interview Operations & Interviewer Enablement — Feature 7
Models:
  1.  InterviewPlanTemplate       — plan template per job role/level
  2.  InterviewPlanStage          — ordered stage in a plan template
  3.  CompetencyQuestionBank      — question bank with competency linkage
  4.  InterviewQuestion           — individual question in bank
  5.  InterviewKit                — compiled kit for an interview stage
  6.  InterviewKitQuestion        — question selected into a kit
  7.  InterviewerTrainingModule   — training / certification modules
  8.  InterviewerCertification    — interviewer's training record
  9.  InterviewPrepBrief          — auto-generated prep brief for an interviewer
 10.  PanelRoleAssignment         — role assignment (lead, note-taker, technical...)
 11.  AvailabilitySlot            — interviewer availability declaration
 12.  ConflictOfInterestDisclosure— COI disclosure per interview
 13.  NoteTakingTemplate          — structured note templates
 14.  InterviewNote               — note taken during interview
 15.  FeedbackLock                — feedback locked until debrief flag
 16.  DebriefWorkspace            — decision workspace for a debrief session
 17.  DebriefVote                 — individual hire/no-hire vote
 18.  CalibrationAudit            — calibration score snapshot per interviewer per job
 19.  ScorecardReminder           — late/missing scorecard reminder log
 20.  InterviewerWorkload         — workload budget tracking
 21.  OnsiteAgenda                — onsite interview agenda
 22.  OnsiteAgendaSlot            — slot in an onsite agenda
 23.  TravelLogistics             — travel/logistics record for onsite
 24.  InterviewerPerformanceRecord— per-interviewer performance metrics snapshot
 25.  NoShowPolicy                — configurable no-show / reschedule policy
 26.  CandidateInterviewReminder  — candidate-facing reminder log
 27.  PanelDiversitySnapshot      — per-interview panel diversity snapshot
"""

import uuid
from django.db import models


# ══════════════════════════════════════════════════════════════════════════════
# 1. INTERVIEW PLAN TEMPLATES
# ══════════════════════════════════════════════════════════════════════════════

class InterviewPlanTemplate(models.Model):
    """Reusable interview plan template keyed by job family / level."""

    LEVEL_CHOICES = [
        ("ic1", "IC1 — Entry"),
        ("ic2", "IC2 — Mid"),
        ("ic3", "IC3 — Senior"),
        ("ic4", "IC4 — Staff"),
        ("ic5", "IC5 — Principal"),
        ("m1", "M1 — Manager"),
        ("m2", "M2 — Senior Manager"),
        ("m3", "M3 — Director"),
        ("m4", "M4 — VP+"),
        ("exec", "Executive"),
        ("any", "Any Level"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="interview_plan_templates")
    name = models.CharField(max_length=255)
    job_family = models.CharField(max_length=150, blank=True, default="", help_text="e.g. Engineering, Sales, Design")
    job_level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default="any")
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    # Target total duration in minutes
    total_duration_minutes = models.IntegerField(default=0)
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_interview_plans"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "interview_plan_templates"
        ordering = ["job_family", "job_level", "name"]
        indexes = [models.Index(fields=["tenant", "job_family", "job_level"])]

    def __str__(self):
        return f"{self.name} ({self.job_family} / {self.job_level})"


class InterviewPlanStage(models.Model):
    """Ordered stage within an interview plan template."""

    STAGE_TYPE_CHOICES = [
        ("phone_screen", "Phone Screen"),
        ("recruiter_screen", "Recruiter Screen"),
        ("hiring_manager_screen", "Hiring Manager Screen"),
        ("technical", "Technical Interview"),
        ("system_design", "System Design"),
        ("coding", "Coding Assessment"),
        ("case_study", "Case Study"),
        ("behavioral", "Behavioral Interview"),
        ("panel", "Panel Interview"),
        ("presentation", "Presentation"),
        ("culture_fit", "Culture / Values"),
        ("executive", "Executive Interview"),
        ("reference_check", "Reference Check"),
        ("take_home", "Take-Home Exercise"),
        ("onsite", "Onsite Loop"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(InterviewPlanTemplate, on_delete=models.CASCADE, related_name="stages")
    stage_type = models.CharField(max_length=30, choices=STAGE_TYPE_CHOICES, default="phone_screen")
    name = models.CharField(max_length=150)
    order = models.PositiveIntegerField(default=0)
    duration_minutes = models.IntegerField(default=45)
    # How many interviewers needed
    min_interviewers = models.IntegerField(default=1)
    max_interviewers = models.IntegerField(default=3)
    required_competencies = models.JSONField(
        default=list, blank=True,
        help_text='["problem_solving", "communication", "technical_depth"]'
    )
    notes_template_id = models.UUIDField(null=True, blank=True, help_text="FK to NoteTakingTemplate")
    instructions = models.TextField(blank=True, default="")
    scorecard_required = models.BooleanField(default=True)
    feedback_deadline_hours = models.IntegerField(
        default=24, help_text="Hours after interview end to submit feedback"
    )

    class Meta:
        db_table = "interview_plan_stages"
        ordering = ["plan", "order"]
        unique_together = [("plan", "order")]

    def __str__(self):
        return f"{self.plan.name} — Stage {self.order}: {self.name}"


# ══════════════════════════════════════════════════════════════════════════════
# 2. COMPETENCY QUESTION BANK
# ══════════════════════════════════════════════════════════════════════════════

class CompetencyQuestionBank(models.Model):
    """Named bank of interview questions, scoped to a competency / job family."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="question_banks")
    name = models.CharField(max_length=255)
    competency = models.CharField(max_length=150, help_text="e.g. Problem Solving, Leadership, Communication")
    job_family = models.CharField(max_length=150, blank=True, default="")
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_question_banks"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "competency_question_banks"
        ordering = ["competency", "name"]
        indexes = [models.Index(fields=["tenant", "competency"])]

    def __str__(self):
        return f"{self.name} ({self.competency})"


class InterviewQuestion(models.Model):
    """An individual question in a competency question bank."""

    DIFFICULTY_CHOICES = [
        ("easy", "Easy"),
        ("medium", "Medium"),
        ("hard", "Hard"),
        ("expert", "Expert"),
    ]

    QUESTION_TYPE_CHOICES = [
        ("behavioral", "Behavioral (STAR)"),
        ("situational", "Situational"),
        ("technical", "Technical"),
        ("hypothetical", "Hypothetical"),
        ("case", "Case / Problem Solving"),
        ("culture", "Culture / Values"),
        ("motivation", "Motivation / Career"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank = models.ForeignKey(CompetencyQuestionBank, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField(help_text="The question text")
    follow_ups = models.JSONField(default=list, blank=True, help_text='["Tell me more…", "Give a specific example…"]')
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES, default="behavioral")
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default="medium")
    # What a good answer looks like
    scoring_rubric = models.TextField(blank=True, default="")
    ideal_answer_notes = models.TextField(blank=True, default="")
    # Tags for quick search
    tags = models.JSONField(default=list, blank=True)
    usage_count = models.IntegerField(default=0, help_text="How many kits this question is used in")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_interview_questions"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "interview_questions"
        ordering = ["bank", "difficulty", "question_type"]
        indexes = [models.Index(fields=["bank", "difficulty"])]

    def __str__(self):
        return f"Q [{self.question_type}/{self.difficulty}]: {self.text[:80]}"


# ══════════════════════════════════════════════════════════════════════════════
# 3. INTERVIEW KIT
# ══════════════════════════════════════════════════════════════════════════════

class InterviewKit(models.Model):
    """
    Compiled interview kit for a specific interview stage.
    Can be linked to a plan stage or created ad-hoc.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="interview_kits")
    name = models.CharField(max_length=255)
    plan_stage = models.ForeignKey(
        InterviewPlanStage, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="kits"
    )
    # Optional direct link to a job/application when kit is instantiated
    job = models.ForeignKey(
        "jobs.Job", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="interview_kits"
    )
    interview = models.ForeignKey(
        "applications.Interview", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="kits"
    )
    competencies_covered = models.JSONField(default=list, blank=True)
    interviewer_instructions = models.TextField(blank=True, default="")
    candidate_instructions = models.TextField(blank=True, default="")
    time_allocation = models.JSONField(
        default=dict, blank=True,
        help_text='{"intro": 5, "questions": 35, "candidate_questions": 5}'
    )
    is_published = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_kits"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "interview_kits"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["tenant", "job"])]

    def __str__(self):
        return f"Kit: {self.name}"


class InterviewKitQuestion(models.Model):
    """A question selected into a kit, with per-instance scoring weight."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kit = models.ForeignKey(InterviewKit, on_delete=models.CASCADE, related_name="kit_questions")
    question = models.ForeignKey(
        InterviewQuestion, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="kit_usages"
    )
    # Support ad-hoc questions not in bank
    custom_question_text = models.TextField(blank=True, default="")
    order = models.PositiveIntegerField(default=0)
    weight = models.FloatField(default=1.0, help_text="Scoring weight for this question")
    required = models.BooleanField(default=True)
    time_minutes = models.IntegerField(default=5)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "interview_kit_questions"
        ordering = ["kit", "order"]

    def __str__(self):
        return f"KitQ {self.order} in {self.kit_id}"


# ══════════════════════════════════════════════════════════════════════════════
# 4. INTERVIEWER TRAINING & CERTIFICATION
# ══════════════════════════════════════════════════════════════════════════════

class InterviewerTrainingModule(models.Model):
    """A training or certification module for interviewers."""

    MODULE_TYPE_CHOICES = [
        ("bias_awareness", "Bias Awareness"),
        ("legal_compliance", "Legal / Compliance"),
        ("structured_interviewing", "Structured Interviewing"),
        ("technical_calibration", "Technical Calibration"),
        ("feedback_writing", "Feedback Writing"),
        ("dei_practices", "DEI Practices"),
        ("scorecard_usage", "Scorecard Usage"),
        ("onboarding", "Interviewer Onboarding"),
        ("refresher", "Refresher"),
        ("custom", "Custom"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="training_modules")
    name = models.CharField(max_length=255)
    module_type = models.CharField(max_length=30, choices=MODULE_TYPE_CHOICES, default="structured_interviewing")
    description = models.TextField(blank=True, default="")
    content_url = models.URLField(blank=True, default="")
    duration_minutes = models.IntegerField(default=30)
    # Passing score (0-100) if there's a quiz
    passing_score = models.IntegerField(default=80)
    is_mandatory = models.BooleanField(default=False)
    recertification_months = models.IntegerField(
        default=0, help_text="0 = no expiry; N = expires after N months"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "interviewer_training_modules"
        ordering = ["module_type", "name"]

    def __str__(self):
        return f"{self.name} ({self.module_type})"


class InterviewerCertification(models.Model):
    """Record of an interviewer completing a training module."""

    STATUS_CHOICES = [
        ("enrolled", "Enrolled"),
        ("in_progress", "In Progress"),
        ("passed", "Passed"),
        ("failed", "Failed"),
        ("expired", "Expired"),
        ("waived", "Waived"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="interviewer_certifications")
    interviewer = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="interview_certifications"
    )
    module = models.ForeignKey(InterviewerTrainingModule, on_delete=models.CASCADE, related_name="certifications")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="enrolled")
    score = models.IntegerField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateField(null=True, blank=True)
    certificate_url = models.URLField(blank=True, default="")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "interviewer_certifications"
        unique_together = [("interviewer", "module")]
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["tenant", "interviewer", "status"])]

    def __str__(self):
        return f"Cert: {self.interviewer_id} — {self.module.name} ({self.status})"


# ══════════════════════════════════════════════════════════════════════════════
# 5. INTERVIEWER PREP BRIEF
# ══════════════════════════════════════════════════════════════════════════════

class InterviewPrepBrief(models.Model):
    """
    Auto-generated prep brief sent to an interviewer before an interview.
    Contains candidate summary, role context, questions to ask, and tips.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="prep_briefs")
    interview = models.ForeignKey(
        "applications.Interview", on_delete=models.CASCADE, related_name="prep_briefs"
    )
    interviewer = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="prep_briefs"
    )
    kit = models.ForeignKey(InterviewKit, on_delete=models.SET_NULL, null=True, blank=True, related_name="prep_briefs")
    # Content sections (auto-generated or manually edited)
    candidate_summary = models.TextField(blank=True, default="")
    role_context = models.TextField(blank=True, default="")
    suggested_questions = models.JSONField(default=list, blank=True)
    areas_to_probe = models.JSONField(default=list, blank=True, help_text="Gaps or concerns to investigate")
    dos_and_donts = models.JSONField(
        default=dict, blank=True,
        help_text='{"dos": ["Ask follow-ups"], "donts": ["Ask about family status"]}'
    )
    logistics_notes = models.TextField(blank=True, default="")
    sent_at = models.DateTimeField(null=True, blank=True)
    viewed_at = models.DateTimeField(null=True, blank=True)
    is_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "interview_prep_briefs"
        unique_together = [("interview", "interviewer")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"Prep brief for {self.interviewer_id} — Interview {self.interview_id}"


# ══════════════════════════════════════════════════════════════════════════════
# 6. PANEL ROLE ASSIGNMENT
# ══════════════════════════════════════════════════════════════════════════════

class PanelRoleAssignment(models.Model):
    """
    Assigns a named role to each panel member within an interview.
    Extends the existing InterviewPanel model without modifying it.
    """

    ROLE_CHOICES = [
        ("lead", "Lead Interviewer"),
        ("co_interviewer", "Co-Interviewer"),
        ("note_taker", "Note-Taker"),
        ("technical", "Technical Evaluator"),
        ("behavioral", "Behavioral Evaluator"),
        ("culture", "Culture / Values Evaluator"),
        ("observer", "Observer (Shadowing)"),
        ("hiring_manager", "Hiring Manager"),
        ("recruiter", "Recruiter"),
        ("executive", "Executive Sponsor"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="panel_role_assignments")
    interview = models.ForeignKey(
        "applications.Interview", on_delete=models.CASCADE, related_name="panel_roles"
    )
    interviewer = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="panel_role_assignments"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="co_interviewer")
    competencies_to_assess = models.JSONField(default=list, blank=True)
    is_decision_maker = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "panel_role_assignments"
        unique_together = [("interview", "interviewer")]
        ordering = ["interview", "role"]
        indexes = [models.Index(fields=["tenant", "interview"])]

    def __str__(self):
        return f"{self.interviewer_id} as {self.role} in interview {self.interview_id}"


# ══════════════════════════════════════════════════════════════════════════════
# 7. AVAILABILITY OPTIMIZER
# ══════════════════════════════════════════════════════════════════════════════

class AvailabilitySlot(models.Model):
    """Interviewer declares available time slots for scheduling optimization."""

    SLOT_STATUS_CHOICES = [
        ("available", "Available"),
        ("tentative", "Tentative"),
        ("blocked", "Blocked"),
        ("booked", "Booked"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="availability_slots")
    interviewer = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="availability_slots"
    )
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    status = models.CharField(max_length=20, choices=SLOT_STATUS_CHOICES, default="available")
    # If booked, reference to interview
    booked_interview = models.ForeignKey(
        "applications.Interview", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="booked_slots"
    )
    timezone = models.CharField(max_length=50, default="UTC")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "availability_slots"
        ordering = ["interviewer", "start_datetime"]
        indexes = [
            models.Index(fields=["tenant", "interviewer", "start_datetime"]),
            models.Index(fields=["tenant", "start_datetime", "status"]),
        ]

    def __str__(self):
        return f"Slot: {self.interviewer_id} {self.start_datetime} — {self.status}"


# ══════════════════════════════════════════════════════════════════════════════
# 8. CONFLICT OF INTEREST DISCLOSURE
# ══════════════════════════════════════════════════════════════════════════════

class ConflictOfInterestDisclosure(models.Model):
    """An interviewer discloses (or clears) a conflict of interest for an interview."""

    COI_TYPE_CHOICES = [
        ("personal_relationship", "Personal Relationship"),
        ("family", "Family Member"),
        ("former_colleague", "Former Colleague"),
        ("financial_interest", "Financial Interest"),
        ("competitor", "Competitor Affiliation"),
        ("social_connection", "Social / Online Connection"),
        ("managed_previously", "Previously Managed Candidate"),
        ("other", "Other"),
    ]

    RESOLUTION_CHOICES = [
        ("pending", "Pending Review"),
        ("cleared", "Cleared — No Conflict"),
        ("recused", "Recused from Panel"),
        ("waived", "Waived by Recruiter"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="coi_disclosures")
    interview = models.ForeignKey(
        "applications.Interview", on_delete=models.CASCADE, related_name="coi_disclosures"
    )
    interviewer = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="coi_disclosures"
    )
    has_conflict = models.BooleanField(default=False)
    conflict_type = models.CharField(max_length=30, choices=COI_TYPE_CHOICES, blank=True, default="")
    description = models.TextField(blank=True, default="")
    resolution = models.CharField(max_length=20, choices=RESOLUTION_CHOICES, default="pending")
    resolved_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="resolved_coi_disclosures"
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "coi_disclosures"
        unique_together = [("interview", "interviewer")]
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["tenant", "interview"])]

    def __str__(self):
        return f"COI: {self.interviewer_id} — interview {self.interview_id} ({self.resolution})"


# ══════════════════════════════════════════════════════════════════════════════
# 9. NOTE-TAKING TEMPLATES
# ══════════════════════════════════════════════════════════════════════════════

class NoteTakingTemplate(models.Model):
    """Structured note template for use during interviews."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="note_templates")
    name = models.CharField(max_length=255)
    # JSON schema for sections: [{"section": "Technical", "prompt": "Rate SQL knowledge 1-5", "field_type": "rating"}]
    sections = models.JSONField(default=list, blank=True)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_note_templates"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "note_taking_templates"
        ordering = ["name"]

    def __str__(self):
        return self.name


class InterviewNote(models.Model):
    """Notes taken by an interviewer using a template during an interview."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="interview_notes")
    interview = models.ForeignKey(
        "applications.Interview", on_delete=models.CASCADE, related_name="structured_notes"
    )
    interviewer = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="interview_notes"
    )
    template = models.ForeignKey(
        NoteTakingTemplate, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="interview_notes"
    )
    # Filled-in section data matching template.sections
    filled_sections = models.JSONField(default=dict, blank=True)
    free_text_notes = models.TextField(blank=True, default="")
    is_locked = models.BooleanField(default=False, help_text="Locked after debrief starts")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "interview_notes"
        unique_together = [("interview", "interviewer")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notes by {self.interviewer_id} for interview {self.interview_id}"


# ══════════════════════════════════════════════════════════════════════════════
# 10. FEEDBACK LOCK
# ══════════════════════════════════════════════════════════════════════════════

class FeedbackLock(models.Model):
    """
    Enforces that an interviewer cannot see others' feedback until
    they submit their own or until the debrief begins.
    """

    LOCK_STATUS_CHOICES = [
        ("locked", "Locked — Awaiting Submission"),
        ("unlocked", "Unlocked"),
        ("unlocked_by_admin", "Unlocked by Admin Override"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="feedback_locks")
    interview = models.ForeignKey(
        "applications.Interview", on_delete=models.CASCADE, related_name="feedback_locks"
    )
    interviewer = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="feedback_locks"
    )
    status = models.CharField(max_length=20, choices=LOCK_STATUS_CHOICES, default="locked")
    unlocked_at = models.DateTimeField(null=True, blank=True)
    unlocked_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="unlocked_feedback"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "feedback_locks"
        unique_together = [("interview", "interviewer")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"FeedbackLock: {self.interviewer_id} — {self.status}"


# ══════════════════════════════════════════════════════════════════════════════
# 11. DEBRIEF WORKSPACE
# ══════════════════════════════════════════════════════════════════════════════

class DebriefWorkspace(models.Model):
    """
    Decision workspace for a debrief session.
    Extends the existing DebriefSession with richer decision tooling.
    """

    DECISION_CHOICES = [
        ("strong_hire", "Strong Hire"),
        ("hire", "Hire"),
        ("lean_hire", "Lean Hire"),
        ("lean_no_hire", "Lean No Hire"),
        ("no_hire", "No Hire"),
        ("strong_no_hire", "Strong No Hire"),
        ("hold", "Hold"),
        ("pending", "Pending"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="debrief_workspaces")
    # Can link to existing DebriefSession or standalone
    debrief_session = models.OneToOneField(
        "applications.DebriefSession", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="workspace"
    )
    application = models.ForeignKey(
        "applications.Application", on_delete=models.CASCADE, related_name="debrief_workspaces"
    )
    final_decision = models.CharField(max_length=20, choices=DECISION_CHOICES, default="pending")
    decision_rationale = models.TextField(blank=True, default="")
    decision_made_at = models.DateTimeField(null=True, blank=True)
    decision_made_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="debrief_decisions"
    )
    # Score variance flagged automatically
    score_variance_flagged = models.BooleanField(default=False)
    score_variance_notes = models.TextField(blank=True, default="")
    # Fairness/consistency flag
    fairness_flag = models.BooleanField(default=False)
    fairness_flag_reason = models.TextField(blank=True, default="")
    # Shared notes visible to all participants
    shared_notes = models.TextField(blank=True, default="")
    # Action items post-debrief
    action_items = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "debrief_workspaces"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["tenant", "application"])]

    def __str__(self):
        return f"Workspace: {self.application_id} — {self.final_decision}"


class DebriefVote(models.Model):
    """An individual hire/no-hire vote cast in a debrief workspace."""

    VOTE_CHOICES = [
        ("strong_hire", "Strong Hire"),
        ("hire", "Hire"),
        ("lean_hire", "Lean Hire"),
        ("lean_no_hire", "Lean No Hire"),
        ("no_hire", "No Hire"),
        ("strong_no_hire", "Strong No Hire"),
        ("abstain", "Abstain"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(DebriefWorkspace, on_delete=models.CASCADE, related_name="votes")
    voter = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="debrief_votes")
    vote = models.CharField(max_length=20, choices=VOTE_CHOICES)
    rationale = models.TextField(blank=True, default="")
    top_strength = models.TextField(blank=True, default="")
    top_concern = models.TextField(blank=True, default="")
    # Feedback locked until submitted
    is_submitted = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "debrief_votes"
        unique_together = [("workspace", "voter")]
        ordering = ["workspace", "voter"]

    def __str__(self):
        return f"Vote: {self.voter_id} — {self.vote}"


# ══════════════════════════════════════════════════════════════════════════════
# 12. CALIBRATION AUDIT
# ══════════════════════════════════════════════════════════════════════════════

class CalibrationAudit(models.Model):
    """
    Snapshot of an interviewer's scoring patterns for a given job.
    Used to detect score inflation, deflation, or inconsistency.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="calibration_audits")
    job = models.ForeignKey("jobs.Job", on_delete=models.SET_NULL, null=True, blank=True, related_name="calibration_audits")
    interviewer = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="calibration_audits"
    )
    # Computed metrics over a period
    avg_score_given = models.FloatField(null=True, blank=True)
    median_score_given = models.FloatField(null=True, blank=True)
    team_avg_score = models.FloatField(null=True, blank=True, help_text="Panel average for comparison")
    score_std_dev = models.FloatField(null=True, blank=True)
    # Variance from team average (positive = lenient, negative = harsh)
    variance_from_team = models.FloatField(null=True, blank=True)
    interviews_evaluated = models.IntegerField(default=0)
    # Consistency score (0-1): how consistent this interviewer is across similar candidates
    consistency_score = models.FloatField(null=True, blank=True)
    # Flags
    is_outlier = models.BooleanField(default=False)
    outlier_notes = models.TextField(blank=True, default="")
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "calibration_audits"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["tenant", "interviewer", "job"])]

    def __str__(self):
        return f"CalibAudit: {self.interviewer_id} — avg {self.avg_score_given}"


# ══════════════════════════════════════════════════════════════════════════════
# 13. SCORECARD REMINDERS
# ══════════════════════════════════════════════════════════════════════════════

class ScorecardReminder(models.Model):
    """Log of late / missing scorecard reminder notifications sent."""

    TRIGGER_CHOICES = [
        ("approaching_deadline", "Approaching Deadline"),
        ("past_deadline", "Past Deadline"),
        ("missing_after_interview", "Missing After Interview"),
        ("escalation", "Escalation to Hiring Manager"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="scorecard_reminders")
    interview = models.ForeignKey(
        "applications.Interview", on_delete=models.CASCADE, related_name="scorecard_reminders"
    )
    interviewer = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="scorecard_reminders"
    )
    trigger = models.CharField(max_length=30, choices=TRIGGER_CHOICES)
    sent_at = models.DateTimeField(auto_now_add=True)
    # Number of reminders sent so far for this interview+interviewer
    reminder_count = models.IntegerField(default=1)
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "scorecard_reminders"
        ordering = ["-sent_at"]
        indexes = [models.Index(fields=["tenant", "interview", "interviewer"])]

    def __str__(self):
        return f"Reminder: {self.interviewer_id} — {self.trigger} (x{self.reminder_count})"


# ══════════════════════════════════════════════════════════════════════════════
# 14. INTERVIEWER WORKLOAD
# ══════════════════════════════════════════════════════════════════════════════

class InterviewerWorkload(models.Model):
    """
    Tracks and enforces interviewer workload budgets.
    Prevents overloading high-demand interviewers.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="interviewer_workloads")
    interviewer = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="workload_records"
    )
    # Budget window (e.g., a calendar week)
    week_start = models.DateField()
    # Configured max for this interviewer/period
    max_interviews_per_week = models.IntegerField(default=5)
    max_hours_per_week = models.FloatField(default=5.0)
    # Actual counts (auto-updated)
    scheduled_count = models.IntegerField(default=0)
    completed_count = models.IntegerField(default=0)
    scheduled_hours = models.FloatField(default=0.0)
    # Flag if over budget
    is_overloaded = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "interviewer_workloads"
        unique_together = [("interviewer", "week_start")]
        ordering = ["-week_start"]
        indexes = [models.Index(fields=["tenant", "week_start"])]

    def __str__(self):
        return f"Workload: {self.interviewer_id} w/o {self.week_start} ({self.scheduled_count}/{self.max_interviews_per_week})"


# ══════════════════════════════════════════════════════════════════════════════
# 15. ONSITE AGENDA BUILDER
# ══════════════════════════════════════════════════════════════════════════════

class OnsiteAgenda(models.Model):
    """Onsite interview day agenda for a candidate."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="onsite_agendas")
    interview = models.OneToOneField(
        "applications.Interview", on_delete=models.CASCADE, related_name="onsite_agenda"
    )
    candidate_name = models.CharField(max_length=255, blank=True, default="")
    date = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=500, blank=True, default="")
    # Check-in instructions, parking, etc.
    arrival_instructions = models.TextField(blank=True, default="")
    dress_code = models.CharField(max_length=100, blank=True, default="")
    # Candidate-facing intro note
    welcome_message = models.TextField(blank=True, default="")
    is_published_to_candidate = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "onsite_agendas"
        ordering = ["-date"]

    def __str__(self):
        return f"Agenda: {self.candidate_name} on {self.date}"


class OnsiteAgendaSlot(models.Model):
    """A time slot in an onsite agenda."""

    SLOT_TYPE_CHOICES = [
        ("interview", "Interview"),
        ("break", "Break"),
        ("lunch", "Lunch"),
        ("tour", "Office Tour"),
        ("intro", "Team Introduction"),
        ("presentation", "Presentation"),
        ("travel", "Travel / Transit"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agenda = models.ForeignKey(OnsiteAgenda, on_delete=models.CASCADE, related_name="slots")
    slot_type = models.CharField(max_length=20, choices=SLOT_TYPE_CHOICES, default="interview")
    title = models.CharField(max_length=255)
    start_time = models.TimeField()
    end_time = models.TimeField()
    location = models.CharField(max_length=255, blank=True, default="")
    host = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="agenda_slots_hosted"
    )
    notes = models.TextField(blank=True, default="")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "onsite_agenda_slots"
        ordering = ["agenda", "order", "start_time"]

    def __str__(self):
        return f"{self.start_time}–{self.end_time}: {self.title}"


# ══════════════════════════════════════════════════════════════════════════════
# 16. TRAVEL & LOGISTICS
# ══════════════════════════════════════════════════════════════════════════════

class TravelLogistics(models.Model):
    """Travel and logistics record for an onsite interview."""

    REIMBURSEMENT_STATUS_CHOICES = [
        ("not_applicable", "Not Applicable"),
        ("pending_request", "Pending Request"),
        ("approved", "Approved"),
        ("submitted", "Expenses Submitted"),
        ("reimbursed", "Reimbursed"),
        ("declined", "Declined"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="travel_logistics")
    interview = models.OneToOneField(
        "applications.Interview", on_delete=models.CASCADE, related_name="travel_logistics"
    )
    # Flight / train details
    travel_required = models.BooleanField(default=False)
    origin_city = models.CharField(max_length=150, blank=True, default="")
    destination_city = models.CharField(max_length=150, blank=True, default="")
    travel_date = models.DateField(null=True, blank=True)
    return_date = models.DateField(null=True, blank=True)
    booking_reference = models.CharField(max_length=255, blank=True, default="")
    # Hotel
    hotel_required = models.BooleanField(default=False)
    hotel_name = models.CharField(max_length=255, blank=True, default="")
    hotel_address = models.TextField(blank=True, default="")
    hotel_confirmation = models.CharField(max_length=100, blank=True, default="")
    # Reimbursement
    reimbursement_status = models.CharField(
        max_length=25, choices=REIMBURSEMENT_STATUS_CHOICES, default="not_applicable"
    )
    reimbursement_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    reimbursement_currency = models.CharField(max_length=3, default="USD")
    expense_receipts = models.JSONField(default=list, blank=True, help_text='["https://..."]')
    special_instructions = models.TextField(blank=True, default="")
    travel_contact_name = models.CharField(max_length=200, blank=True, default="")
    travel_contact_email = models.EmailField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "travel_logistics"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Travel: interview {self.interview_id} ({self.origin_city} → {self.destination_city})"


# ══════════════════════════════════════════════════════════════════════════════
# 17. INTERVIEWER PERFORMANCE ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════

class InterviewerPerformanceRecord(models.Model):
    """
    Periodic snapshot of an interviewer's performance metrics.
    Used for score variance, fairness, and consistency analytics.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="interviewer_performance")
    interviewer = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="performance_records"
    )
    period_start = models.DateField()
    period_end = models.DateField()
    # Volume
    total_interviews = models.IntegerField(default=0)
    completed_interviews = models.IntegerField(default=0)
    cancelled_interviews = models.IntegerField(default=0)
    # Timeliness
    avg_feedback_hours = models.FloatField(null=True, blank=True, help_text="Avg hours to submit feedback")
    late_feedback_count = models.IntegerField(default=0)
    missing_feedback_count = models.IntegerField(default=0)
    # Score quality
    avg_score_given = models.FloatField(null=True, blank=True)
    score_variance = models.FloatField(null=True, blank=True)
    # Decision accuracy (vs. eventual hire outcome)
    hire_recommendation_count = models.IntegerField(default=0)
    hire_recommendation_accuracy = models.FloatField(null=True, blank=True, help_text="0-1 accuracy rate")
    # Fairness
    demographic_score_variance_flag = models.BooleanField(default=False)
    fairness_score = models.FloatField(null=True, blank=True, help_text="0-1 consistency score")
    # Candidate experience
    avg_candidate_rating = models.FloatField(null=True, blank=True, help_text="From post-interview survey")
    # Training compliance
    certifications_current = models.BooleanField(default=True)
    overdue_training_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "interviewer_performance_records"
        unique_together = [("interviewer", "period_start", "period_end")]
        ordering = ["-period_end"]
        indexes = [models.Index(fields=["tenant", "period_end"])]

    def __str__(self):
        return f"Perf: {self.interviewer_id} {self.period_start}–{self.period_end}"


# ══════════════════════════════════════════════════════════════════════════════
# 18. NO-SHOW / RESCHEDULE POLICIES
# ══════════════════════════════════════════════════════════════════════════════

class NoShowPolicy(models.Model):
    """
    Tenant-configurable policy for candidate no-shows and reschedule limits.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="no_show_policies")
    name = models.CharField(max_length=255)
    # Max rescheduling attempts before auto-reject
    max_reschedule_attempts = models.IntegerField(default=2)
    # Grace period minutes before marking no-show
    no_show_grace_period_minutes = models.IntegerField(default=10)
    # What happens after no-show: auto_reject, hold, notify_recruiter
    no_show_action = models.CharField(
        max_length=30, default="notify_recruiter",
        choices=[
            ("auto_reject", "Auto-Reject"),
            ("hold", "Place on Hold"),
            ("notify_recruiter", "Notify Recruiter"),
        ]
    )
    # Auto-send reminder N hours before interview
    reminder_hours_before = models.JSONField(
        default=list, blank=True,
        help_text='[48, 24, 2] — hours before interview to send reminders'
    )
    # Whether to require candidate confirmation
    require_candidate_confirmation = models.BooleanField(default=True)
    # Reschedule window: candidate can reschedule up to N hours before
    reschedule_deadline_hours = models.IntegerField(default=24)
    is_default = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "no_show_policies"
        ordering = ["name"]

    def __str__(self):
        return f"Policy: {self.name}"


# ══════════════════════════════════════════════════════════════════════════════
# 19. CANDIDATE-FACING REMINDERS
# ══════════════════════════════════════════════════════════════════════════════

class CandidateInterviewReminder(models.Model):
    """Log of reminders and instructions sent to candidates."""

    REMINDER_TYPE_CHOICES = [
        ("confirmation", "Interview Confirmation"),
        ("reminder_48h", "48-Hour Reminder"),
        ("reminder_24h", "24-Hour Reminder"),
        ("reminder_2h", "2-Hour Reminder"),
        ("onsite_instructions", "Onsite Instructions"),
        ("video_link", "Video Link / Join Instructions"),
        ("agenda", "Agenda Sent"),
        ("reschedule_offer", "Reschedule Offer"),
        ("cancellation", "Cancellation Notice"),
        ("no_show_followup", "No-Show Follow-Up"),
    ]

    CHANNEL_CHOICES = [
        ("email", "Email"),
        ("sms", "SMS"),
        ("portal", "Candidate Portal"),
        ("whatsapp", "WhatsApp"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="candidate_reminders")
    interview = models.ForeignKey(
        "applications.Interview", on_delete=models.CASCADE, related_name="candidate_reminders"
    )
    candidate = models.ForeignKey(
        "candidates.Candidate", on_delete=models.CASCADE, related_name="interview_reminders"
    )
    reminder_type = models.CharField(max_length=30, choices=REMINDER_TYPE_CHOICES)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default="email")
    subject = models.CharField(max_length=255, blank=True, default="")
    body = models.TextField(blank=True, default="")
    sent_at = models.DateTimeField(auto_now_add=True)
    delivered = models.BooleanField(default=False)
    opened_at = models.DateTimeField(null=True, blank=True)
    # Candidate response (confirmed, reschedule_requested, declined)
    candidate_response = models.CharField(max_length=30, blank=True, default="")
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "candidate_interview_reminders"
        ordering = ["-sent_at"]
        indexes = [
            models.Index(fields=["tenant", "interview"]),
            models.Index(fields=["tenant", "candidate"]),
        ]

    def __str__(self):
        return f"Reminder: {self.reminder_type} to candidate {self.candidate_id}"


# ══════════════════════════════════════════════════════════════════════════════
# 20. PANEL DIVERSITY SNAPSHOT
# ══════════════════════════════════════════════════════════════════════════════

class PanelDiversitySnapshot(models.Model):
    """
    Optional diversity snapshot of an interview panel.
    Only collected when customer policy requires it.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="panel_diversity_snapshots")
    interview = models.OneToOneField(
        "applications.Interview", on_delete=models.CASCADE, related_name="panel_diversity_snapshot"
    )
    panel_size = models.IntegerField(default=0)
    # Voluntary, aggregated — never stored per-individual
    gender_diversity_met = models.BooleanField(
        null=True, blank=True,
        help_text="True if panel meets tenant's configured gender diversity target"
    )
    ethnic_diversity_met = models.BooleanField(
        null=True, blank=True,
        help_text="True if panel meets tenant's configured ethnic diversity target"
    )
    # Overall policy met flag
    diversity_policy_met = models.BooleanField(null=True, blank=True)
    diversity_policy_name = models.CharField(max_length=150, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    # Who ran the check
    checked_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="panel_diversity_checks"
    )
    checked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "panel_diversity_snapshots"
        ordering = ["-checked_at"]

    def __str__(self):
        return f"DiversitySnap: interview {self.interview_id} (met={self.diversity_policy_met})"
