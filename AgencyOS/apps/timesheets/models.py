"""
Timesheets app models.
Worker timesheet entry, client/supervisor approval, overtime,
expenses, shift differentials, payroll/billing export, locked periods.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class TimesheetPeriod(models.Model):
    """
    A billing/payroll period (week, bi-week, or month).
    Can be locked to prevent further edits.
    """

    class PeriodType(models.TextChoices):
        WEEKLY = "weekly", "Weekly"
        BIWEEKLY = "biweekly", "Bi-Weekly"
        MONTHLY = "monthly", "Monthly"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="timesheet_periods"
    )
    period_type = models.CharField(
        max_length=20, choices=PeriodType.choices, default=PeriodType.WEEKLY
    )
    start_date = models.DateField()
    end_date = models.DateField()
    is_locked = models.BooleanField(default=False)
    locked_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="locked_periods"
    )
    locked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ts_period"
        unique_together = [["agency", "start_date", "end_date"]]
        ordering = ["-start_date"]

    def __str__(self):
        return f"Period {self.start_date} – {self.end_date}"


class Timesheet(models.Model):
    """
    A contractor's timesheet for a given period and assignment.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        SUPERVISOR_APPROVED = "supervisor_approved", "Supervisor Approved"
        CLIENT_APPROVED = "client_approved", "Client Approved"
        REJECTED = "rejected", "Rejected"
        LOCKED = "locked", "Locked"
        EXPORTED = "exported", "Exported to Payroll"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="timesheets"
    )
    assignment = models.ForeignKey(
        "contractor_ops.Assignment", on_delete=models.CASCADE, related_name="timesheets"
    )
    period = models.ForeignKey(
        TimesheetPeriod, on_delete=models.CASCADE, related_name="timesheets"
    )
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT)
    # Hours
    regular_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    overtime_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    double_time_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    shift_differential_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    total_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    # Rates (captured at timesheet creation)
    pay_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    bill_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    overtime_pay_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    overtime_bill_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, default="USD")
    # Computed amounts
    gross_pay = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    gross_bill = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    gross_margin = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    # Approval
    submitted_at = models.DateTimeField(null=True, blank=True)
    supervisor_approved_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="sup_approved_ts"
    )
    supervisor_approved_at = models.DateTimeField(null=True, blank=True)
    client_approved_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="client_approved_ts"
    )
    client_approved_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="rejected_ts"
    )
    rejection_reason = models.TextField(blank=True)
    # Export
    payroll_exported_at = models.DateTimeField(null=True, blank=True)
    billing_exported_at = models.DateTimeField(null=True, blank=True)
    payroll_reference = models.CharField(max_length=100, blank=True)
    billing_reference = models.CharField(max_length=100, blank=True)
    # Notes
    worker_notes = models.TextField(blank=True)
    approver_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ts_timesheet"
        unique_together = [["assignment", "period"]]
        ordering = ["-period__start_date"]

    def __str__(self):
        return f"Timesheet {self.assignment} – {self.period}"

    def compute_totals(self):
        """Compute gross pay, bill, and margin from rates and hours."""
        if self.pay_rate:
            reg_pay = self.regular_hours * self.pay_rate
            ot_pay = self.overtime_hours * (self.overtime_pay_rate or self.pay_rate * 1.5)
            self.gross_pay = reg_pay + ot_pay
        if self.bill_rate:
            reg_bill = self.regular_hours * self.bill_rate
            ot_bill = self.overtime_hours * (self.overtime_bill_rate or self.bill_rate * 1.5)
            self.gross_bill = reg_bill + ot_bill
        if self.gross_bill and self.gross_pay:
            self.gross_margin = self.gross_bill - self.gross_pay


class TimesheetEntry(models.Model):
    """Day-level timesheet entry within a timesheet."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timesheet = models.ForeignKey(
        Timesheet, on_delete=models.CASCADE, related_name="entries"
    )
    work_date = models.DateField()
    regular_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    overtime_hours = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    shift_differential = models.BooleanField(default=False)
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = "ts_entry"
        unique_together = [["timesheet", "work_date"]]
        ordering = ["work_date"]

    def __str__(self):
        return f"{self.work_date}: {self.regular_hours}h regular, {self.overtime_hours}h OT"


class ExpenseReport(models.Model):
    """Expense report submitted alongside or separate from a timesheet."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        INVOICED = "invoiced", "Invoiced"
        PAID = "paid", "Paid"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="expense_reports"
    )
    assignment = models.ForeignKey(
        "contractor_ops.Assignment", on_delete=models.CASCADE, related_name="expenses"
    )
    timesheet = models.ForeignKey(
        Timesheet, null=True, blank=True, on_delete=models.SET_NULL, related_name="expenses"
    )
    period = models.ForeignKey(
        TimesheetPeriod, null=True, blank=True, on_delete=models.SET_NULL, related_name="expenses"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default="USD")
    is_invoiceable = models.BooleanField(default=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_expenses"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ts_expense_report"

    def __str__(self):
        return f"Expenses – {self.assignment} ({self.total_amount} {self.currency})"


class ExpenseLineItem(models.Model):
    """A single expense line within an expense report."""

    class ExpenseCategory(models.TextChoices):
        TRAVEL = "travel", "Travel"
        MILEAGE = "mileage", "Mileage"
        ACCOMMODATION = "accommodation", "Accommodation"
        MEALS = "meals", "Meals & Entertainment"
        EQUIPMENT = "equipment", "Equipment"
        COMMUNICATION = "communication", "Communication"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    expense_report = models.ForeignKey(
        ExpenseReport, on_delete=models.CASCADE, related_name="line_items"
    )
    category = models.CharField(max_length=30, choices=ExpenseCategory.choices)
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")
    expense_date = models.DateField()
    receipt_url = models.URLField(blank=True)
    mileage_km = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    is_invoiceable = models.BooleanField(default=True)

    class Meta:
        db_table = "ts_expense_line"

    def __str__(self):
        return f"{self.get_category_display()}: {self.amount} {self.currency}"
