"""
CampusOS Business Model — Institution license + student-facing premium + employer events.

Revenue streams covered:
    Layer 1 — Recurring software revenue:
        - CampusPlan: annual institution license (by student count / departments)
        - CampusSubscription: campus / institution subscription record

    Layer 2 — Transactional / event revenue:
        - EmployerCampusCampaign: employer branding campaigns on campus portal
        - PlacementDriveFee: per-drive / per-event placement drive fees
        - HiringEventPackage: campus hiring fair / event sponsorship packages
        - StudentPremiumUpgrade: individual student premium upsell (per student)

    Layer 3 — Commerce & services revenue:
        - EmployabilityProgram: institution-purchased readiness / employability programs
        - CampusServiceProduct: placement consulting, outcomes reporting, accreditation packs
        - CampusServiceOrder: service fulfillment tracker
        - SponsoredPlacementDrive: employer-sponsored drive packages

Pricing model:
    Annual campus license:
        - Priced by student count tier or active departments
        - Add paid readiness programs and employer campaigns on top
    Student-facing:
        - Individual premium upgrade (optional, priced for students)
        - Certification prep, workshops, mentor access
"""

import uuid
from django.db import models


# ---------------------------------------------------------------------------
# Campus Plan Definition (institution license)
# ---------------------------------------------------------------------------

class CampusPlan(models.Model):
    """
    CampusOS annual institution license plan.
    Priced by student enrollment tier or active departments.
    """

    class Tier(models.TextChoices):
        SMALL = "small", "Small Institution (up to 500 students)"
        MEDIUM = "medium", "Medium Institution (501–2,000 students)"
        LARGE = "large", "Large Institution (2,001–10,000 students)"
        UNIVERSITY = "university", "University / Multi-Campus (10,000+)"

    class PricingBasis(models.TextChoices):
        STUDENT_COUNT = "student_count", "Per Student Count Tier"
        DEPARTMENT_COUNT = "department_count", "Per Active Department"
        PLACEMENT_VOLUME = "placement_volume", "Per Placement Volume (annual)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tier = models.CharField(max_length=20, choices=Tier.choices, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    pricing_basis = models.CharField(
        max_length=20, choices=PricingBasis.choices, default=PricingBasis.STUDENT_COUNT,
    )

    # Annual pricing (campuses buy annually)
    price_annual_lkr = models.DecimalField(
        max_digits=14, decimal_places=2,
        help_text="Annual license fee in LKR.",
    )
    price_per_student_annual_lkr = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Per-student annual rate for above-tier overages.",
    )
    price_per_department_annual_lkr = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Per-department annual rate (if dept-based pricing).",
    )

    # Student enrollment limits for this tier
    max_students = models.IntegerField(
        default=-1, help_text="Max students for this tier. -1 = unlimited.",
    )
    max_departments = models.IntegerField(default=-1)

    # Stripe reference
    stripe_price_annual_id = models.CharField(max_length=100, blank=True, default="")

    # Included modules / features
    module_readiness_engine = models.BooleanField(default=True)
    module_internship_management = models.BooleanField(default=False)
    module_employer_crm = models.BooleanField(default=False)
    module_placement_drive_ops = models.BooleanField(default=False)
    module_alumni_mentor_network = models.BooleanField(default=False)
    module_outcomes_analytics = models.BooleanField(default=False)
    module_accreditation_reports = models.BooleanField(default=False)
    module_branded_student_portals = models.BooleanField(default=False)

    # Student discount codes allocation
    student_careeros_discount_codes = models.IntegerField(
        default=0,
        help_text="Number of CareerOS student discount codes included per year.",
    )

    trial_days = models.IntegerField(default=30)
    features = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "campus_plans"
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.name} — LKR {self.price_annual_lkr}/year"


# ---------------------------------------------------------------------------
# Campus Subscription
# ---------------------------------------------------------------------------

