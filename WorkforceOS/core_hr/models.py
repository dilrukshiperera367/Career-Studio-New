"""
Core HR models — the main business objects of the HRM system.
Company, Branch, Department, Position, Employee, JobHistory, Documents.
"""

import uuid
from django.db import models
from django.conf import settings
from simple_history.models import HistoricalRecords


# ============ COMPANY (Legal Entity) ============

class Company(models.Model):
    """Legal entity within a tenant. A tenant can have multiple companies."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='companies')
    name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255, blank=True)
    registration_no = models.CharField(max_length=100, blank=True)
    tax_id = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=3, default='LKA')
    currency = models.CharField(max_length=3, default='LKR')
    address = models.JSONField(default=dict, blank=True)
    logo_url = models.URLField(max_length=500, blank=True)
    settings = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, default='active', choices=[
        ('active', 'Active'), ('inactive', 'Inactive'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'companies'
        verbose_name_plural = 'companies'

    def __str__(self):
        return self.name


# ============ BRANCH ============

class Branch(models.Model):
    """Physical location / office of a company."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='branches')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20, blank=True)
    address = models.JSONField(default=dict, blank=True)
    country = models.CharField(max_length=3, default='LKA')
    timezone = models.CharField(max_length=50, default='Asia/Colombo')
    geo_coordinates = models.JSONField(
        null=True, blank=True,
        help_text='{"lat": 6.9271, "lng": 79.8612, "radius_m": 200}'
    )
    status = models.CharField(max_length=20, default='active', choices=[
        ('active', 'Active'), ('inactive', 'Inactive'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'branches'
        verbose_name_plural = 'branches'

    def __str__(self):
        return f"{self.name} ({self.company.name})"


# ============ DEPARTMENT ============

class Department(models.Model):
    """Hierarchical department structure."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='departments')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='departments', null=True, blank=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20, blank=True)
    head = models.ForeignKey(
        'Employee', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='headed_departments'
    )
    cost_center = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, default='active', choices=[
        ('active', 'Active'), ('inactive', 'Inactive'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'departments'

    def __str__(self):
        return self.name

    def get_ancestors(self):
        """Return list of parent departments up to root."""
        ancestors = []
        current = self.parent
        while current:
            ancestors.append(current)
            current = current.parent
        return ancestors

    def get_descendants(self):
        """Return all child departments recursively."""
        descendants = list(self.children.all())
        for child in list(descendants):
            descendants.extend(child.get_descendants())
        return descendants


# ============ POSITION ============

class Position(models.Model):
    """Job role definition — represents a position in the org structure."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='positions')
    title = models.CharField(max_length=255)
    code = models.CharField(max_length=20, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='positions')
    grade = models.CharField(max_length=20, blank=True, help_text="Job grade (e.g., L1, L2, L3)")
    band = models.CharField(max_length=20, blank=True, help_text="Salary band (e.g., B1, B2)")
    reports_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='direct_reports')
    headcount = models.IntegerField(default=1)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='active', choices=[
        ('active', 'Active'), ('inactive', 'Inactive'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'positions'

    def __str__(self):
        return f"{self.title} ({self.code})" if self.code else self.title


# ============ EMPLOYEE (Single Source of Truth) ============

class Employee(models.Model):
    """
    The central record — "Single Source of Truth" for every employee.
    All modules reference this model.
    """

    CONTRACT_TYPE_CHOICES = [
        ('permanent', 'Permanent'),
        ('contract', 'Contract'),
        ('probation', 'Probation'),
        ('intern', 'Intern'),
        ('part_time', 'Part-time'),
        ('casual', 'Casual'),
    ]

    EMPLOYMENT_TYPE_CHOICES = [
        ('full_time', 'Full-time'),
        ('part_time', 'Part-time'),
        ('casual', 'Casual'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('probation', 'Probation'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
        ('resigned', 'Resigned'),
        ('retired', 'Retired'),
        ('deceased', 'Deceased'),
    ]

    SEPARATION_TYPE_CHOICES = [
        ('resignation', 'Resignation'),
        ('termination', 'Termination'),
        ('retirement', 'Retirement'),
        ('contract_end', 'Contract End'),
        ('death', 'Death'),
        ('mutual', 'Mutual Separation'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='employees')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='employees')
    employee_number = models.CharField(max_length=50, blank=True)

    # --- Personal Info ---
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    preferred_name = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, blank=True, choices=[
        ('male', 'Male'), ('female', 'Female'), ('other', 'Other'), ('prefer_not_to_say', 'Prefer not to say'),
    ])
    marital_status = models.CharField(max_length=20, blank=True, choices=[
        ('single', 'Single'), ('married', 'Married'), ('divorced', 'Divorced'), ('widowed', 'Widowed'),
    ])
    nationality = models.CharField(max_length=50, blank=True)
    nic_number = models.CharField(max_length=20, blank=True, help_text="Sri Lanka National ID")
    passport_number = models.CharField(max_length=20, blank=True)
    photo_url = models.URLField(max_length=500, blank=True)

    # --- Contact Info ---
    personal_email = models.EmailField(max_length=320, blank=True)
    work_email = models.EmailField(max_length=320)
    mobile_phone = models.CharField(max_length=20, blank=True)
    home_phone = models.CharField(max_length=20, blank=True)
    address_current = models.JSONField(default=dict, blank=True)
    address_permanent = models.JSONField(default=dict, blank=True)

    # --- Employment Info ---
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')
    manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='direct_reports')
    hire_date = models.DateField()
    confirmation_date = models.DateField(null=True, blank=True)
    contract_type = models.CharField(max_length=30, default='permanent', choices=CONTRACT_TYPE_CHOICES)
    contract_end_date = models.DateField(null=True, blank=True)
    employment_type = models.CharField(max_length=20, default='full_time', choices=EMPLOYMENT_TYPE_CHOICES)
    work_schedule = models.CharField(max_length=20, default='standard', choices=[
        ('standard', 'Standard'), ('shift', 'Shift-based'), ('flexible', 'Flexible'),
    ])
    notice_period_days = models.IntegerField(default=30)
    probation_months = models.IntegerField(default=3)

    # --- Status ---
    status = models.CharField(max_length=20, default='active', choices=STATUS_CHOICES)
    separation_date = models.DateField(null=True, blank=True)
    separation_type = models.CharField(max_length=30, blank=True, choices=SEPARATION_TYPE_CHOICES)
    separation_reason = models.TextField(blank=True)

    # --- Emergency Contact ---
    emergency_contact = models.JSONField(default=dict, blank=True,
                                         help_text='{"name": "", "relationship": "", "phone": "", "address": ""}')

    # --- Bank Details ---
    bank_details = models.JSONField(default=dict, blank=True,
                                    help_text='{"bank_name": "", "branch": "", "account_no": "", "account_type": ""}')

    # --- Source tracking ---
    source = models.CharField(max_length=30, default='manual', choices=[
        ('manual', 'Manual Entry'), ('ats_import', 'ATS Import'), ('bulk_import', 'Bulk Import'),
    ])
    ats_candidate_id = models.UUIDField(null=True, blank=True, help_text="Link to ATS candidate record")

    # --- Custom Fields ---
    custom_fields = models.JSONField(default=dict, blank=True)

    # --- Linked User Account ---
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='employee_profile'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_employees'
    )
    history = HistoricalRecords()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'employees'
        ordering = ['last_name', 'first_name']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'employee_number'],
                name='unique_tenant_employee_number',
                condition=models.Q(employee_number__gt='')
            )
        ]
        indexes = [
            models.Index(fields=['tenant', 'status'], name='idx_emp_status'),
            models.Index(fields=['tenant', 'company'], name='idx_emp_company'),
            models.Index(fields=['tenant', 'department'], name='idx_emp_dept'),
            models.Index(fields=['tenant', 'nic_number'], name='idx_emp_nic'),
        ]

    def __str__(self):
        return f"{self.employee_number or '—'} {self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        # Auto-generate employee number if not set
        if not self.employee_number:
            self.employee_number = self._generate_employee_number()
        super().save(*args, **kwargs)

    def _generate_employee_number(self):
        """Generate next employee number: EMP-0001 format."""
        last = Employee.objects.filter(
            tenant=self.tenant,
            employee_number__startswith='EMP-'
        ).order_by('-employee_number').first()

        if last and last.employee_number:
            try:
                num = int(last.employee_number.split('-')[1]) + 1
            except (ValueError, IndexError):
                num = 1
        else:
            num = 1
        return f"EMP-{num:04d}"


