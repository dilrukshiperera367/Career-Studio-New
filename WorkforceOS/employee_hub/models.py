"""
Employee Hub — Employee Self-Service 2.0

Covers all 16 feature areas:
  1.  Home dashboard (widgets, feed, quick links)                 — EmployeeHubWidget, EmployeeFeedItem, EmployeeQuickLink
  2.  Personal profile updates                                     — EmployeeProfileCompletion, ProfileChangeRequest
  3.  Bank / tax / emergency contact / dependent self-service      — BankDetail, TaxDeclaration, EmergencyContact, Dependent
  4.  Payslips / tax letters / salary history                      — PayslipAccess, TaxLetterRequest, SalaryHistoryView
  5.  Leave / attendance / shift self-service                      — (proxies to leave_attendance; ShiftSwapRequest here)
  6.  Overtime view and approval status                            — OvertimeRequest
  7.  Benefits enrollment and life-event changes                   — BenefitsEnrollment, LifeEventChange
  8.  Document vault                                               — EmployeeDocumentVault
  9.  Policy acknowledgement center                               — PolicyAcknowledgement (extends documents_policies)
  10. Training and certification center                            — TrainingEnrollment, CertificationRecord
  11. Goals / reviews / feedback view                              — (read-only proxy via performance; GoalComment here)
  12. Internal jobs and gigs tab                                   — InternalJobApplication
  13. Helpdesk and case status                                     — EmployeeCase
  14. Asset requests and returns                                   — AssetRequest
  15. Multilingual self-service                                     — EmployeeLanguagePreference
  16. Mobile-first / WCAG 2.2 metadata                             — AccessibilityPreference, ServiceRequest (renamed from SelfServiceRequest)

WCAG 2.2 baseline: all user-facing content driven by these models must support:
  - keyboard navigation, sufficient colour contrast (4.5:1 normal / 3:1 large),
  - focus-visible indicators, touch targets ≥ 24×24 px, draggable alternatives.
  API responses include wcag_level='AA' metadata field on paginated list endpoints
  (injected in views, not stored in DB).
"""

import uuid
from django.db import models
from django.conf import settings


# ---------------------------------------------------------------------------
# 1. Home dashboard
# ---------------------------------------------------------------------------

class EmployeeProfileCompletion(models.Model):
    """Tracks how complete an employee's self-service profile is."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='profile_completions')
    employee = models.OneToOneField('core_hr.Employee', on_delete=models.CASCADE, related_name='profile_completion')
    overall_pct = models.IntegerField(default=0)
    section_scores = models.JSONField(default=dict,
        help_text='{"personal":100,"contact":80,"emergency":0,"bank":50,"documents":60}')
    missing_fields = models.JSONField(default=list)
    last_computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'employee_hub'
        db_table = 'employee_profile_completions'

    def __str__(self):
        return f"Profile {self.overall_pct}% — {self.employee}"

    def recompute(self):
        """Recompute section scores and overall pct based on filled fields."""
        emp = self.employee
        sections = {
            'personal': self._score_personal(emp),
            'contact': self._score_contact(emp),
            'emergency': 100 if emp.emergency_contacts.exists() else 0,
            'bank': 100 if emp.bank_details.exists() else 0,
            'documents': min(100, emp.document_vault_entries.count() * 20),
        }
        self.section_scores = sections
        self.overall_pct = int(sum(sections.values()) / len(sections))
        missing = []
        if sections['emergency'] == 0:
            missing.append('emergency_contact')
        if sections['bank'] == 0:
            missing.append('bank_details')
        self.missing_fields = missing
        self.save(update_fields=['section_scores', 'overall_pct', 'missing_fields', 'last_computed_at'])

    def _score_personal(self, emp):
        fields = ['first_name', 'last_name', 'date_of_birth', 'gender', 'nationality']
        filled = sum(1 for f in fields if getattr(emp, f, None))
        return int(filled / len(fields) * 100)

    def _score_contact(self, emp):
        fields = ['work_email', 'personal_email', 'phone_number', 'address']
        filled = sum(1 for f in fields if getattr(emp, f, None))
        return int(filled / len(fields) * 100)


class EmployeeQuickLink(models.Model):
    """Tenant-configured quick links shown on the employee self-service portal."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='employee_quick_links')
    title = models.CharField(max_length=200)
    url = models.CharField(max_length=500)
    icon = models.CharField(max_length=10, default='link')
    category = models.CharField(max_length=50, blank=True)
    audience = models.JSONField(default=list, help_text='Department/grade filters; empty = all')
    is_active = models.BooleanField(default=True)
    opens_in_new_tab = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    click_count = models.IntegerField(default=0)

    class Meta:
        app_label = 'employee_hub'
        db_table = 'employee_quick_links'
        ordering = ['sort_order', 'title']

    def __str__(self):
        return self.title


