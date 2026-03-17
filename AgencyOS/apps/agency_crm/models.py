"""
Agency CRM & Sales Pipeline models.
Covers: prospect/client accounts, contacts, opportunities, deal types,
activity logs, rate cards, MSA tracking, account health, and forecasting.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class ProspectCompany(models.Model):
    """A company that is a prospect (not yet a signed client)."""

    class Stage(models.TextChoices):
        IDENTIFIED = "identified", "Identified"
        CONTACTED = "contacted", "Contacted"
        MEETING_BOOKED = "meeting_booked", "Meeting Booked"
        PROPOSAL_SENT = "proposal_sent", "Proposal Sent"
        NEGOTIATING = "negotiating", "Negotiating"
        CLOSED_WON = "closed_won", "Closed Won"
        CLOSED_LOST = "closed_lost", "Closed Lost"
        ON_HOLD = "on_hold", "On Hold"

    class Tier(models.TextChoices):
        STRATEGIC = "strategic", "Strategic"
        KEY = "key", "Key"
        STANDARD = "standard", "Standard"
        SMALL = "small", "Small"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="prospects"
    )
    company_name = models.CharField(max_length=255)
    industry = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    company_size = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    stage = models.CharField(max_length=30, choices=Stage.choices, default=Stage.IDENTIFIED)
    tier = models.CharField(max_length=20, choices=Tier.choices, default=Tier.STANDARD)
    assigned_to = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="prospect_accounts"
    )
    # Deal metadata
    estimated_annual_revenue = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    estimated_headcount_needs = models.IntegerField(null=True, blank=True)
    deal_type = models.CharField(
        max_length=30,
        choices=[
            ("contingency", "Contingency"),
            ("retained", "Retained"),
            ("exclusive", "Exclusive"),
            ("rpo", "RPO"),
            ("msp", "MSP"),
        ],
        blank=True,
    )
    lost_reason = models.TextField(blank=True)
    lost_to_competitor = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    next_follow_up = models.DateField(null=True, blank=True)
    source = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "crm_prospect_company"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.company_name} ({self.get_stage_display()})"


class ClientAccount(models.Model):
    """
    A signed client account. Maps to AgencyClient in agencies app but with
    richer CRM data including health, tiering, rate cards, and contract tracking.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        AT_RISK = "at_risk", "At Risk"
        PAUSED = "paused", "Paused"
        CHURNED = "churned", "Churned"

    class Tier(models.TextChoices):
        PLATINUM = "platinum", "Platinum"
        GOLD = "gold", "Gold"
        SILVER = "silver", "Silver"
        BRONZE = "bronze", "Bronze"

    class DealType(models.TextChoices):
        CONTINGENCY = "contingency", "Contingency"
        RETAINED = "retained", "Retained"
        EXCLUSIVE = "exclusive", "Exclusive"
        RPO = "rpo", "RPO"
        MSP = "msp", "MSP / VMS"
        STAFF_AUG = "staff_aug", "Staff Augmentation"
        PROJECT = "project", "Project-Based"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="crm_clients"
    )
    # Link back to AgencyClient (optional tight coupling)
    agency_client = models.OneToOneField(
        "agencies.AgencyClient",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="crm_account",
    )
    company_name = models.CharField(max_length=255)
    industry = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    tier = models.CharField(max_length=20, choices=Tier.choices, default=Tier.SILVER)
    deal_type = models.CharField(max_length=20, choices=DealType.choices, default=DealType.CONTINGENCY)
    # Account team
    account_manager = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="managed_accounts"
    )
    delivery_manager = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="delivery_accounts"
    )
    # Contract details
    msa_start_date = models.DateField(null=True, blank=True)
    msa_expiry_date = models.DateField(null=True, blank=True)
    msa_document_url = models.URLField(blank=True)
    rebate_policy = models.TextField(blank=True)
    replacement_policy_days = models.IntegerField(default=90)
    notice_period_days = models.IntegerField(default=30)
    # Commercial
    is_preferred = models.BooleanField(default=False)
    exclusivity = models.BooleanField(default=False)
    annual_revenue_target = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    # Health & satisfaction
    health_score = models.IntegerField(default=70)  # 0-100
    last_satisfaction_score = models.IntegerField(null=True, blank=True)  # NPS
    last_satisfaction_date = models.DateField(null=True, blank=True)
    # Parent/child account structure
    parent_account = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="child_accounts"
    )
    branch_region = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    prospect = models.OneToOneField(
        ProspectCompany,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="converted_account",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "crm_client_account"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.company_name} [{self.get_tier_display()}]"


class ClientContact(models.Model):
    """Individual contact person at a client or prospect."""

    class ContactType(models.TextChoices):
        HIRING_MANAGER = "hiring_manager", "Hiring Manager"
        HR_DIRECTOR = "hr_director", "HR Director"
        PROCUREMENT = "procurement", "Procurement"
        FINANCE = "finance", "Finance / AP"
        SPONSOR = "sponsor", "Executive Sponsor"
        CHAMPION = "champion", "Internal Champion"
        GATEKEEPER = "gatekeeper", "Gatekeeper"
        TECHNICAL = "technical", "Technical Evaluator"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="crm_contacts"
    )
    client_account = models.ForeignKey(
        ClientAccount, null=True, blank=True, on_delete=models.CASCADE, related_name="contacts"
    )
    prospect_company = models.ForeignKey(
        ProspectCompany, null=True, blank=True, on_delete=models.CASCADE, related_name="contacts"
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    job_title = models.CharField(max_length=150, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)
    mobile = models.CharField(max_length=50, blank=True)
    linkedin_url = models.URLField(blank=True)
    contact_type = models.CharField(
        max_length=30, choices=ContactType.choices, default=ContactType.HIRING_MANAGER
    )
    is_primary = models.BooleanField(default=False)
    is_decision_maker = models.BooleanField(default=False)
    preferred_contact_method = models.CharField(
        max_length=20,
        choices=[("email", "Email"), ("phone", "Phone"), ("linkedin", "LinkedIn")],
        default="email",
    )
    do_not_contact = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    last_contacted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "crm_client_contact"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name} – {self.job_title}"


