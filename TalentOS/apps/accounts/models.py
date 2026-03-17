"""Accounts app — Users, Roles, Permissions."""

import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model with tenant affiliation."""

    USER_TYPE_CHOICES = [
        ("company_admin", "Company Admin"),
        ("recruiter", "Recruiter"),
        ("hiring_manager", "Hiring Manager"),
        ("candidate", "Candidate"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="users",
        null=True, blank=True,  # null for candidates and superadmins
    )
    user_type = models.CharField(
        max_length=20, choices=USER_TYPE_CHOICES, default="candidate",
    )
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    # MFA (TOTP)
    mfa_enabled = models.BooleanField(default=False)
    mfa_secret = models.CharField(max_length=64, blank=True, default="")
    # Email verification (#17)
    email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        db_table = "users"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"


class Role(models.Model):
    """Role definition (Admin, Recruiter, Hiring Manager, Interviewer)."""

    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("recruiter", "Recruiter"),
        ("hiring_manager", "Hiring Manager"),
        ("interviewer", "Interviewer"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="roles",
    )
    name = models.CharField(max_length=50, choices=ROLE_CHOICES)
    permissions = models.JSONField(default=list, help_text="List of permission strings")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "roles"
        unique_together = [("tenant", "name")]

    def __str__(self):
        return f"{self.name} ({self.tenant.name})"


class UserRole(models.Model):
    """Many-to-many: user ↔ role."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_roles")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="user_roles")
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_roles"
        unique_together = [("user", "role")]

    def __str__(self):
        return f"{self.user.email} → {self.role.name}"


# ---------------------------------------------------------------------------
# Permission constants (referenced by RBAC checks)
# ---------------------------------------------------------------------------

PERMISSIONS = {
    "admin": [
        "tenants.manage", "users.manage", "jobs.create", "jobs.edit", "jobs.delete",
        "jobs.view_all", "candidates.view_all", "candidates.edit",
        "applications.view_all", "applications.move_stage", "applications.reject",
        "evaluations.submit", "evaluations.view_all",
        "messages.send", "messages.view_all",
        "templates.manage", "integrations.manage", "analytics.view_all",
    ],
    "recruiter": [
        "jobs.create", "jobs.edit", "jobs.view_all",
        "candidates.view_all", "candidates.edit",
        "applications.view_all", "applications.move_stage", "applications.reject",
        "evaluations.submit", "evaluations.view_all",
        "messages.send", "messages.view_all",
        "analytics.view_all",
    ],
    "hiring_manager": [
        "jobs.view_own", "candidates.view_own", "applications.view_own",
        "applications.move_stage_own", "evaluations.submit", "evaluations.view_own",
        "messages.send", "messages.view_own", "analytics.view_own",
    ],
    "interviewer": [
        "evaluations.submit", "evaluations.view_own",
    ],
}


class Notification(models.Model):
    """In-app notification for user — bell icon in nav."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="notifications")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=50,
        help_text="new_applicant, interview_scheduled, feedback_submitted, offer_decision, "
        "mention, task_assigned, sla_warning, system")
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, default="")
    entity_type = models.CharField(max_length=50, blank=True, default="")
    entity_id = models.UUIDField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "created_at"]),
        ]

    def __str__(self):
        return f"[{'✓' if self.is_read else '●'}] {self.title}"


class UserNotificationPreference(models.Model):
    """Per-user notification preferences — which events and channels."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notification_preferences")
    event_type = models.CharField(max_length=50,
        help_text="new_applicant, interview_scheduled, feedback_submitted, offer_decision, etc.")
    email_enabled = models.BooleanField(default=True)
    in_app_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_notification_preferences"
        unique_together = [("user", "event_type")]

    def __str__(self):
        return f"{self.user.email}: {self.event_type}"


# ---------------------------------------------------------------------------
# Password reset tokens
# ---------------------------------------------------------------------------

