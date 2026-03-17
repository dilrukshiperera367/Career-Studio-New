"""
MarketplaceOS — apps.payments

Payments, Billing & Payouts.

Models:
    Payment              — A single payment transaction (booking purchase, subscription, etc.)
    Payout              — Provider payout record
    PayoutLineItem      — Individual earnings that make up a payout
    PromoCode           — Discount / promo code
    PromoCodeUsage      — Tracks each redemption of a promo code
    Wallet              — Buyer credit wallet
    WalletTransaction   — Wallet deposit / spend / refund
    Invoice             — Platform-generated invoice record
    RefundRequest       — Buyer-initiated refund request
    TaxDocument         — Provider tax document collection (e.g. W9/W8, business reg)
"""
import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings


class Payment(models.Model):
    """
    Single payment transaction — one booking purchase, subscription renewal, etc.
    Covers Stripe, PayHere, wallet/credit, and enterprise billing flows.
    """

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"
        PARTIALLY_REFUNDED = "partial_refund", "Partially Refunded"
        DISPUTED = "disputed", "Disputed"
        CANCELLED = "cancelled", "Cancelled"

    class PaymentMethod(models.TextChoices):
        CARD = "card", "Credit / Debit Card"
        PAYHERE = "payhere", "PayHere"
        WALLET = "wallet", "Platform Wallet / Credits"
        ENTERPRISE_BUDGET = "enterprise_budget", "Enterprise Budget"
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"
        PROMO_COVERED = "promo_covered", "Fully Covered by Promo"

    class PaymentType(models.TextChoices):
        BOOKING = "booking", "Session Booking"
        PACKAGE = "package", "Service Package"
        SUBSCRIPTION = "subscription", "Provider Subscription"
        COURSE = "course", "Course Enrollment"
        ASSESSMENT = "assessment", "Assessment Order"
        WALLET_TOPUP = "wallet_topup", "Wallet Top-up"
        ENTERPRISE_TOPUP = "enterprise_topup", "Enterprise Budget Top-up"
        VERIFICATION_FEE = "verification_fee", "Provider Verification Fee"
        FEATURED_LISTING = "featured_listing", "Featured Listing"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=30, unique=True, db_index=True)
    payer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payments",
    )
    booking = models.OneToOneField(
        "bookings.Booking", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="payment",
    )

    payment_type = models.CharField(max_length=25, choices=PaymentType.choices)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)

    # Amounts
    gross_amount_lkr = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount_lkr = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    net_amount_lkr = models.DecimalField(max_digits=10, decimal_places=2)
    platform_commission_lkr = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    provider_earnings_lkr = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=5, default="LKR")

    # Gateway references
    stripe_payment_intent_id = models.CharField(max_length=200, blank=True, default="")
    payhere_order_id = models.CharField(max_length=200, blank=True, default="")
    gateway_response = models.JSONField(default=dict, blank=True)

    # Promo
    promo_code = models.ForeignKey(
        "PromoCode", on_delete=models.SET_NULL, null=True, blank=True, related_name="payments",
    )

    # Enterprise
    enterprise_account = models.ForeignKey(
        "enterprise_marketplace.EnterpriseAccount", on_delete=models.SET_NULL,
        null=True, blank=True,
    )

    # Metadata
    notes = models.TextField(blank=True, default="")
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.CharField(max_length=500, blank=True, default="")
    risk_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    is_flagged = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mp_payment"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["payer", "status"]),
            models.Index(fields=["status", "payment_type"]),
        ]

    def __str__(self):
        return f"{self.reference} — {self.net_amount_lkr} LKR ({self.status})"

    def save(self, *args, **kwargs):
        if not self.reference:
            import random, string
            self.reference = "PAY-" + "".join(random.choices(string.digits + string.ascii_uppercase, k=10))
        super().save(*args, **kwargs)