# ============ JOB HISTORY (Immutable Audit) ============

class JobHistory(models.Model):
    """Immutable record of every job change (promotion, transfer, etc.)."""
    CHANGE_TYPES = [
        ('hire', 'Hire'),
        ('promotion', 'Promotion'),
        ('transfer', 'Transfer'),
        ('redesignation', 'Redesignation'),
        ('demotion', 'Demotion'),
        ('suspension', 'Suspension'),
        ('reinstatement', 'Reinstatement'),
        ('confirmation', 'Confirmation'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='job_histories')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='job_history')
    change_type = models.CharField(max_length=30, choices=CHANGE_TYPES)
    effective_date = models.DateField()

    # Previous values
    prev_position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    prev_department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    prev_branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    prev_manager = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    prev_grade = models.CharField(max_length=20, blank=True)

    # New values
    new_position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    new_department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    new_branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    new_manager = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    new_grade = models.CharField(max_length=20, blank=True)

    reason = models.TextField(blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)  # Immutable — no updated_at

    class Meta:
        db_table = 'job_history'
        ordering = ['-effective_date', '-created_at']
        indexes = [
            models.Index(fields=['employee', '-effective_date'], name='idx_jobhist_emp_date'),
        ]

    def __str__(self):
        return f"{self.employee} — {self.change_type} on {self.effective_date}"