class PasswordResetToken(models.Model):
    """Secure one-use token for password reset flow."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_reset_tokens")
    token = models.CharField(max_length=128, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        db_table = "password_reset_tokens"

    def __str__(self):
        return f"PasswordResetToken({self.user.email})"


# ---------------------------------------------------------------------------
# Email verification tokens  (#17)
# ---------------------------------------------------------------------------

class EmailVerificationToken(models.Model):
    """One-use token to verify a user's email address after registration."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="email_verification_tokens")
    token = models.CharField(max_length=128, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        db_table = "email_verification_tokens"

    def __str__(self):
        return f"EmailVerificationToken({self.user.email})"


class InviteToken(models.Model):
    """Invitation token for new team members."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="invites")
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="sent_invites")
    email = models.EmailField()
    user_type = models.CharField(max_length=20, default="recruiter")
    token = models.CharField(max_length=128, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "invite_tokens"
        unique_together = [("tenant", "email")]

    def __str__(self):
        return f"Invite({self.email} → {self.tenant.name})"


# ---------------------------------------------------------------------------
# Subscription / Billing models (SaaS plan management)
# ---------------------------------------------------------------------------

from django.utils import timezone  # noqa: E402 — needed here for model methods
from datetime import timedelta  # noqa: E402


class Plan(models.Model):
    """SaaS plan definition."""
    TIER_CHOICES = [
        ('free_trial', 'Free Trial'),
        ('starter', 'Starter'),
        ('professional', 'Professional'),
        ('enterprise', 'Enterprise'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    tier = models.CharField(max_length=30, choices=TIER_CHOICES, unique=True)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_annually = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_jobs = models.IntegerField(default=5)
    max_candidates = models.IntegerField(default=100)
    max_users = models.IntegerField(default=3)
    features = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "plans"
        ordering = ['price_monthly']

    def __str__(self):
        return self.name


class Subscription(models.Model):
    """Tenant subscription and trial tracking."""
    STATUS_CHOICES = [
        ('trialing', 'Trialing'),
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('canceled', 'Canceled'),
        ('expired', 'Expired'),
        ('grace_period', 'Grace Period'),
    ]
    BILLING_CYCLE = [('monthly', 'Monthly'), ('annually', 'Annually')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(
        'tenants.Tenant', on_delete=models.CASCADE, related_name='subscription',
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trialing')
    billing_cycle = models.CharField(max_length=10, choices=BILLING_CYCLE, default='monthly')

    # Trial
    trial_start = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    trial_days = models.IntegerField(default=14)

    # Stripe
    stripe_customer_id = models.CharField(max_length=100, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True)

    # Billing dates
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)

    # Grace period (3 days after expiry)
    grace_period_end = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "subscriptions"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.tenant} - {self.status}"

    @property
    def is_active(self):
        return self.status in ('trialing', 'active', 'grace_period')

    @property
    def trial_days_remaining(self):
        if self.status == 'trialing' and self.trial_end:
            delta = self.trial_end - timezone.now()
            return max(0, delta.days)
        return 0

    @property
    def in_grace_period(self):
        return (
            self.status == 'grace_period'
            and self.grace_period_end is not None
            and timezone.now() < self.grace_period_end
        )

    def start_trial(self, days=14):
        self.status = 'trialing'
        self.trial_start = timezone.now()
        self.trial_end = timezone.now() + timedelta(days=days)
        self.trial_days = days
        self.save()

    def expire_trial(self):
        """Move to grace period after trial ends."""
        self.status = 'grace_period'
        self.grace_period_end = timezone.now() + timedelta(days=3)
        self.save()

    def activate(self):
        self.status = 'active'
        self.grace_period_end = None
        self.save()


class BillingHistory(models.Model):
    """Invoice and payment history."""
    TYPE_CHOICES = [
        ('invoice', 'Invoice'),
        ('payment', 'Payment'),
        ('refund', 'Refund'),
        ('credit', 'Credit'),
    ]
    STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('unpaid', 'Unpaid'),
        ('void', 'Void'),
        ('refunded', 'Refunded'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, related_name='billing_history',
    )
    record_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='invoice')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unpaid')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='USD')
    description = models.CharField(max_length=255, blank=True)
    stripe_invoice_id = models.CharField(max_length=100, blank=True)
    period_start = models.DateTimeField(null=True, blank=True)
    period_end = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    invoice_pdf_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "billing_history"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.record_type} {self.amount} {self.currency} ({self.status})"

