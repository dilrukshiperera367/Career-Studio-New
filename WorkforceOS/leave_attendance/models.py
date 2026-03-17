"""
Leave & Attendance models — Leave types, balances, requests, holidays,
shift management, attendance records, overtime.
"""

import uuid
from django.db import models
from django.conf import settings


# ============ LEAVE TYPES ============

class LeaveType(models.Model):
    """Configurable leave policy (annual, casual, sick, maternity, etc.)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='leave_types')
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10)
    paid = models.BooleanField(default=True)
    max_days_per_year = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    carry_forward = models.BooleanField(default=False)
    max_carry_forward = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    encashable = models.BooleanField(default=False)
    accrual_type = models.CharField(max_length=20, default='annual', choices=[
        ('annual', 'Annual'), ('monthly', 'Monthly'), ('none', 'No Accrual'),
    ])
    applicable_gender = models.CharField(max_length=10, blank=True, choices=[
        ('male', 'Male'), ('female', 'Female'),
    ], help_text="Leave blank for all genders")
    probation_eligible = models.BooleanField(default=False)
    min_service_months = models.IntegerField(default=0)
    allow_half_day = models.BooleanField(default=True)
    allow_short_leave = models.BooleanField(default=False)
    requires_attachment = models.BooleanField(default=False)
    requires_attachment_after_days = models.IntegerField(null=True, blank=True)
    color = models.CharField(max_length=7, default='#3B82F6')
    sort_order = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default='active', choices=[
        ('active', 'Active'), ('inactive', 'Inactive'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'leave_types'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return f"{self.name} ({self.code})"


# ============ LEAVE BALANCES ============

class LeaveBalance(models.Model):
    """Per-employee, per-leave-type, per-year balance tracking."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='leave_balances')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='leave_balances')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, related_name='balances')
    year = models.IntegerField()
    entitled = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    taken = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    pending = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    carried_forward = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    adjustment = models.DecimalField(max_digits=5, decimal_places=1, default=0)

    class Meta:
        db_table = 'leave_balances'
        unique_together = ['tenant', 'employee', 'leave_type', 'year']

    @property
    def remaining(self):
        return self.entitled + self.carried_forward + self.adjustment - self.taken - self.pending

    def __str__(self):
        return f"{self.employee} — {self.leave_type.name} {self.year}: {self.remaining} remaining"


# ============ LEAVE REQUESTS ============

class LeaveRequest(models.Model):
    """Employee leave application with approval workflow."""
    STATUS_CHOICES = [
        ('pending', 'Pending'), ('approved', 'Approved'),
        ('rejected', 'Rejected'), ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='leave_requests')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, related_name='requests')
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.DecimalField(max_digits=5, decimal_places=1)
    is_half_day = models.BooleanField(default=False)
    half_day_period = models.CharField(max_length=10, blank=True, choices=[
        ('morning', 'Morning'), ('afternoon', 'Afternoon'),
    ])
    is_short_leave = models.BooleanField(default=False)
    short_leave_from = models.TimeField(null=True, blank=True)
    short_leave_to = models.TimeField(null=True, blank=True)
    reason = models.TextField(blank=True)
    attachment = models.FileField(upload_to='leave_attachments/%Y/%m/', null=True, blank=True)
    status = models.CharField(max_length=20, default='pending', choices=STATUS_CHOICES)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'leave_requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'employee', 'start_date'], name='idx_leave_emp_date'),
            models.Index(fields=['tenant', 'status'], name='idx_leave_status'),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._previous_status = self.status

    def __str__(self):
        return f"{self.employee} — {self.leave_type.name} ({self.start_date} to {self.end_date})"


# ============ HOLIDAY CALENDARS ============