class EmployeeHubWidget(models.Model):
    """Widget configuration for an employee's self-service portal home dashboard."""
    WIDGET_TYPES = [
        ('leave_balance', 'Leave Balance'),
        ('attendance_summary', 'Attendance Summary'),
        ('payslips', 'Recent Payslips'),
        ('goals', 'My Goals'),
        ('tasks', 'My Tasks'),
        ('announcements', 'Announcements'),
        ('quick_links', 'Quick Links'),
        ('recognition', 'Recognition Feed'),
        ('upcoming_events', 'Upcoming Events'),
        ('org_chart', 'Team Org Chart'),
        ('learning', 'Learning Progress'),
        ('benefits', 'My Benefits'),
        ('overtime', 'Overtime Summary'),
        ('asset_requests', 'Asset Requests'),
        ('cases', 'Open Cases'),
        ('policy_ack', 'Policy Acknowledgements'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='hub_widgets')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='hub_widgets')
    widget_type = models.CharField(max_length=30, choices=WIDGET_TYPES)
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)
    width = models.IntegerField(default=4, help_text='Grid column span (1-12)')
    height = models.IntegerField(default=2, help_text='Grid row span')
    is_visible = models.BooleanField(default=True)
    config = models.JSONField(default=dict)

    class Meta:
        app_label = 'employee_hub'
        db_table = 'employee_hub_widgets'
        ordering = ['position_y', 'position_x']

    def __str__(self):
        return f"{self.widget_type} widget for {self.employee}"


class EmployeeFeedItem(models.Model):
    """Personalised feed item on employee portal (announcements, recognitions, events)."""
    ITEM_TYPES = [
        ('announcement', 'Announcement'),
        ('recognition', 'Recognition'),
        ('birthday', 'Birthday'),
        ('anniversary', 'Work Anniversary'),
        ('new_joiner', 'New Joiner'),
        ('achievement', 'Achievement'),
        ('poll', 'Poll'),
        ('event', 'Event'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='feed_items')
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES)
    title = models.CharField(max_length=300)
    body = models.TextField(blank=True)
    image_url = models.CharField(max_length=500, blank=True)
    action_url = models.CharField(max_length=500, blank=True)
    author = models.ForeignKey('core_hr.Employee', on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='authored_feed_items')
    target_employee = models.ForeignKey('core_hr.Employee', on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name='feed_items_about_me')
    audience_filter = models.JSONField(default=dict, help_text='{"departments":[],"grades":[],"all":true}')
    likes_count = models.IntegerField(default=0)
    comments_count = models.IntegerField(default=0)
    is_pinned = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'employee_hub'
        db_table = 'employee_feed_items'
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return f"{self.item_type}: {self.title}"


# ---------------------------------------------------------------------------
# 2. Personal profile updates
# ---------------------------------------------------------------------------

