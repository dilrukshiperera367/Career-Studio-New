"""
MarketplaceOS — apps.assessment_marketplace

Assessment Marketplace — assessment vendors, test catalog, ordering,
delivery, result ingestion.  Integrates with TalentOS and CareerOS.

Models:
    AssessmentVendor    — Assessment provider / testing company
    AssessmentProduct   — Individual assessment / test product
    AssessmentRoleMap   — Maps assessments to job roles
    AssessmentOrder     — Buyer/employer purchase of an assessment
    AssessmentDelivery  — Delivery record of a specific assessment
    AssessmentResult    — Normalized result ingestion from vendor
"""
import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings


class AssessmentVendor(models.Model):
    """Registered assessment vendor on the marketplace."""

    class VendorStatus(models.TextChoices):
        PENDING = "pending", "Pending Approval"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.OneToOneField(
        "providers.Provider", on_delete=models.CASCADE, related_name="assessment_vendor",
    )
    vendor_name = models.CharField(max_length=200)
    website = models.URLField(blank=True, default="")
    description = models.TextField(blank=True, default="")
    specialties = models.JSONField(default=list,
                                    help_text="e.g. ['technical', 'aptitude', 'personality', 'language']")
    supported_languages = models.JSONField(default=list)
    api_integration = models.BooleanField(default=False,
                                           help_text="True if delivery is via API integration.")
    api_endpoint = models.URLField(blank=True, default="")
    status = models.CharField(max_length=15, choices=VendorStatus.choices, default=VendorStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_assessment_vendor"
        ordering = ["vendor_name"]

    def __str__(self):
        return self.vendor_name


class AssessmentProduct(models.Model):
    """Individual assessment/test product in the marketplace catalog."""

    class AssessmentCategory(models.TextChoices):
        TECHNICAL = "technical", "Technical Skills"
        APTITUDE = "aptitude", "Aptitude / Cognitive"
        PERSONALITY = "personality", "Personality"
        LANGUAGE = "language", "Language Proficiency"
        LEADERSHIP = "leadership", "Leadership / Management"
        SOFT_SKILLS = "soft_skills", "Soft Skills"
        DOMAIN = "domain", "Domain / Industry Knowledge"
        CODING = "coding", "Coding / Programming"
        CERTIFICATION = "certification", "Certification-Linked"
        SITUATIONAL = "situational", "Situational Judgement"

    class DeliveryFormat(models.TextChoices):
        ONLINE_PROCTORED = "online_proctored", "Online Proctored"
        ONLINE_UNPROCTORED = "online_unproctored", "Online Unproctored"
        IN_PERSON = "in_person", "In-Person Testing"
        API_EMBEDDED = "api_embedded", "API-Embedded"

    class PricingModel(models.TextChoices):
        PER_SEAT = "per_seat", "Per Seat"
        PER_TEST = "per_test", "Per Test"
        BUNDLE = "bundle", "Bundle"
        SUBSCRIPTION = "subscription", "Subscription"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(AssessmentVendor, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=300)
    slug = models.SlugField(max_length=300)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=AssessmentCategory.choices)
    delivery_format = models.CharField(max_length=25, choices=DeliveryFormat.choices)
    pricing_model = models.CharField(max_length=15, choices=PricingModel.choices, default=PricingModel.PER_SEAT)
    price_per_unit_lkr = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=5, default="LKR")
    duration_minutes = models.IntegerField(null=True, blank=True)
    question_count = models.IntegerField(null=True, blank=True)
    supported_languages = models.JSONField(default=list)
    skills_measured = models.JSONField(default=list)
    validity_days = models.IntegerField(
        null=True, blank=True,
        help_text="How many days the result is valid for hiring purposes.",
    )
    has_candidate_feedback = models.BooleanField(default=False)
    has_fraud_detection = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_assessment_product"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} — {self.vendor.vendor_name}"


