"""
Finance Operations models.
Rate cards, invoicing, credit notes, gross margin tracking,
perm fee rules, revenue recognition, DSO dashboards, client profitability.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class ClientInvoice(models.Model):
    """An invoice issued to a client for placements, contractor billing, or fees."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        PARTIAL = "partial", "Partially Paid"
        PAID = "paid", "Paid"
        OVERDUE = "overdue", "Overdue"
        DISPUTED = "disputed", "Disputed"
        VOID = "void", "Void"
        WRITTEN_OFF = "written_off", "Written Off"

    class InvoiceType(models.TextChoices):
        PERM_FEE = "perm_fee", "Permanent Placement Fee"
        CONTRACT_BILLING = "contract_billing", "Contract / Temp Billing"
        RETAINER = "retainer", "Retainer Fee"
        MILESTONE = "milestone", "Milestone Payment"
        REBATE = "rebate", "Rebate / Credit"
        EXPENSE_REIMBURSEMENT = "expense_reimbursement", "Expense Reimbursement"
        MANAGEMENT_FEE = "management_fee", "Management Fee"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="client_invoices"
    )
    client_account = models.ForeignKey(
        "agency_crm.ClientAccount",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="invoices",
    )
    invoice_number = models.CharField(max_length=50, unique=True)
    invoice_type = models.CharField(max_length=30, choices=InvoiceType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    # Period
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    invoice_date = models.DateField()
    due_date = models.DateField()
    # Amounts
    currency = models.CharField(max_length=10, default="USD")
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    balance_due = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    # Reference
    po_number = models.CharField(max_length=100, blank=True)
    payment_terms = models.CharField(max_length=100, blank=True)  # e.g., "Net 30"
    bank_details = models.TextField(blank=True)
    # Tracking
    sent_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    last_chased_at = models.DateTimeField(null=True, blank=True)
    # Created by
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_invoices"
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "fin_client_invoice"
        ordering = ["-invoice_date"]

    def __str__(self):
        return f"INV#{self.invoice_number} – {self.client_account} ({self.total} {self.currency})"


class InvoiceLineItem(models.Model):
    """A line item on a client invoice."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(
        ClientInvoice, on_delete=models.CASCADE, related_name="line_items"
    )
    description = models.CharField(max_length=300)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    # Links
    assignment = models.ForeignKey(
        "contractor_ops.Assignment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="invoice_lines",
    )
    timesheet = models.ForeignKey(
        "timesheets.Timesheet",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="invoice_lines",
    )
    placement = models.ForeignKey(
        "agencies.AgencyPlacement",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="invoice_lines",
    )

    class Meta:
        db_table = "fin_invoice_line"

    def save(self, *args, **kwargs):
        self.amount = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class CreditNote(models.Model):
    """A credit note against a previously issued invoice (rebate, replacement, dispute)."""

    class Reason(models.TextChoices):
        REBATE = "rebate", "Rebate"
        REPLACEMENT = "replacement", "Replacement Guarantee"
        DISPUTE = "dispute", "Client Dispute"
        ERROR = "error", "Invoice Error"
        GOODWILL = "goodwill", "Goodwill"
        EARLY_TERMINATION = "early_termination", "Early Termination"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="credit_notes"
    )
    original_invoice = models.ForeignKey(
        ClientInvoice, on_delete=models.CASCADE, related_name="credit_notes"
    )
    credit_note_number = models.CharField(max_length=50, unique=True)
    reason = models.CharField(max_length=30, choices=Reason.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")
    issued_date = models.DateField()
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_credit_notes"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "fin_credit_note"
        ordering = ["-issued_date"]

    def __str__(self):
        return f"CN#{self.credit_note_number} – {self.amount} {self.currency}"


class PaymentRecord(models.Model):
    """Payment received against an invoice."""

    class PaymentMethod(models.TextChoices):
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"
        CHECK = "check", "Check"
        CARD = "card", "Card"
        ACH = "ach", "ACH"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(
        ClientInvoice, on_delete=models.CASCADE, related_name="payments"
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")
    payment_date = models.DateField()
    payment_method = models.CharField(
        max_length=30, choices=PaymentMethod.choices, default=PaymentMethod.BANK_TRANSFER
    )
    reference = models.CharField(max_length=200, blank=True)
    recorded_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="recorded_payments"
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "fin_payment"
        ordering = ["-payment_date"]

    def __str__(self):
        return f"Payment {self.amount} {self.currency} on {self.payment_date}"


class MarginRecord(models.Model):
    """
    Snapshot of gross margin for an assignment period or perm placement.
    Used for desk/client/recruiter profitability analytics.
    """

    class RecordType(models.TextChoices):
        CONTRACT = "contract", "Contract Spread"
        PERM = "perm", "Perm Fee"
        RETAINER = "retainer", "Retainer"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(
        "agencies.Agency", on_delete=models.CASCADE, related_name="margin_records"
    )
    record_type = models.CharField(max_length=20, choices=RecordType.choices)
    client_account = models.ForeignKey(
        "agency_crm.ClientAccount",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="margins",
    )
    assignment = models.ForeignKey(
        "contractor_ops.Assignment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="margins",
    )
    placement = models.ForeignKey(
        "agencies.AgencyPlacement",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="margins",
    )
    recruiter = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="margin_records"
    )
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    currency = models.CharField(max_length=10, default="USD")
    gross_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    direct_costs = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    gross_margin = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    margin_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "fin_margin_record"
        ordering = ["-period_start"]

    def save(self, *args, **kwargs):
        self.gross_margin = self.gross_revenue - self.direct_costs
        if self.gross_revenue > 0:
            self.margin_pct = (self.gross_margin / self.gross_revenue) * 100
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_record_type_display()} margin: {self.gross_margin} {self.currency}"