class ProfileChangeRequest(models.Model):
    """Employee-initiated request to change personal profile data requiring HR approval."""
    CHANGE_TYPES = [
        ('name', 'Name Change'),
        ('address', 'Address Change'),
        ('contact', 'Contact Number Change'),
        ('personal_email', 'Personal Email Change'),
        ('date_of_birth', 'Date of Birth Correction'),
        ('gender', 'Gender Update'),
        ('nationality', 'Nationality Change'),
        ('marital_status', 'Marital Status Update'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='profile_change_requests')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='profile_change_requests')
    change_type = models.CharField(max_length=30, choices=CHANGE_TYPES)
    field_name = models.CharField(max_length=100, help_text='Model field being changed')
    old_value = models.TextField(blank=True)
    new_value = models.TextField()
    supporting_documents = models.JSONField(default=list, help_text='List of uploaded document URLs')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='+')
    review_notes = models.TextField(blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'employee_hub'
        db_table = 'profile_change_requests'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.change_type} for {self.employee} ({self.status})"


# ---------------------------------------------------------------------------
# 3. Bank / tax / emergency contact / dependent self-service
# ---------------------------------------------------------------------------

class BankDetail(models.Model):
    """Employee bank account details for salary payment."""
    ACCOUNT_TYPES = [
        ('savings', 'Savings'),
        ('current', 'Current'),
        ('salary', 'Salary Account'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='employee_bank_details')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='employee_bank_details')
    bank_name = models.CharField(max_length=200)
    branch_name = models.CharField(max_length=200, blank=True)
    branch_code = models.CharField(max_length=20, blank=True)
    account_number = models.CharField(max_length=50)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default='savings')
    ifsc_swift_code = models.CharField(max_length=30, blank=True)
    iban = models.CharField(max_length=50, blank=True)
    currency = models.CharField(max_length=5, default='USD')
    is_primary = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='+')
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'employee_hub'
        db_table = 'employee_bank_details'
        ordering = ['-is_primary', '-created_at']

    def __str__(self):
        return f"{self.bank_name} ****{self.account_number[-4:]} ({self.employee})"


class TaxDeclaration(models.Model):
    """Employee tax declaration / investment proofs submitted for TDS computation."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='tax_declarations')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='tax_declarations')
    financial_year = models.CharField(max_length=10, help_text='e.g. 2025-26')
    tax_regime = models.CharField(max_length=20, choices=[('old', 'Old Regime'), ('new', 'New Regime')], default='new')
    declared_investments = models.JSONField(default=dict,
        help_text='{"80C": 150000, "80D": 25000, "HRA": 120000, ...}')
    proof_documents = models.JSONField(default=list)
    declared_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    approved_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='+')
    review_notes = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'employee_hub'
        db_table = 'employee_tax_declarations'
        unique_together = [('tenant', 'employee', 'financial_year')]
        ordering = ['-financial_year']

    def __str__(self):
        return f"Tax {self.financial_year} — {self.employee} ({self.status})"


class EmergencyContact(models.Model):
    """Emergency contact for an employee."""
    RELATIONSHIP_CHOICES = [
        ('spouse', 'Spouse'), ('parent', 'Parent'), ('sibling', 'Sibling'),
        ('child', 'Child'), ('friend', 'Friend'), ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='emergency_contacts')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='emergency_contacts')
    full_name = models.CharField(max_length=200)
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)
    phone_primary = models.CharField(max_length=30)
    phone_secondary = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'employee_hub'
        db_table = 'employee_emergency_contacts'
        ordering = ['-is_primary', 'full_name']

    def __str__(self):
        return f"{self.full_name} ({self.relationship}) — {self.employee}"


class Dependent(models.Model):
    """Employee dependent (child, spouse, parent) for benefits and tax purposes."""
    RELATIONSHIP_CHOICES = [
        ('spouse', 'Spouse'), ('child', 'Child'), ('parent', 'Parent'),
        ('parent_in_law', 'Parent-in-law'), ('sibling', 'Sibling'), ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='dependents')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='dependents')
    full_name = models.CharField(max_length=200)
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, blank=True)
    national_id = models.CharField(max_length=50, blank=True)
    is_covered_by_benefits = models.BooleanField(default=False)
    proof_documents = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'employee_hub'
        db_table = 'employee_dependents'
        ordering = ['relationship', 'full_name']

    def __str__(self):
        return f"{self.full_name} ({self.relationship}) — {self.employee}"


# ---------------------------------------------------------------------------
# 4. Payslips / tax letters / salary history
# ---------------------------------------------------------------------------

class PayslipAccess(models.Model):
    """Record of employee accessing/downloading a payslip."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='payslip_accesses')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='payslip_accesses')
    payslip_month = models.CharField(max_length=7, help_text='YYYY-MM')
    payslip_year = models.IntegerField()
    file_url = models.CharField(max_length=500)
    accessed_at = models.DateTimeField(auto_now_add=True)
    download_count = models.IntegerField(default=1)

    class Meta:
        app_label = 'employee_hub'
        db_table = 'payslip_accesses'
        ordering = ['-payslip_year', '-payslip_month']

    def __str__(self):
        return f"{self.employee} payslip {self.payslip_month}"