class HolidayCalendar(models.Model):
    """Holiday calendar — can be location/branch-specific."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='holiday_calendars')
    name = models.CharField(max_length=100)
    year = models.IntegerField()
    country = models.CharField(max_length=3, default='LKA')
    applies_to = models.JSONField(default=list, blank=True, help_text="Branch IDs or empty for all")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'holiday_calendars'

    def __str__(self):
        return f"{self.name} ({self.year})"


class Holiday(models.Model):
    """Individual holiday within a calendar."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    calendar = models.ForeignKey(HolidayCalendar, on_delete=models.CASCADE, related_name='holidays')
    name = models.CharField(max_length=255)
    date = models.DateField()
    type = models.CharField(max_length=20, default='public', choices=[
        ('public', 'Public Holiday'), ('mercantile', 'Mercantile Holiday'),
        ('poya', 'Poya Day'), ('optional', 'Optional Holiday'), ('company', 'Company Holiday'),
    ])
    is_optional = models.BooleanField(default=False)

    class Meta:
        db_table = 'holidays'
        ordering = ['date']

    def __str__(self):
        return f"{self.name} ({self.date})"


# ============ SHIFT TEMPLATES ============

class ShiftTemplate(models.Model):
    """Shift definition with working hours and grace period."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='shift_templates')
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, blank=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    break_minutes = models.IntegerField(default=60)
    grace_minutes = models.IntegerField(default=15)
    working_hours = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    is_night_shift = models.BooleanField(default=False)
    color = models.CharField(max_length=7, default='#10B981')
    status = models.CharField(max_length=20, default='active', choices=[
        ('active', 'Active'), ('inactive', 'Inactive'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'shift_templates'

    def __str__(self):
        return f"{self.name} ({self.start_time}–{self.end_time})"


# ============ SHIFT ASSIGNMENTS ============

class ShiftAssignment(models.Model):
    """Assigns a shift to an employee for a specific date or as a recurring default."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='shift_assignments')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='shift_assignments')
    shift = models.ForeignKey(ShiftTemplate, on_delete=models.CASCADE, related_name='assignments')
    date = models.DateField(null=True, blank=True, help_text="Specific date; null if recurring")
    is_default = models.BooleanField(default=False, help_text="If true, repeats weekly")
    day_of_week = models.IntegerField(null=True, blank=True, help_text="0=Mon, 6=Sun (for default shifts)")

    class Meta:
        db_table = 'shift_assignments'
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'employee', 'date'],
                name='unique_shift_per_day',
                condition=models.Q(date__isnull=False)
            )
        ]


# ============ ATTENDANCE RECORDS ============

class AttendanceRecord(models.Model):
    """Daily attendance record for an employee."""
    SOURCE_CHOICES = [
        ('web', 'Web'), ('mobile', 'Mobile'), ('biometric', 'Biometric'),
        ('manual', 'Manual'), ('qr', 'QR Code'),
    ]
    STATUS_CHOICES = [
        ('present', 'Present'), ('absent', 'Absent'), ('half_day', 'Half Day'),
        ('holiday', 'Holiday'), ('leave', 'On Leave'), ('weekend', 'Weekend'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='attendance_records')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    shift = models.ForeignKey(ShiftTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    clock_in = models.DateTimeField(null=True, blank=True)
    clock_out = models.DateTimeField(null=True, blank=True)
    clock_in_source = models.CharField(max_length=20, blank=True, choices=SOURCE_CHOICES)
    clock_out_source = models.CharField(max_length=20, blank=True, choices=SOURCE_CHOICES)
    clock_in_location = models.JSONField(null=True, blank=True, help_text='{"lat": ..., "lng": ..., "address": ...}')
    clock_out_location = models.JSONField(null=True, blank=True)
    clock_in_photo_url = models.URLField(max_length=500, blank=True)
    working_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    late_minutes = models.IntegerField(default=0)
    early_leave_minutes = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default='present', choices=STATUS_CHOICES)
    exception_type = models.CharField(max_length=30, blank=True, choices=[
        ('late', 'Late'), ('early_leave', 'Early Leave'),
        ('missing_punch', 'Missing Punch'), ('overtime', 'Overtime'),
    ])
    regularized = models.BooleanField(default=False)
    regularized_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'attendance_records'
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'employee', 'date'], name='unique_attendance_per_day')
        ]
        indexes = [
            models.Index(fields=['tenant', 'employee', 'date'], name='idx_attend_emp_date'),
            models.Index(fields=['tenant', 'date', 'status'], name='idx_attend_date_status'),
        ]

    def __str__(self):
        return f"{self.employee} — {self.date} ({self.status})"


