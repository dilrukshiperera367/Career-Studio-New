"""Payments app — Subscriptions, invoices, payment integrations."""
import uuid
from django.db import models
from django.conf import settings


class SubscriptionPlan(models.Model):
    """Available subscription plans for employers."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)
    tier = models.CharField(max_length=15, choices=[
        ("free", "Free"), ("starter", "Starter"), ("professional", "Professional"),
        ("enterprise", "Enterprise"), ("agency", "Agency"),
    ])
    price_lkr = models.DecimalField(max_digits=10, decimal_places=2)
    price_usd = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    billing_period = models.CharField(max_length=10, choices=[("monthly", "Monthly"), ("annual", "Annual")])
    monthly_job_limit = models.IntegerField(default=3)
    resume_db_access = models.BooleanField(default=False)
    featured_jobs = models.IntegerField(default=0)
    analytics_access = models.BooleanField(default=False)
    ats_integration = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    features = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_subscription_plans"

    def __str__(self):
        return f"{self.name} ({self.billing_period})"


class Subscription(models.Model):
    """Active subscription for an employer."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past Due"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"
        TRIAL = "trial", "Trial"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    cancelled_at = models.DateTimeField(null=True, blank=True)
    payment_gateway = models.CharField(max_length=20, choices=[
        ("payhere", "PayHere"), ("stripe", "Stripe"), ("manual", "Manual"),
    ])
    gateway_subscription_id = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_subscriptions"


class Invoice(models.Model):
    """Payment invoices."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE, related_name="invoices")
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True)
    invoice_number = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="LKR")
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    payment_gateway = models.CharField(max_length=20, blank=True, default="")
    gateway_payment_id = models.CharField(max_length=200, blank=True, default="")
    paid_at = models.DateTimeField(null=True, blank=True)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_invoices"
        ordering = ["-created_at"]