class TaxLetterRequest(models.Model):
    """Request for a tax letter / Form 16 / salary certificate for tax filing."""
    LETTER_TYPES = [
        ('form16', 'Form 16'),
        ('form16a', 'Form 16A'),
        ('salary_certificate', 'Salary Certificate'),
        ('tax_computation', 'Tax Computation Sheet'),
        ('it_declaration', 'IT Declaration Summary'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'), ('generated', 'Generated'), ('dispatched', 'Dispatched'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='tax_letter_requests')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='tax_letter_requests')
    letter_type = models.CharField(max_length=30, choices=LETTER_TYPES)
    financial_year = models.CharField(max_length=10)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    generated_file_url = models.CharField(max_length=500, blank=True)
    notes = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    fulfilled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'employee_hub'
        db_table = 'tax_letter_requests'
        ordering = ['-requested_at']

    def __str__(self):
        return f"{self.letter_type} {self.financial_year} — {self.employee}"


# ---------------------------------------------------------------------------
# 5 & 6. Shift self-service / Overtime
# ---------------------------------------------------------------------------

class ShiftSwapRequest(models.Model):
    """Employee-initiated shift swap request with a colleague."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('approved', 'Approved by Manager'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='hub_shift_swap_requests')
    requester = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='hub_shift_swap_requests_sent')
    swap_with = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='hub_shift_swap_requests_received')
    requester_shift_date = models.DateField()
    swap_with_shift_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='+')
    review_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'employee_hub'
        db_table = 'hub_shift_swap_requests'
        ordering = ['-created_at']

    def __str__(self):
        return f"Swap: {self.requester} ({self.requester_shift_date}) <-> {self.swap_with} ({self.swap_with_shift_date})"


class OvertimeRequest(models.Model):
    """Employee overtime claim with approval workflow."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
    ]
    OT_TYPE_CHOICES = [
        ('weekday', 'Weekday OT'),
        ('weekend', 'Weekend OT'),
        ('holiday', 'Holiday OT'),
        ('comp_off', 'Compensatory Off'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='overtime_requests')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='overtime_requests')
    ot_date = models.DateField()
    ot_type = models.CharField(max_length=20, choices=OT_TYPE_CHOICES, default='weekday')
    hours_claimed = models.DecimalField(max_digits=5, decimal_places=2)
    hours_approved = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    task_description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='+')
    approval_notes = models.TextField(blank=True)
    payroll_period = models.CharField(max_length=7, blank=True, help_text='YYYY-MM when paid')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'employee_hub'
        db_table = 'overtime_requests'
        ordering = ['-ot_date']

    def __str__(self):
        return f"OT {self.ot_date} {self.hours_claimed}h — {self.employee} ({self.status})"


# ---------------------------------------------------------------------------
# 7. Benefits enrollment and life-event changes
# (BenefitPlan is defined in platform_core — no duplicate here)
# ---------------------------------------------------------------------------

class BenefitsEnrollment(models.Model):
    """Employee enrollment in a benefit plan."""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('pending', 'Pending Approval'),
        ('waived', 'Waived'),
        ('terminated', 'Terminated'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='benefits_enrollments')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='benefits_enrollments')
    plan = models.ForeignKey('platform_core.BenefitPlan', on_delete=models.CASCADE, related_name='hub_enrollments')
    coverage_level = models.CharField(max_length=30, default='employee_only')
    enrolled_dependents = models.ManyToManyField('Dependent', blank=True, related_name='benefit_enrollments')
    effective_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    employee_contribution = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    employer_contribution = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    enrollment_notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'employee_hub'
        db_table = 'benefits_enrollments'
        unique_together = [('tenant', 'employee', 'plan', 'effective_date')]
        ordering = ['-effective_date']

    def __str__(self):
        return f"{self.employee} — {self.plan} ({self.status})"


