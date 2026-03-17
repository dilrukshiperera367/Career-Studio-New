"""
CampusOS — Accounts: Custom User model supporting all platform roles.

Roles:
    student         — enrolled students
    placement_officer — campus placement cell staff
    faculty_advisor — faculty/academic advisors
    career_center   — career center counselors
    employer_recruiter — employer-side recruiters
    alumni_mentor   — alumni providing mentoring
    campus_admin    — institution-level admin
    super_admin     — platform super admin
"""

import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


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
        extra_fields.setdefault("role", User.Role.SUPER_ADMIN)
        extra_fields.setdefault("is_verified", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Central user model for all CampusOS actors."""

    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        PLACEMENT_OFFICER = "placement_officer", "Placement Officer"
        FACULTY_ADVISOR = "faculty_advisor", "Faculty / Advisor"
        CAREER_CENTER = "career_center", "Career Center Staff"
        EMPLOYER_RECRUITER = "employer_recruiter", "Employer / Recruiter"
        ALUMNI_MENTOR = "alumni_mentor", "Alumni Mentor"
        CAMPUS_ADMIN = "campus_admin", "Campus Administrator"
        SUPER_ADMIN = "super_admin", "Super Admin"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    role = models.CharField(max_length=25, choices=Role.choices, default=Role.STUDENT)

    # Campus / institution link (null for super_admin and free students)
    campus = models.ForeignKey(
        "campus.Campus",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )

    # Contact
    phone = models.CharField(max_length=20, blank=True, default="")
    profile_photo = models.ImageField(
        upload_to="users/photos/", null=True, blank=True
    )

    # Status flags
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)

    # Privacy
    profile_visibility = models.CharField(
        max_length=10,
        choices=[("public", "Public"), ("campus", "Campus Only"), ("private", "Private")],
        default="campus",
    )

    # Notification preferences
    notify_email = models.BooleanField(default=True)
    notify_sms = models.BooleanField(default=False)
    notify_whatsapp = models.BooleanField(default=False)
    notify_push = models.BooleanField(default=True)

    # Consent & policy
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    privacy_accepted_at = models.DateTimeField(null=True, blank=True)
    data_processing_consent = models.BooleanField(default=False)
    marketing_consent = models.BooleanField(default=False)

    # Analytics / tracking
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    login_count = models.PositiveIntegerField(default=0)

    date_joined = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    class Meta:
        db_table = "campus_users"
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-date_joined"]
        indexes = [
            models.Index(fields=["email", "role"]),
            models.Index(fields=["campus", "role"]),
        ]

    def __str__(self):
        return f"{self.get_full_name()} ({self.role}) — {self.email}"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_placement_officer(self):
        return self.role == self.Role.PLACEMENT_OFFICER

    @property
    def is_faculty_advisor(self):
        return self.role == self.Role.FACULTY_ADVISOR

    @property
    def is_employer(self):
        return self.role == self.Role.EMPLOYER_RECRUITER

    @property
    def is_alumni_mentor(self):
        return self.role == self.Role.ALUMNI_MENTOR

    @property
    def is_campus_admin(self):
        return self.role in (self.Role.CAMPUS_ADMIN, self.Role.SUPER_ADMIN)


class EmailVerificationToken(models.Model):
    """Token for email address verification."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="email_tokens")
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "campus_email_verification_tokens"

    def is_valid(self):
        return self.used_at is None and self.expires_at > timezone.now()


class PasswordResetToken(models.Model):
    """Token for password reset flow."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_reset_tokens")
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "campus_password_reset_tokens"

    def is_valid(self):
        return self.used_at is None and self.expires_at > timezone.now()