class CampusSubscription(models.Model):
    """Annual license subscription for a campus / institution."""

    class Status(models.TextChoices):
        TRIAL = "trial", "Trial"
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"
        PENDING_RENEWAL = "pending_renewal", "Pending Renewal"

    class Gateway(models.TextChoices):
        INVOICE = "invoice", "Invoice / Bank Transfer"
        STRIPE = "stripe", "Stripe"
        PAYHERE = "payhere", "PayHere"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campus = models.ForeignKey(
        "campus.Campus", on_delete=models.CASCADE, related_name="subscriptions",
    )
    plan = models.ForeignKey(
        CampusPlan, on_delete=models.PROTECT, related_name="subscriptions",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TRIAL)
    gateway = models.CharField(max_length=20, choices=Gateway.choices, default=Gateway.INVOICE)

    # Enrollment at time of purchase (drives tier qualification)
    enrolled_student_count = models.IntegerField(default=0)
    active_department_count = models.IntegerField(default=0)

    license_start = models.DateField()
    license_end = models.DateField()
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    auto_renew = models.BooleanField(default=True)
    renewal_price_lkr = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        help_text="Agreed renewal price. Null = recalculated at renewal.",
    )

    amount_paid_lkr = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    payment_reference = models.CharField(max_length=200, blank=True, default="")
    stripe_customer_id = models.CharField(max_length=100, blank=True, default="")

    po_number = models.CharField(
        max_length=100, blank=True, default="",
        help_text="Institution purchase order number (for invoice billing).",
    )
    cancellation_reason = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "campus_subscriptions"
        ordering = ["-license_start"]

    def __str__(self):
        return f"{self.campus} — {self.plan.name} ({self.status})"


# ---------------------------------------------------------------------------
# Student Premium Upgrade (B2C layer from campus)
# ---------------------------------------------------------------------------

class StudentPremiumPlan(models.Model):
    """
    Optional premium upgrade plan sold directly to individual students.
    Campus institutions may provide subsidized or free access;
    non-subsidized students pay directly.
    """

    class Tier(models.TextChoices):
        CAMPUS_FREE = "campus_free", "Campus Free (institution-subsidized)"
        STUDENT_PRO = "student_pro", "Student Pro"
        PLACEMENT_READY = "placement_ready", "Placement Ready (exam + drive prep)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tier = models.CharField(max_length=20, choices=Tier.choices, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    price_monthly_lkr = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_annual_lkr = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stripe_price_monthly_id = models.CharField(max_length=100, blank=True, default="")
    stripe_price_annual_id = models.CharField(max_length=100, blank=True, default="")
    payhere_plan_id = models.CharField(max_length=100, blank=True, default="")

    # Features
    interview_prep_access = models.BooleanField(default=False)
    certification_prep_access = models.BooleanField(default=False)
    mentor_network_access = models.BooleanField(default=False)
    careeros_discount_pct = models.IntegerField(default=0)

    features = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "campus_student_premium_plans"
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.name} — LKR {self.price_monthly_lkr}/mo"


# ---------------------------------------------------------------------------
# Employer Campus Campaign (transactional revenue — employer-facing)
# ---------------------------------------------------------------------------