class LifeEventChange(models.Model):
    """Life event triggering a benefits change window (marriage, birth, divorce, etc.)."""
    EVENT_TYPES = [
        ('marriage', 'Marriage'),
        ('birth_adoption', 'Birth / Adoption'),
        ('divorce', 'Divorce / Legal Separation'),
        ('death_of_dependent', 'Death of Dependent'),
        ('dependent_lost_coverage', 'Dependent Lost Other Coverage'),
        ('dependent_gained_coverage', 'Dependent Gained Other Coverage'),
        ('relocation', 'Relocation'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='life_event_changes')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='life_event_changes')
    event_type = models.CharField(max_length=40, choices=EVENT_TYPES)
    event_date = models.DateField()
    description = models.TextField(blank=True)
    supporting_documents = models.JSONField(default=list)
    requested_changes = models.JSONField(default=dict,
        help_text='{"add_dependent": [...], "change_coverage_level": "employee_family"}')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='+')
    review_notes = models.TextField(blank=True)
    change_window_end = models.DateField(null=True, blank=True,
        help_text='Deadline by which changes must be applied (typically 30 days from event)')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'employee_hub'
        db_table = 'life_event_changes'
        ordering = ['-event_date']

    def __str__(self):
        return f"{self.event_type} — {self.employee} ({self.event_date})"


# ---------------------------------------------------------------------------
# 8. Document vault
# ---------------------------------------------------------------------------

class EmployeeDocumentVault(models.Model):
    """Secure personal document vault for employee-uploaded documents."""
    DOC_CATEGORIES = [
        ('passport', 'Passport'),
        ('national_id', 'National ID / Aadhaar'),
        ('driving_license', "Driver's License"),
        ('educational', 'Educational Certificate'),
        ('professional_cert', 'Professional Certification'),
        ('visa_permit', 'Visa / Work Permit'),
        ('pan_tax', 'PAN / Tax ID'),
        ('salary_proof', 'Salary Proof'),
        ('insurance', 'Insurance Document'),
        ('other', 'Other'),
    ]
    VISIBILITY_CHOICES = [
        ('private', 'Private — Employee only'),
        ('hr', 'HR & Managers'),
        ('company', 'Company-wide'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='document_vaults')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='document_vault_entries')
    document_name = models.CharField(max_length=300)
    category = models.CharField(max_length=30, choices=DOC_CATEGORIES)
    file_url = models.CharField(max_length=500)
    file_size_kb = models.IntegerField(default=0)
    mime_type = models.CharField(max_length=100, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    issuing_authority = models.CharField(max_length=200, blank=True)
    document_number = models.CharField(max_length=100, blank=True)
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='hr')
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='+')
    verified_at = models.DateTimeField(null=True, blank=True)
    tags = models.JSONField(default=list)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'employee_hub'
        db_table = 'employee_document_vault'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.document_name} ({self.category}) — {self.employee}"


# ---------------------------------------------------------------------------
# 9. Policy acknowledgement center
# ---------------------------------------------------------------------------