# ============ EMPLOYEE DOCUMENTS ============

class EmployeeDocument(models.Model):
    """Documents associated with an employee (contracts, IDs, certificates, etc.)."""
    CATEGORY_CHOICES = [
        ('contract', 'Contract'),
        ('id_proof', 'ID Proof'),
        ('certificate', 'Certificate'),
        ('policy_ack', 'Policy Acknowledgement'),
        ('payslip', 'Payslip'),
        ('letter', 'Letter'),
        ('qualification', 'Qualification'),
        ('other', 'Other'),
    ]

    ESIGN_STATUS_CHOICES = [
        ('not_required', 'Not Required'),
        ('pending', 'Pending'),
        ('signed', 'Signed'),
        ('declined', 'Declined'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='employee_documents')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='documents')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/%Y/%m/')
    file_name = models.CharField(max_length=255, blank=True)
    file_type = models.CharField(max_length=10, blank=True)
    file_size_bytes = models.IntegerField(null=True, blank=True)
    version = models.IntegerField(default=1)
    expiry_date = models.DateField(null=True, blank=True)
    e_sign_status = models.CharField(max_length=20, default='not_required', choices=ESIGN_STATUS_CHOICES)
    e_signed_at = models.DateTimeField(null=True, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    visibility = models.CharField(max_length=20, default='hr_only', choices=[
        ('hr_only', 'HR Only'), ('employee', 'Employee + HR'), ('public', 'All Staff'),
    ])
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'employee_documents'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.employee})"


# ============ ANNOUNCEMENT ============

class Announcement(models.Model):
    """Company-wide or targeted announcements."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='announcements')
    title = models.CharField(max_length=255)
    body = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    audience_filter = models.JSONField(default=dict, blank=True,
                                        help_text='{"departments": [], "branches": [], "all": true}')
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    read_receipt_enabled = models.BooleanField(default=False)
    pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'announcements'
        ordering = ['-pinned', '-published_at']

    def __str__(self):
        return self.title


# ---------------------------------------------------------------------------
# P1 Upgrades — Critical Roles & Internal Mobility Profiles
# ---------------------------------------------------------------------------

class CriticalRole(models.Model):
    """Flags a Position as business-critical for succession planning purposes."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='critical_roles')
    position = models.OneToOneField(
        Position, on_delete=models.CASCADE, related_name='critical_role',
    )
    rationale = models.TextField(blank=True,
        help_text="Why this role is considered critical")
    impact_if_vacant = models.CharField(max_length=20, default='high', choices=[
        ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical'),
    ])
    target_successor_count = models.IntegerField(default=2,
        help_text="Desired number of ready successors")
    review_date = models.DateField(null=True, blank=True,
        help_text="Next scheduled review of this critical role designation")
    flagged_by = models.ForeignKey(
        'authentication.User', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='flagged_critical_roles',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'critical_roles'
        ordering = ['position__title']

    def __str__(self):
        return f"Critical: {self.position}"


class InternalMobilityProfile(models.Model):
    """Employee's self-declared internal mobility preferences."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='core_hr_mobility_profiles')
    employee = models.OneToOneField(
        Employee, on_delete=models.CASCADE, related_name='core_mobility_profile',
    )
    open_to_move = models.BooleanField(default=False,
        help_text="Employee is open to internal moves")
    mobility_type = models.JSONField(default=list, blank=True,
        help_text='["lateral","promotion","project","relocation","remote"]')
    preferred_departments = models.ManyToManyField(
        Department, blank=True, related_name='interested_employees',
    )
    preferred_locations = models.JSONField(default=list, blank=True,
        help_text="List of preferred branch/location names")
    target_roles = models.JSONField(default=list, blank=True,
        help_text="List of position IDs the employee is targeting")
    earliest_available = models.DateField(null=True, blank=True,
        help_text="Earliest date employee is available for a move")
    notes = models.TextField(blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'internal_mobility_profiles'

    def __str__(self):
        return f"Mobility Profile: {self.employee}"