class EmployerCampusCampaign(models.Model):
    """
    Employer branding / recruitment campaigns on a campus portal.
    Charged to employers who want to reach students / graduates on CampusOS.
    """

    class CampaignType(models.TextChoices):
        BANNER_BRANDING = "banner_branding", "Campus Portal Banner Branding"
        SPONSORED_DRIVE = "sponsored_drive", "Sponsored Placement Drive"
        CAMPUS_TALK = "campus_talk", "Campus Talk / Webinar"
        SCHOLARSHIP_PROGRAM = "scholarship_program", "Scholarship / Fellowship Program"
        INTERNSHIP_SPOTLIGHT = "internship_spotlight", "Internship Spotlight"
        GRADUATE_PROGRAM = "graduate_program", "Graduate Hiring Program"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending Payment"
        PAID = "paid", "Paid — Awaiting Schedule"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campus = models.ForeignKey(
        "campus.Campus", on_delete=models.CASCADE, related_name="employer_campaigns",
    )
    employer_name = models.CharField(max_length=300)
    employer_reference = models.CharField(
        max_length=200, blank=True, default="",
        help_text="Cross-reference to TalentOS or Job Finder employer ID.",
    )
    campaign_type = models.CharField(max_length=25, choices=CampaignType.choices)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    campaign_title = models.CharField(max_length=300)
    description = models.TextField(blank=True, default="")
    target_student_count = models.IntegerField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    price_lkr = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid_lkr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_reference = models.CharField(max_length=200, blank=True, default="")
    paid_at = models.DateTimeField(null=True, blank=True)
    deliverables = models.JSONField(default=list)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "campus_employer_campaigns"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.employer_name} → {self.campus} — {self.campaign_type}"


# ---------------------------------------------------------------------------
# Placement Drive Fee (per-drive transactional charge)
# ---------------------------------------------------------------------------