class PolicyAcknowledgement(models.Model):
    """Employee acknowledgement of a policy document."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('acknowledged', 'Acknowledged'),
        ('overdue', 'Overdue'),
        ('exempted', 'Exempted'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='hub_policy_acknowledgements')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='hub_policy_acknowledgements')
    policy_document = models.ForeignKey('documents_policies.PolicyDocument', on_delete=models.CASCADE,
                                         related_name='hub_acknowledgements')
    policy_version = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    due_date = models.DateField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    digital_signature = models.CharField(max_length=500, blank=True,
        help_text='Hash or e-signature token confirming acceptance')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    exemption_reason = models.TextField(blank=True)
    reminder_count = models.IntegerField(default=0)
    last_reminded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'employee_hub'
        db_table = 'hub_policy_acknowledgements'
        unique_together = [('tenant', 'employee', 'policy_document', 'policy_version')]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee} ack {self.policy_document} ({self.status})"


# ---------------------------------------------------------------------------
# 10. Training and certification center
# ---------------------------------------------------------------------------

class TrainingEnrollment(models.Model):
    """Employee enrollment in a learning/training course."""
    STATUS_CHOICES = [
        ('enrolled', 'Enrolled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('dropped', 'Dropped'),
        ('waitlisted', 'Waitlisted'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='training_enrollments')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='training_enrollments')
    course_title = models.CharField(max_length=300)
    course_code = models.CharField(max_length=50, blank=True)
    provider = models.CharField(max_length=200, blank=True)
    course_url = models.CharField(max_length=500, blank=True)
    duration_hours = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    is_mandatory = models.BooleanField(default=False)
    enrollment_date = models.DateField()
    start_date = models.DateField(null=True, blank=True)
    completion_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    progress_pct = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='enrolled')
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    certificate_url = models.CharField(max_length=500, blank=True)
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'employee_hub'
        db_table = 'training_enrollments'
        ordering = ['-enrollment_date']

    def __str__(self):
        return f"{self.employee} — {self.course_title} ({self.status})"


class CertificationRecord(models.Model):
    """Employee professional certification (external or internal)."""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expiring_soon', 'Expiring Soon'),
        ('expired', 'Expired'),
        ('revoked', 'Revoked'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='certification_records')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='certification_records')
    certification_name = models.CharField(max_length=300)
    issuing_body = models.CharField(max_length=200)
    credential_id = models.CharField(max_length=100, blank=True)
    issue_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    certificate_url = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    skill_tags = models.JSONField(default=list)
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'employee_hub'
        db_table = 'certification_records'
        ordering = ['-issue_date']

    def __str__(self):
        return f"{self.certification_name} — {self.employee}"


# ---------------------------------------------------------------------------
# 11. Goals / reviews / feedback (read-view support)
# ---------------------------------------------------------------------------

class GoalComment(models.Model):
    """Employee comment on a performance goal (extends performance app goals)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='goal_comments')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='goal_comments')
    goal_id = models.UUIDField(help_text='UUID of the Goal in performance app')
    comment = models.TextField()
    is_private = models.BooleanField(default=False, help_text='Private notes visible only to employee')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'employee_hub'
        db_table = 'goal_comments'
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment by {self.employee} on goal {self.goal_id}"


# ---------------------------------------------------------------------------
# 12. Internal jobs and gigs tab
# ---------------------------------------------------------------------------