class Payout(models.Model):
    """
    Provider payout batch record.
    Aggregates multiple earned amounts into a single bank/wallet transfer.
    """

    class PayoutStatus(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        ON_HOLD = "on_hold", "On Hold"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=30, unique=True)
    provider = models.ForeignKey(
        "providers.Provider", on_delete=models.PROTECT, related_name="payouts",
    )
    status = models.CharField(max_length=15, choices=PayoutStatus.choices, default=PayoutStatus.SCHEDULED)
    gross_amount_lkr = models.DecimalField(max_digits=12, decimal_places=2)
    platform_fee_lkr = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    net_amount_lkr = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=5, default="LKR")
    payout_method = models.CharField(max_length=50, blank=True, default="")
    bank_reference = models.CharField(max_length=200, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    period_start = models.DateField()
    period_end = models.DateField()
    scheduled_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_payout"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reference} — {self.provider} — {self.net_amount_lkr} LKR"

    def save(self, *args, **kwargs):
        if not self.reference:
            import random, string
            self.reference = "OUT-" + "".join(random.choices(string.digits, k=8))
        super().save(*args, **kwargs)


class PayoutLineItem(models.Model):
    """Individual earning that contributes to a payout batch."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payout = models.ForeignKey(Payout, on_delete=models.CASCADE, related_name="line_items")
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="payout_lines")
    description = models.CharField(max_length=300)
    gross_lkr = models.DecimalField(max_digits=10, decimal_places=2)
    commission_lkr = models.DecimalField(max_digits=10, decimal_places=2)
    net_lkr = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "mp_payout_line_item"

    def __str__(self):
        return f"{self.description} — {self.net_lkr} LKR"


class PromoCode(models.Model):
    """Promotional / discount code issued by the platform or a provider."""

    class DiscountType(models.TextChoices):
        PERCENT = "percent", "Percentage Discount"
        FIXED = "fixed", "Fixed Amount Discount"
        FREE = "free", "Fully Free"

    class PromoScope(models.TextChoices):
        PLATFORM_WIDE = "platform", "Platform Wide"
        CATEGORY = "category", "Category"
        PROVIDER = "provider", "Specific Provider"
        SERVICE = "service", "Specific Service"
        ENTERPRISE = "enterprise", "Enterprise Only"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.CharField(max_length=300, blank=True, default="")
    discount_type = models.CharField(max_length=10, choices=DiscountType.choices)
    discount_value = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    max_discount_lkr = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Cap on discount amount for percentage codes.",
    )
    scope = models.CharField(max_length=15, choices=PromoScope.choices, default=PromoScope.PLATFORM_WIDE)
    provider = models.ForeignKey(
        "providers.Provider", on_delete=models.SET_NULL, null=True, blank=True,
    )
    service = models.ForeignKey(
        "services_catalog.Service", on_delete=models.SET_NULL, null=True, blank=True,
    )
    enterprise = models.ForeignKey(
        "enterprise_marketplace.EnterpriseAccount", on_delete=models.SET_NULL, null=True, blank=True,
    )
    min_order_lkr = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    max_uses = models.IntegerField(null=True, blank=True, help_text="Null = unlimited.")
    uses_per_user = models.IntegerField(default=1)
    total_used = models.IntegerField(default=0)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_promo_code"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.code} ({self.discount_type} {self.discount_value})"


class PromoCodeUsage(models.Model):
    """Records each time a promo code is used."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promo_code = models.ForeignKey(PromoCode, on_delete=models.CASCADE, related_name="usages")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)
    discount_applied_lkr = models.DecimalField(max_digits=10, decimal_places=2)
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_promo_usage"

    def __str__(self):
        return f"{self.user} used {self.promo_code.code}"


class Wallet(models.Model):
    """Buyer credit/gift wallet on the platform."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet")
    balance_lkr = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=5, default="LKR")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mp_wallet"

    def __str__(self):
        return f"Wallet for {self.user.email} — {self.balance_lkr} LKR"


class WalletTransaction(models.Model):
    """Credit/debit ledger for a buyer wallet."""

    class TransactionType(models.TextChoices):
        TOPUP = "topup", "Top-Up"
        SPEND = "spend", "Spend (Purchase)"
        REFUND = "refund", "Refund"
        GIFT = "gift", "Gift Credit"
        ENTERPRISE_GRANT = "enterprise_grant", "Enterprise Grant"
        EXPIRY = "expiry", "Expiry"
        ADJUSTMENT = "adjustment", "Manual Adjustment"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transactions")
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    amount_lkr = models.DecimalField(max_digits=10, decimal_places=2)
    balance_after_lkr = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=300, blank=True, default="")
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_wallet_transaction"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.transaction_type} {self.amount_lkr} LKR — {self.wallet}"


class Invoice(models.Model):
    """Platform-generated invoice for a payment."""

    class InvoiceStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        ISSUED = "issued", "Issued"
        PAID = "paid", "Paid"
        VOID = "void", "Void"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice_number = models.CharField(max_length=30, unique=True)
    payment = models.OneToOneField(Payment, on_delete=models.PROTECT, related_name="invoice")
    issued_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    status = models.CharField(max_length=10, choices=InvoiceStatus.choices, default=InvoiceStatus.ISSUED)
    line_items = models.JSONField(default=list)
    subtotal_lkr = models.DecimalField(max_digits=10, decimal_places=2)
    tax_lkr = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_lkr = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=5, default="LKR")
    issued_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "mp_invoice"
        ordering = ["-issued_at"]

    def __str__(self):
        return f"Invoice {self.invoice_number} — {self.total_lkr} LKR"


class RefundRequest(models.Model):
    """Buyer-initiated refund request on a payment."""

    class RefundStatus(models.TextChoices):
        PENDING = "pending", "Pending Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        PROCESSED = "processed", "Processed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="refund_requests")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    reason = models.TextField()
    requested_amount_lkr = models.DecimalField(max_digits=10, decimal_places=2)
    approved_amount_lkr = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=15, choices=RefundStatus.choices, default=RefundStatus.PENDING)
    admin_notes = models.TextField(blank=True, default="")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reviewed_refunds",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_refund_request"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Refund {self.status} — {self.payment.reference}"


class TaxDocument(models.Model):
    """Provider tax document collection for payouts (W9, W8, business registration, etc.)."""

    class DocType(models.TextChoices):
        W9 = "w9", "W-9 (US Resident)"
        W8 = "w8", "W-8 (Non-US)"
        BUSINESS_REG = "business_reg", "Business Registration"
        VAT_REG = "vat_reg", "VAT Registration"
        ID_PROOF = "id_proof", "Identity Proof"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        "providers.Provider", on_delete=models.CASCADE, related_name="tax_documents",
    )
    doc_type = models.CharField(max_length=15, choices=DocType.choices)
    file_url = models.URLField()
    tax_id = models.CharField(max_length=100, blank=True, default="",
                               help_text="Encrypted tax identification number.")
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "mp_tax_document"

    def __str__(self):
        return f"{self.provider} — {self.doc_type}"