class AssessmentRoleMap(models.Model):
    """Maps assessment products to job roles for smart recommendations."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(AssessmentProduct, on_delete=models.CASCADE, related_name="role_maps")
    job_role = models.CharField(max_length=200)
    industry = models.CharField(max_length=100, blank=True, default="")
    relevance_score = models.IntegerField(default=5, help_text="1–10 relevance for this role.")

    class Meta:
        db_table = "mp_assessment_role_map"
        unique_together = [["assessment", "job_role"]]

    def __str__(self):
        return f"{self.assessment.name} → {self.job_role}"


class AssessmentOrder(models.Model):
    """
    Buyer (individual or enterprise) orders one or more assessments.
    Can be ordered for a specific candidate (TalentOS flow) or self-assessment (CareerOS flow).
    """

    class OrderStatus(models.TextChoices):
        PENDING = "pending", "Pending Payment"
        PAID = "paid", "Paid — Awaiting Delivery"
        IN_DELIVERY = "in_delivery", "In Delivery"
        COMPLETED = "completed", "Completed"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=20, unique=True)
    purchased_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="assessment_orders",
    )
    assessment = models.ForeignKey(AssessmentProduct, on_delete=models.PROTECT, related_name="orders")
    quantity = models.IntegerField(default=1)
    unit_price_lkr = models.DecimalField(max_digits=10, decimal_places=2)
    total_price_lkr = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=5, default="LKR")
    payment = models.ForeignKey(
        "payments.Payment", on_delete=models.SET_NULL, null=True, blank=True,
    )
    enterprise_account = models.ForeignKey(
        "enterprise_marketplace.EnterpriseAccount", on_delete=models.SET_NULL, null=True, blank=True,
    )
    status = models.CharField(max_length=15, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mp_assessment_order"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order {self.reference} — {self.assessment.name}"

    def save(self, *args, **kwargs):
        if not self.reference:
            import random, string
            self.reference = "ASS-" + "".join(random.choices(string.digits, k=8))
        super().save(*args, **kwargs)


class AssessmentDelivery(models.Model):
    """Individual assessment delivery to a specific candidate."""

    class DeliveryStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Invite Sent"
        STARTED = "started", "Started"
        SUBMITTED = "submitted", "Submitted"
        GRADED = "graded", "Graded"
        EXPIRED = "expired", "Expired"
        VOIDED = "voided", "Voided (Fraud)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(AssessmentOrder, on_delete=models.CASCADE, related_name="deliveries")
    candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="assessment_deliveries",
    )
    candidate_email = models.EmailField()
    status = models.CharField(max_length=15, choices=DeliveryStatus.choices, default=DeliveryStatus.PENDING)
    vendor_candidate_id = models.CharField(max_length=200, blank=True, default="")
    invite_link = models.URLField(blank=True, default="")
    invite_sent_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_fraud_flagged = models.BooleanField(default=False)
    fraud_flag_reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_assessment_delivery"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Delivery to {self.candidate_email} — {self.status}"


class AssessmentResult(models.Model):
    """Normalized result ingested from the assessment vendor after completion."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    delivery = models.OneToOneField(AssessmentDelivery, on_delete=models.CASCADE, related_name="result")
    raw_score = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    normalized_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                            help_text="Normalized 0–100 score.")
    percentile = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    band = models.CharField(max_length=50, blank=True, default="",
                             help_text="e.g. Proficient, Developing, Expert")
    dimension_scores = models.JSONField(default=dict,
                                         help_text="Breakdown by skill dimension.")
    passed = models.BooleanField(null=True, blank=True)
    report_url = models.URLField(blank=True, default="")
    candidate_report_url = models.URLField(blank=True, default="",
                                            help_text="Candidate-visible feedback report.")
    is_visible_to_candidate = models.BooleanField(default=True)
    validity_expires_at = models.DateField(null=True, blank=True)
    vendor_result_ref = models.CharField(max_length=200, blank=True, default="")
    ingested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mp_assessment_result"

    def __str__(self):
        return f"Result for {self.delivery} — {self.normalized_score}"
