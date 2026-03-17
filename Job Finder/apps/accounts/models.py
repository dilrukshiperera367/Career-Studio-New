"""Accounts app — Custom User model, sessions, verification tokens.
Features #1–35: Authentication & User Management.
"""
import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("user_type", "admin")
        extra.setdefault("is_verified", True)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user for Job Finder (#1–8, #28, #30)."""

    class UserType(models.TextChoices):
        SEEKER = "seeker", "Job Seeker"
        EMPLOYER = "employer", "Employer"
        ADMIN = "admin", "Admin"
        MODERATOR = "moderator", "Moderator"

    class LoginMethod(models.TextChoices):
        EMAIL = "email", "Email"
        PHONE = "phone", "Phone"
        GOOGLE = "google", "Google"
        FACEBOOK = "facebook", "Facebook"
        LINKEDIN = "linkedin", "LinkedIn"
        APPLE = "apple", "Apple"

    class Language(models.TextChoices):
        EN = "en", "English"
        SI = "si", "සිංහල"
        TA = "ta", "தமிழ்"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, unique=True, null=True, blank=True)
    user_type = models.CharField(max_length=10, choices=UserType.choices, default=UserType.SEEKER)
    preferred_lang = models.CharField(max_length=2, choices=Language.choices, default=Language.EN)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    login_method = models.CharField(max_length=10, choices=LoginMethod.choices, default=LoginMethod.EMAIL)
    avatar_url = models.URLField(max_length=500, null=True, blank=True)

    # Social auth IDs (#3–6, #21–22)
    google_id = models.CharField(max_length=100, null=True, blank=True, unique=True)
    facebook_id = models.CharField(max_length=100, null=True, blank=True, unique=True)
    linkedin_id = models.CharField(max_length=100, null=True, blank=True, unique=True)
    apple_id = models.CharField(max_length=100, null=True, blank=True, unique=True)

    # ToS acceptance (#32)
    tos_accepted_version = models.CharField(max_length=20, blank=True, default="")
    tos_accepted_at = models.DateTimeField(null=True, blank=True)

    # Registration tracking (#31)
    registration_source = models.CharField(max_length=50, blank=True, default="")
    utm_source = models.CharField(max_length=100, blank=True, default="")
    utm_medium = models.CharField(max_length=100, blank=True, default="")
    utm_campaign = models.CharField(max_length=100, blank=True, default="")

    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "jf_users"
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["phone"]),
            models.Index(fields=["user_type"]),
        ]

    def __str__(self):
        return self.email


class EmailVerificationToken(models.Model):
    """Email verification OTP (#1, #19)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="email_tokens")
    token = models.CharField(max_length=6)
    new_email = models.EmailField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = "jf_email_verification_tokens"


class PhoneVerificationToken(models.Model):
    """SMS OTP verification (#2, #8, #20)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="phone_tokens")
    phone = models.CharField(max_length=15)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = "jf_phone_verification_tokens"


class PasswordResetToken(models.Model):
    """Password reset (#12, #13)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_reset_tokens")
    token = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = "jf_password_reset_tokens"


class MagicLinkToken(models.Model):
    """Passwordless login via magic link (#7)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="magic_links")
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = "jf_magic_link_tokens"


class UserSession(models.Model):
    """Active session tracking (#16, #17, #25)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    session_key = models.CharField(max_length=64, unique=True)
    device_info = models.CharField(max_length=200, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True)
    location = models.CharField(max_length=100, blank=True, default="")
    is_trusted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_active_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_user_sessions"


class LoginAttempt(models.Model):
    """Login attempt tracking for rate limiting (#23)."""
    email = models.EmailField()
    ip_address = models.GenericIPAddressField()
    success = models.BooleanField(default=False)
    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_login_attempts"
        indexes = [
            models.Index(fields=["email", "attempted_at"]),
            models.Index(fields=["ip_address", "attempted_at"]),
        ]


class TwoFactorSecret(models.Model):
    """TOTP 2FA for employer accounts (#10)."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="two_factor")
    secret = models.CharField(max_length=32)
    is_enabled = models.BooleanField(default=False)
    backup_codes = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_two_factor_secrets"


class PushToken(models.Model):
    """Push notification device tokens (#27)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="push_tokens")
    token = models.CharField(max_length=500)
    platform = models.CharField(max_length=10, choices=[("web", "Web"), ("android", "Android"), ("ios", "iOS")])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_push_tokens"
        unique_together = ["user", "token"]