class InternalJobApplication(models.Model):
    """Employee application for an internal job posting or gig."""
    APPLICATION_TYPES = [
        ('full_time', 'Full-Time Transfer'),
        ('lateral', 'Lateral Move'),
        ('promotion', 'Promotion'),
        ('gig', 'Internal Gig'),
        ('secondment', 'Secondment'),
        ('project', 'Project Rotation'),
    ]
    STATUS_CHOICES = [
        ('applied', 'Applied'),
        ('shortlisted', 'Shortlisted'),
        ('interview', 'Interview Scheduled'),
        ('offer_extended', 'Offer Extended'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='internal_job_applications')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='internal_job_applications')
    job_posting_id = models.UUIDField(help_text='UUID of JobPosting in internal_marketplace or integrations app')
    job_title = models.CharField(max_length=300)
    application_type = models.CharField(max_length=20, choices=APPLICATION_TYPES, default='lateral')
    cover_note = models.TextField(blank=True)
    resume_url = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='applied')
    current_manager_notified = models.BooleanField(default=False)
    hiring_manager_notes = models.TextField(blank=True)
    interview_date = models.DateTimeField(null=True, blank=True)
    outcome_date = models.DateField(null=True, blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'employee_hub'
        db_table = 'internal_job_applications'
        ordering = ['-applied_at']

    def __str__(self):
        return f"{self.employee} → {self.job_title} ({self.status})"


# ---------------------------------------------------------------------------
# 13. Helpdesk and case status
# ---------------------------------------------------------------------------

class EmployeeCase(models.Model):
    """HR helpdesk case raised by an employee."""
    CATEGORY_CHOICES = [
        ('payroll', 'Payroll Query'),
        ('leave', 'Leave Query'),
        ('benefits', 'Benefits Query'),
        ('it_access', 'IT / System Access'),
        ('policy', 'Policy Clarification'),
        ('grievance', 'Grievance'),
        ('letter_request', 'Letter Request'),
        ('other', 'Other'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('urgent', 'Urgent'),
    ]
    STATUS_CHOICES = [
        ('open', 'Open'), ('in_progress', 'In Progress'),
        ('pending_employee', 'Pending Employee Response'),
        ('resolved', 'Resolved'), ('closed', 'Closed'), ('escalated', 'Escalated'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='employee_cases')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='employee_cases')
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    subject = models.CharField(max_length=300)
    description = models.TextField()
    attachments = models.JSONField(default=list)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='open')
    assigned_agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                        null=True, blank=True, related_name='+')
    resolution_notes = models.TextField(blank=True)
    sla_due_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    satisfaction_rating = models.IntegerField(null=True, blank=True,
        help_text='1-5 CSAT rating by employee')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'employee_hub'
        db_table = 'employee_cases'
        ordering = ['-created_at']

    def __str__(self):
        return f"Case #{str(self.id)[:8]} — {self.subject} ({self.status})"


class CaseComment(models.Model):
    """Comment thread on an employee case."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='case_comments')
    case = models.ForeignKey(EmployeeCase, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')
    body = models.TextField()
    is_internal = models.BooleanField(default=False, help_text='Internal note not visible to employee')
    attachments = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'employee_hub'
        db_table = 'case_comments'
        ordering = ['created_at']

    def __str__(self):
        return f"Comment on case {self.case_id} by {self.author}"


# ---------------------------------------------------------------------------
# 14. Asset requests and returns
# ---------------------------------------------------------------------------

class AssetRequest(models.Model):
    """Employee request for an asset (laptop, phone, equipment, etc.)."""
    ASSET_CATEGORIES = [
        ('laptop', 'Laptop / Computer'),
        ('mobile', 'Mobile Phone'),
        ('monitor', 'Monitor'),
        ('headset', 'Headset'),
        ('keyboard_mouse', 'Keyboard & Mouse'),
        ('desk', 'Desk / Furniture'),
        ('access_card', 'Access Card / Badge'),
        ('vehicle', 'Company Vehicle'),
        ('software_license', 'Software License'),
        ('other', 'Other'),
    ]
    REQUEST_TYPES = [
        ('new', 'New Request'),
        ('replacement', 'Replacement'),
        ('return', 'Return'),
        ('repair', 'Repair'),
        ('upgrade', 'Upgrade'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('issued', 'Issued'),
        ('returned', 'Returned'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='asset_requests')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='asset_requests')
    asset_category = models.CharField(max_length=30, choices=ASSET_CATEGORIES)
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPES, default='new')
    asset_description = models.CharField(max_length=300)
    justification = models.TextField(blank=True)
    quantity = models.IntegerField(default=1)
    asset_tag = models.CharField(max_length=100, blank=True, help_text='Tag of existing asset (for return/repair)')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='+')
    approval_notes = models.TextField(blank=True)
    issued_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'employee_hub'
        db_table = 'asset_requests'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.request_type} {self.asset_category} — {self.employee} ({self.status})"


# ---------------------------------------------------------------------------
# 15. Multilingual self-service
# ---------------------------------------------------------------------------

class EmployeeLanguagePreference(models.Model):
    """Employee language and locale preferences for the self-service portal."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='language_preferences')
    employee = models.OneToOneField('core_hr.Employee', on_delete=models.CASCADE,
                                     related_name='language_preference')
    ui_language = models.CharField(max_length=10, default='en',
        help_text='BCP-47 language tag, e.g. en, fr, ar, zh-Hans')
    date_format = models.CharField(max_length=20, default='YYYY-MM-DD')
    time_format = models.CharField(max_length=5, default='24h', choices=[('12h', '12-hour'), ('24h', '24-hour')])
    timezone = models.CharField(max_length=60, default='UTC')
    currency_display = models.CharField(max_length=5, default='USD')
    number_format = models.CharField(max_length=10, default='en-US',
        help_text='Locale string for Intl.NumberFormat, e.g. de-DE')
    rtl = models.BooleanField(default=False, help_text='Right-to-left UI layout')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'employee_hub'
        db_table = 'employee_language_preferences'

    def __str__(self):
        return f"{self.employee} — {self.ui_language}"