class Opportunity(models.Model):
    """Sales opportunity in the pipeline."""

    class Stage(models.TextChoices):
        PROSPECTING = "prospecting", "Prospecting"
        QUALIFICATION = "qualification", "Qualification"
        PROPOSAL = "proposal", "Proposal"
        NEGOTIATION = "negotiation", "Negotiation"
        CLOSED_WON = "closed_won", "Closed Won"
        CLOSED_LOST = "closed_lost", "Closed Lost"

    class DealType(models.TextChoices):
        PERM = "perm", "Permanent Placement"
        CONTRACT = "contract", "Contract / Temp"
        RPO = "rpo", "RPO Engagement"
        MSP = "msp", "MSP Program"
        RETAINED = "retained", "Retained Search"
        EXEC = "exec", "Executive Search"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="opportunities"
    )
    prospect = models.ForeignKey(
        ProspectCompany, null=True, blank=True, on_delete=models.SET_NULL, related_name="opportunities"
    )
    client_account = models.ForeignKey(
        ClientAccount, null=True, blank=True, on_delete=models.SET_NULL, related_name="opportunities"
    )
    title = models.CharField(max_length=255)
    stage = models.CharField(max_length=30, choices=Stage.choices, default=Stage.PROSPECTING)
    deal_type = models.CharField(max_length=20, choices=DealType.choices, default=DealType.PERM)
    owner = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="owned_opportunities"
    )
    # Commercial
    estimated_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    probability_percent = models.IntegerField(default=50)
    weighted_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    expected_close_date = models.DateField(null=True, blank=True)
    actual_close_date = models.DateField(null=True, blank=True)
    number_of_roles = models.IntegerField(default=1)
    # Context
    notes = models.TextField(blank=True)
    lost_reason = models.TextField(blank=True)
    lost_to_competitor = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "crm_opportunity"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.estimated_value and self.probability_percent:
            self.weighted_value = self.estimated_value * self.probability_percent / 100
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.get_stage_display()})"


class ActivityLog(models.Model):
    """Sales activity log: calls, emails, meetings, notes."""

    class ActivityType(models.TextChoices):
        CALL = "call", "Call"
        EMAIL = "email", "Email"
        MEETING = "meeting", "Meeting"
        LINKEDIN = "linkedin", "LinkedIn Message"
        NOTE = "note", "Note"
        TASK = "task", "Task"
        PROPOSAL = "proposal", "Proposal Sent"
        CONTRACT = "contract", "Contract Sent"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="activity_logs"
    )
    activity_type = models.CharField(max_length=20, choices=ActivityType.choices)
    # Polymorphic association
    client_account = models.ForeignKey(
        ClientAccount, null=True, blank=True, on_delete=models.CASCADE, related_name="activities"
    )
    prospect = models.ForeignKey(
        ProspectCompany, null=True, blank=True, on_delete=models.CASCADE, related_name="activities"
    )
    opportunity = models.ForeignKey(
        Opportunity, null=True, blank=True, on_delete=models.CASCADE, related_name="activities"
    )
    contact = models.ForeignKey(
        ClientContact, null=True, blank=True, on_delete=models.SET_NULL, related_name="activities"
    )
    performed_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="crm_activities"
    )
    subject = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    outcome = models.CharField(max_length=200, blank=True)
    next_action = models.CharField(max_length=200, blank=True)
    next_action_date = models.DateField(null=True, blank=True)
    duration_minutes = models.IntegerField(null=True, blank=True)
    activity_date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "crm_activity_log"
        ordering = ["-activity_date"]

    def __str__(self):
        return f"{self.get_activity_type_display()} – {self.subject}"


class RateCard(models.Model):
    """Rate card for a client account (bill rates by role/level)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="rate_cards"
    )
    client_account = models.ForeignKey(
        ClientAccount, on_delete=models.CASCADE, related_name="rate_cards"
    )
    role_title = models.CharField(max_length=200)
    level = models.CharField(max_length=100, blank=True)  # Junior/Mid/Senior/Lead
    currency = models.CharField(max_length=10, default="USD")
    # Perm fees
    perm_fee_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # Contract / temp rates
    bill_rate_hourly = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    pay_rate_hourly = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    markup_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # Validity
    effective_from = models.DateField(null=True, blank=True)
    effective_until = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "crm_rate_card"
        ordering = ["role_title", "level"]

    def __str__(self):
        return f"{self.client_account.company_name} – {self.role_title} ({self.level})"


class AccountPlan(models.Model):
    """Annual / quarterly account plan for a client."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="account_plans"
    )
    client_account = models.ForeignKey(
        ClientAccount, on_delete=models.CASCADE, related_name="account_plans"
    )
    period_label = models.CharField(max_length=50)  # e.g., "2026 Q1"
    revenue_target = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    placement_target = models.IntegerField(null=True, blank=True)
    contractor_target = models.IntegerField(null=True, blank=True)
    key_objectives = models.TextField(blank=True)
    cross_sell_opportunities = models.TextField(blank=True)
    risks = models.TextField(blank=True)
    owner = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="account_plans"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "crm_account_plan"

    def __str__(self):
        return f"{self.client_account.company_name} – {self.period_label}"