class PlacementDriveFeeConfig(models.Model):
    """
    Fee configuration for placement drives hosted via CampusOS.
    Drives can be charged to campuses (ops fee) or employers (sponsorship).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    fee_per_drive_lkr = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Platform fee per placement drive beyond plan-included drives.",
    )
    drives_included_in_plan = models.IntegerField(
        default=2, help_text="Drives included in annual license.",
    )
    employer_participation_fee_lkr = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Optional fee charged to each employer participating in a campus drive.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "campus_placement_drive_fee_configs"

    def __str__(self):
        return f"{self.name} — LKR {self.fee_per_drive_lkr}/drive"


# ---------------------------------------------------------------------------
# Employability Programs (Institution-purchased content programs)
# ---------------------------------------------------------------------------

class EmployabilityProgram(models.Model):
    """
    Structured readiness / employability programs sold to institutions.
    Can also include student-facing certification prep.
    """

    class ProgramType(models.TextChoices):
        CAMPUS_READINESS = "campus_readiness", "Campus Placement Readiness Program"
        INTERNSHIP_PREP = "internship_prep", "Internship Preparation Program"
        RESUME_WORKSHOP = "resume_workshop", "Resume & Interview Workshop Series"
        CERTIFICATION_PREP = "certification_prep", "Certification Preparation Program"
        SOFT_SKILLS = "soft_skills", "Professional Skills & Communication"
        ENTREPRENEURSHIP = "entrepreneurship", "Entrepreneurship & Startup Track"
        INDUSTRY_IMMERSION = "industry_immersion", "Industry Immersion Program"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    program_type = models.CharField(max_length=25, choices=ProgramType.choices)
    description = models.TextField(blank=True, default="")
    duration_weeks = models.IntegerField(null=True, blank=True)
    delivery_mode = models.CharField(
        max_length=20,
        choices=[("online", "Online"), ("in_person", "In-Person"), ("hybrid", "Hybrid")],
        default="online",
    )
    languages = models.JSONField(
        default=list, help_text="Delivery languages, e.g. ['en', 'si', 'ta'].",
    )

    # Pricing (sold to institutions as bulk seat / cohort licenses)
    price_per_student_lkr = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_flat_cohort_lkr = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Flat price for a campus cohort (e.g., one department intake).",
    )
    min_students = models.IntegerField(default=20)
    max_students = models.IntegerField(null=True, blank=True)

    stripe_price_id = models.CharField(max_length=100, blank=True, default="")
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "campus_employability_programs"
        ordering = ["-is_featured", "sort_order"]

    def __str__(self):
        return f"{self.name} — LKR {self.price_flat_cohort_lkr}/cohort"


class EmployabilityProgramEnrollment(models.Model):
    """Tracks an institution's enrollment in an employability program."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending Payment"
        ENROLLED = "enrolled", "Enrolled"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campus = models.ForeignKey(
        "campus.Campus", on_delete=models.CASCADE, related_name="program_enrollments",
    )
    program = models.ForeignKey(
        EmployabilityProgram, on_delete=models.PROTECT, related_name="enrollments",
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    student_count = models.IntegerField()
    amount_paid_lkr = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_reference = models.CharField(max_length=200, blank=True, default="")
    paid_at = models.DateTimeField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "campus_program_enrollments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.campus} — {self.program.name} ({self.status})"


# ---------------------------------------------------------------------------
# Campus Professional Services
# ---------------------------------------------------------------------------

class CampusServiceProduct(models.Model):
    """Professional services sold to campus institutions."""

    class ServiceType(models.TextChoices):
        PLATFORM_ONBOARDING = "platform_onboarding", "Platform Onboarding & Setup"
        PLACEMENT_CONSULTING = "placement_consulting", "Campus Placement Consulting"
        OUTCOMES_REPORTING = "outcomes_reporting", "Accreditation Outcomes Report"
        EMPLOYER_CRM_SETUP = "employer_crm_setup", "Employer CRM Setup"
        DRIVE_EXECUTION = "drive_execution", "Placement Drive Execution Support"
        ALUMNI_NETWORK_SETUP = "alumni_network_setup", "Alumni / Mentor Network Setup"
        CUSTOM_ANALYTICS = "custom_analytics", "Custom Analytics Dashboard"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_type = models.CharField(max_length=30, choices=ServiceType.choices)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    deliverables = models.JSONField(default=list)
    price_lkr = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_quoted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "campus_service_products"
        ordering = ["sort_order"]

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Invoice & Billing Events
# ---------------------------------------------------------------------------

class CampusInvoice(models.Model):
    """Invoice for CampusOS institution charges."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        PAID = "paid", "Paid"
        OVERDUE = "overdue", "Overdue"
        VOID = "void", "Void"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campus = models.ForeignKey(
        "campus.Campus", on_delete=models.CASCADE, related_name="invoices",
    )
    invoice_number = models.CharField(max_length=50, unique=True)
    line_items = models.JSONField(default=list)
    subtotal_lkr = models.DecimalField(max_digits=14, decimal_places=2)
    tax_lkr = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_lkr = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_digits=10, choices=Status.choices, default=Status.DRAFT)
    po_number = models.CharField(max_length=100, blank=True, default="")
    payment_reference = models.CharField(max_length=200, blank=True, default="")
    paid_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "campus_invoices"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invoice {self.invoice_number} — {self.campus} — LKR {self.total_lkr}"


class CampusBillingEvent(models.Model):
    """Immutable audit log of CampusOS billing lifecycle events."""

    class EventType(models.TextChoices):
        TRIAL_STARTED = "trial_started", "Trial Started"
        LICENSE_PURCHASED = "license_purchased", "License Purchased"
        LICENSE_RENEWED = "license_renewed", "License Renewed"
        LICENSE_EXPIRED = "license_expired", "License Expired"
        PAYMENT_RECEIVED = "payment_received", "Payment Received"
        PAYMENT_FAILED = "payment_failed", "Payment Failed"
        PROGRAM_ENROLLED = "program_enrolled", "Program Enrolled"
        EMPLOYER_CAMPAIGN_PAID = "employer_campaign_paid", "Employer Campaign Paid"
        SERVICE_ORDER_PLACED = "service_order_placed", "Service Order Placed"
        STUDENT_PREMIUM_PURCHASED = "student_premium_purchased", "Student Premium Purchased"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campus = models.ForeignKey(
        "campus.Campus", on_delete=models.CASCADE, related_name="billing_events",
    )
    event_type = models.CharField(max_length=40, choices=EventType.choices)
    amount_lkr = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "campus_billing_events"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.campus} — {self.event_type} ({self.created_at:%Y-%m-%d})"