# ---------------------------------------------------------------------------
# 16. WCAG 2.2 / Mobile accessibility preferences
# ---------------------------------------------------------------------------

class AccessibilityPreference(models.Model):
    """Employee accessibility settings for WCAG 2.2 AA compliance."""
    CONTRAST_MODES = [
        ('default', 'Default'),
        ('high_contrast', 'High Contrast (WCAG AAA)'),
        ('dark', 'Dark Mode'),
        ('light', 'Light Mode'),
    ]
    FONT_SIZE_CHOICES = [
        ('small', 'Small'), ('medium', 'Medium'), ('large', 'Large'), ('x_large', 'Extra Large'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='accessibility_prefs')
    employee = models.OneToOneField('core_hr.Employee', on_delete=models.CASCADE,
                                     related_name='accessibility_pref')
    contrast_mode = models.CharField(max_length=20, choices=CONTRAST_MODES, default='default')
    font_size = models.CharField(max_length=10, choices=FONT_SIZE_CHOICES, default='medium')
    reduce_motion = models.BooleanField(default=False,
        help_text='Respect prefers-reduced-motion; disables animations')
    screen_reader_optimised = models.BooleanField(default=False,
        help_text='Adds extra ARIA labels and skips decorative images')
    keyboard_navigation_hints = models.BooleanField(default=True)
    focus_indicator = models.CharField(max_length=20, default='default',
        choices=[('default', 'Default'), ('enhanced', 'Enhanced (3px outline)'), ('high_vis', 'High Visibility')])
    touch_target_size = models.CharField(max_length=10, default='standard',
        choices=[('standard', 'Standard (24px)'), ('large', 'Large (44px)')],
        help_text='WCAG 2.2 SC 2.5.8 minimum target size')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'employee_hub'
        db_table = 'accessibility_preferences'

    def __str__(self):
        return f"{self.employee} accessibility ({self.contrast_mode}, {self.font_size})"


# ---------------------------------------------------------------------------
# Legacy alias kept for backward-compat (was SelfServiceRequest in stub)
# ---------------------------------------------------------------------------

class SelfServiceRequest(models.Model):
    """Employee self-service request (letter, certificate, info change, etc.)."""
    REQUEST_TYPES = [
        ('employment_letter', 'Employment Letter'),
        ('salary_certificate', 'Salary Certificate'),
        ('experience_letter', 'Experience Letter'),
        ('noc_letter', 'No Objection Certificate'),
        ('bank_letter', 'Bank Confirmation Letter'),
        ('address_update', 'Address Update'),
        ('name_change', 'Name Change'),
        ('bank_details_update', 'Bank Details Update'),
        ('emergency_contact_update', 'Emergency Contact Update'),
        ('document_request', 'Document Request'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'), ('in_review', 'In Review'),
        ('approved', 'Approved'), ('rejected', 'Rejected'), ('completed', 'Completed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='self_service_requests')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='self_service_requests')
    request_type = models.CharField(max_length=40, choices=REQUEST_TYPES)
    subject = models.CharField(max_length=300)
    details = models.TextField(blank=True)
    attachments = models.JSONField(default=list)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='+')
    completed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                      null=True, blank=True, related_name='+')
    response_notes = models.TextField(blank=True)
    output_file = models.CharField(max_length=500, blank=True)
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'employee_hub'
        db_table = 'self_service_requests'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.request_type}: {self.employee} ({self.status})"