# ============ OVERTIME RECORDS ============

class OvertimeRecord(models.Model):
    """Overtime request with approval workflow."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='overtime_records')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='overtime_records')
    date = models.DateField()
    hours = models.DecimalField(max_digits=5, decimal_places=2)
    rate_multiplier = models.DecimalField(max_digits=3, decimal_places=1, default=1.5)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ])
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'overtime_records'

    def __str__(self):
        return f"{self.employee} — {self.date}: {self.hours}h OT"


# ============ ROSTER / SCHEDULING (P1 upgrade) ============

class Roster(models.Model):
    """Published weekly/fortnightly roster for a team or department."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='rosters')
    name = models.CharField(max_length=100)
    department = models.ForeignKey('core_hr.Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    branch = models.ForeignKey('core_hr.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    week_start = models.DateField(help_text="Monday of the roster week")
    week_end = models.DateField()
    status = models.CharField(max_length=20, default='draft', choices=[
        ('draft', 'Draft'), ('published', 'Published'), ('archived', 'Archived'),
    ])
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rosters'
        indexes = [
            models.Index(fields=['tenant', 'week_start'], name='idx_roster_week'),
        ]

    def __str__(self):
        return f"{self.name} ({self.week_start} to {self.week_end})"


class RosterSlot(models.Model):
    """A single shift slot on a roster (one employee, one day, one shift)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    roster = models.ForeignKey(Roster, on_delete=models.CASCADE, related_name='slots')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='roster_slots')
    shift = models.ForeignKey(ShiftTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    date = models.DateField()
    is_day_off = models.BooleanField(default=False)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'roster_slots'
        constraints = [
            models.UniqueConstraint(fields=['roster', 'employee', 'date'], name='unique_roster_slot')
        ]

    def __str__(self):
        return f"{self.employee} — {self.date} ({self.shift or 'Day Off'})"


class ShiftSwapRequest(models.Model):
    """Employee-initiated shift swap request between two employees."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='shift_swap_requests')
    requester = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='shift_swap_requests_sent')
    swap_with = models.ForeignKey('core_hr.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='shift_swap_requests_received')
    requester_slot = models.ForeignKey(RosterSlot, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    swap_with_slot = models.ForeignKey(RosterSlot, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    requester_shift = models.ForeignKey(ShiftTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    swap_with_shift = models.ForeignKey(ShiftTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    swap_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected'),
        ('manager_approved', 'Manager Approved'), ('cancelled', 'Cancelled'),
    ])
    peer_response_at = models.DateTimeField(null=True, blank=True)
    manager_approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    manager_approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'shift_swap_requests'

    def __str__(self):
        return f"Swap: {self.requester} ↔ {self.swap_with} on {self.swap_date}"


class ShiftBid(models.Model):
    """Open shift that employees can bid on."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='shift_bids')
    shift = models.ForeignKey(ShiftTemplate, on_delete=models.CASCADE, related_name='bids')
    date = models.DateField()
    department = models.ForeignKey('core_hr.Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    slots_available = models.IntegerField(default=1)
    bid_deadline = models.DateTimeField()
    status = models.CharField(max_length=20, default='open', choices=[
        ('open', 'Open'), ('closed', 'Closed'), ('filled', 'Filled'),
    ])
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'shift_bids'

    def __str__(self):
        return f"Bid: {self.shift} on {self.date}"


class ShiftBidApplication(models.Model):
    """Employee application for an open shift bid."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bid = models.ForeignKey(ShiftBid, on_delete=models.CASCADE, related_name='applications')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='shift_bid_applications')
    status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pending'), ('awarded', 'Awarded'), ('rejected', 'Rejected'),
    ])
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'shift_bid_applications'
        constraints = [
            models.UniqueConstraint(fields=['bid', 'employee'], name='unique_bid_application')
        ]

    def __str__(self):
        return f"{self.employee} → {self.bid}"


class GeofenceZone(models.Model):
    """Geofenced zone for clock-in/out enforcement."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='geofence_zones')
    branch = models.ForeignKey('core_hr.Branch', on_delete=models.SET_NULL, null=True, blank=True, related_name='geofence_zones')
    name = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    radius_meters = models.IntegerField(default=200)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'geofence_zones'

    def __str__(self):
        return f"{self.name} (r={self.radius_meters}m)"


# ---------------------------------------------------------------------------
# Feature 4 additions — Time, Scheduling, Shift & Workforce Operations 2.0
# ---------------------------------------------------------------------------

class EmployeeAvailability(models.Model):
    """Employee availability and preference capture for scheduling."""
    DAY_CHOICES = [
        ('mon', 'Monday'), ('tue', 'Tuesday'), ('wed', 'Wednesday'),
        ('thu', 'Thursday'), ('fri', 'Friday'), ('sat', 'Saturday'), ('sun', 'Sunday'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='employee_availabilities')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='availabilities')
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    preferred_days = models.JSONField(default=list, help_text='["mon","tue","wed"]')
    unavailable_days = models.JSONField(default=list)
    preferred_shifts = models.JSONField(default=list, help_text='List of ShiftTemplate IDs (UUIDs as strings)')
    max_hours_per_week = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    min_hours_per_week = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'employee_availabilities'
        ordering = ['employee', '-effective_from']

    def __str__(self):
        return f"Availability: {self.employee} from {self.effective_from}"


class BreakRecord(models.Model):
    """Break and meal compliance tracking per attendance record."""
    BREAK_TYPES = [
        ('meal', 'Meal Break'), ('rest', 'Rest Break'), ('tea', 'Tea Break'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='break_records')
    attendance_record = models.ForeignKey(AttendanceRecord, on_delete=models.CASCADE, related_name='breaks')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='break_records')
    break_type = models.CharField(max_length=10, choices=BREAK_TYPES, default='meal')
    break_start = models.DateTimeField()
    break_end = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.IntegerField(default=0)
    is_compliant = models.BooleanField(default=True,
        help_text='False if break too short/long vs policy')
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'break_records'
        ordering = ['-break_start']

    def __str__(self):
        return f"{self.break_type} for {self.employee} @ {self.break_start:%Y-%m-%d %H:%M}"


class BiometricDevice(models.Model):
    """Biometric device integration record."""
    DEVICE_TYPES = [
        ('fingerprint', 'Fingerprint'), ('face', 'Face Recognition'),
        ('iris', 'Iris'), ('rfid', 'RFID'), ('palm', 'Palm Vein'),
    ]
    STATUS_CHOICES = [('active', 'Active'), ('inactive', 'Inactive'), ('maintenance', 'Maintenance')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='biometric_devices')
    branch = models.ForeignKey('core_hr.Branch', on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='biometric_devices')
    name = models.CharField(max_length=100)
    device_id = models.CharField(max_length=100, help_text='Manufacturer device ID / serial number')
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    location = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active')
    last_sync_at = models.DateTimeField(null=True, blank=True)
    sync_config = models.JSONField(default=dict, help_text='API credentials / polling config')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'biometric_devices'
        unique_together = ['tenant', 'device_id']

    def __str__(self):
        return f"{self.name} ({self.device_type}) — {self.location}"


class FatigueAlert(models.Model):
    """Fatigue and rest-period violation alert."""
    SEVERITY_CHOICES = [('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='fatigue_alerts')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='fatigue_alerts')
    alert_date = models.DateField()
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='medium')
    consecutive_days_worked = models.IntegerField(default=0)
    total_hours_last_7_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    rest_hours_violated = models.DecimalField(max_digits=5, decimal_places=1, default=0,
        help_text='Hours below minimum required rest between shifts')
    rule_violated = models.CharField(max_length=200, blank=True,
        help_text='E.g. "Minimum 11h rest between shifts"')
    recommended_action = models.TextField(blank=True)
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                         null=True, blank=True, related_name='+')
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'fatigue_alerts'
        ordering = ['-alert_date', '-severity']

    def __str__(self):
        return f"Fatigue ({self.severity}): {self.employee} on {self.alert_date}"


class AttendanceAnomaly(models.Model):
    """Attendance anomaly detection record."""
    ANOMALY_TYPES = [
        ('buddy_punching', 'Buddy Punching Suspected'),
        ('location_mismatch', 'Location Mismatch'),
        ('time_fraud', 'Time Fraud Pattern'),
        ('duplicate_punch', 'Duplicate Punch'),
        ('impossible_commute', 'Impossible Commute'),
        ('excessive_breaks', 'Excessive Breaks'),
        ('irregular_pattern', 'Irregular Pattern'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='attendance_anomalies')
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='attendance_anomalies')
    attendance_record = models.ForeignKey(AttendanceRecord, on_delete=models.SET_NULL, null=True, blank=True,
                                           related_name='anomalies')
    anomaly_type = models.CharField(max_length=25, choices=ANOMALY_TYPES)
    detected_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField()
    evidence = models.JSONField(default=dict)
    confidence_score = models.IntegerField(default=50, help_text='0-100 ML confidence')
    is_confirmed = models.BooleanField(default=False)
    is_false_positive = models.BooleanField(default=False)
    investigated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                         null=True, blank=True, related_name='+')
    investigation_notes = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'attendance_anomalies'
        ordering = ['-detected_at']

    def __str__(self):
        return f"{self.anomaly_type}: {self.employee} ({self.detected_at:%Y-%m-%d})"


class AbsenceForecast(models.Model):
    """Absence forecasting snapshot for workforce planning."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='absence_forecasts')
    department = models.ForeignKey('core_hr.Department', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='absence_forecasts')
    forecast_date = models.DateField()
    period_days = models.IntegerField(default=30, help_text='Forecast horizon in days')
    headcount = models.IntegerField(default=0)
    predicted_absent_count = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    predicted_absence_rate_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    historical_absence_rate_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    seasonal_factor = models.DecimalField(max_digits=4, decimal_places=3, default=1,
        help_text='Multiplier e.g. 1.2 = 20% higher than baseline')
    high_risk_employees = models.JSONField(default=list)
    daily_forecast = models.JSONField(default=list,
        help_text='[{"date":"2025-01-01","predicted_absent":3,"confidence":0.8}]')
    model_version = models.CharField(max_length=20, blank=True)
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'absence_forecasts'
        ordering = ['-forecast_date']

    def __str__(self):
        return f"Absence forecast {self.forecast_date} ({self.department or 'all'})"


class OvertimeThreshold(models.Model):
    """Overtime threshold configuration and auto-alert rules."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='overtime_thresholds')
    department = models.ForeignKey('core_hr.Department', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='overtime_thresholds')
    name = models.CharField(max_length=100)
    weekly_soft_limit_hours = models.DecimalField(max_digits=5, decimal_places=1, default=45,
        help_text='Warn manager at this OT level')
    weekly_hard_limit_hours = models.DecimalField(max_digits=5, decimal_places=1, default=60,
        help_text='Block further OT unless overridden')
    monthly_limit_hours = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    alert_manager_on_breach = models.BooleanField(default=True)
    require_manager_override = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'overtime_thresholds'

    def __str__(self):
        return f"OT threshold: {self.name} (soft={self.weekly_soft_limit_hours}h, hard={self.weekly_hard_limit_hours}h)"


class UnionRulePack(models.Model):
    """Union/CBA rule pack that applies to a subset of employees."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='union_rule_packs')
    name = models.CharField(max_length=200)
    union_name = models.CharField(max_length=200, blank=True)
    agreement_reference = models.CharField(max_length=100, blank=True, help_text='CBA reference number')
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    rules = models.JSONField(default=dict,
        help_text='{"min_rest_hours":11,"max_consecutive_days":6,"ot_rate_multiplier":1.5,...}')
    applicable_departments = models.JSONField(default=list)
    applicable_employee_groups = models.JSONField(default=list, help_text='Employment type / grade filters')
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'union_rule_packs'
        ordering = ['-effective_from']

    def __str__(self):
        return f"{self.name} ({self.union_name or 'No union'})"


class SiteAttendanceAnalytics(models.Model):
    """Site/location attendance analytics snapshot."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='site_attendance_analytics')
    branch = models.ForeignKey('core_hr.Branch', on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='attendance_analytics')
    period_date = models.DateField()
    period_type = models.CharField(max_length=10, default='daily',
        choices=[('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly')])
    total_scheduled = models.IntegerField(default=0)
    total_present = models.IntegerField(default=0)
    total_absent = models.IntegerField(default=0)
    total_late = models.IntegerField(default=0)
    total_wfh = models.IntegerField(default=0)
    attendance_rate_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    avg_clock_in_time = models.TimeField(null=True, blank=True)
    avg_working_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    department_breakdown = models.JSONField(default=dict)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'site_attendance_analytics'
        ordering = ['-period_date']

    def __str__(self):
        return f"Analytics {self.period_type} {self.period_date} — {self.branch or 'all sites'}"


class ContractorTimeEntry(models.Model):
    """Contractor/temp worker time tracking entry."""
    STATUS_CHOICES = [
        ('draft', 'Draft'), ('submitted', 'Submitted'), ('approved', 'Approved'),
        ('rejected', 'Rejected'), ('invoiced', 'Invoiced'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='contractor_time_entries')
    contractor_name = models.CharField(max_length=200)
    contractor_company = models.CharField(max_length=200, blank=True)
    employee = models.ForeignKey('core_hr.Employee', on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='contractor_entries',
                                  help_text='Linked Employee record if contractor is also in system')
    work_date = models.DateField()
    hours_worked = models.DecimalField(max_digits=5, decimal_places=2)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    task_description = models.TextField(blank=True)
    department = models.ForeignKey('core_hr.Department', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='+')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='+')
    invoice_reference = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contractor_time_entries'
        ordering = ['-work_date']

    def __str__(self):
        return f"{self.contractor_name} — {self.work_date}: {self.hours_worked}h"


class ShiftCoveragePlan(models.Model):
    """Manager shift coverage planner for anticipated gaps."""
    STATUS_CHOICES = [
        ('planning', 'Planning'), ('ready', 'Ready'), ('partial', 'Partially Covered'),
        ('covered', 'Fully Covered'), ('uncovered', 'Uncovered'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='shift_coverage_plans')
    manager = models.ForeignKey('core_hr.Employee', on_delete=models.CASCADE, related_name='shift_coverage_plans')
    coverage_date = models.DateField()
    shift = models.ForeignKey(ShiftTemplate, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='coverage_plans')
    department = models.ForeignKey('core_hr.Department', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='shift_coverage_plans')
    required_headcount = models.IntegerField(default=1)
    confirmed_headcount = models.IntegerField(default=0)
    gap_count = models.IntegerField(default=0)
    absent_employees = models.JSONField(default=list,
        help_text='Employee IDs confirmed absent/on-leave for this shift')
    cover_assignments = models.JSONField(default=list,
        help_text='[{"employee_id":...,"coverage_type":"voluntary|mandatory|agency"}]')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='planning')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'shift_coverage_plans'
        ordering = ['-coverage_date']

    def __str__(self):
        return f"Coverage {self.coverage_date} {self.shift or ''} — {self.status}"
