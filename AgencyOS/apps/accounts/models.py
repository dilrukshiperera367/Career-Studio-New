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
    """Custom user model for AgencyOS — UUID PK, email-based auth."""

    class Role(models.TextChoices):
        AGENCY_OWNER = "agency_owner", "Agency Owner"
        AGENCY_MANAGER = "agency_manager", "Agency Manager"
        ACCOUNT_MANAGER = "account_manager", "Account Manager"
        DELIVERY_MANAGER = "delivery_manager", "Delivery Manager"
        RECRUITER = "recruiter", "Recruiter"
        RESEARCHER = "researcher", "Researcher"
        FINANCE = "finance", "Finance / Billing"
        COMPLIANCE_OFFICER = "compliance_officer", "Compliance Officer"
        # External roles
        CLIENT_CONTACT = "client_contact", "Client Contact (Portal)"
        CANDIDATE = "candidate", "Candidate (Portal)"
        CONTRACTOR = "contractor", "Contractor (Portal)"
        ADMIN = "admin", "Platform Admin"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True, default="")
    last_name = models.CharField(max_length=150, blank=True, default="")
    role = models.CharField(max_length=30, choices=Role.choices, default=Role.RECRUITER)
    phone = models.CharField(max_length=30, blank=True, default="")
    avatar_url = models.URLField(blank=True, default="")
    bio = models.TextField(blank=True, default="")
    linkedin_url = models.URLField(blank=True, default="")
    timezone = models.CharField(max_length=50, default="Asia/Colombo")
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    last_active = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        db_table = "agency_user"
        verbose_name = "User"

    def __str__(self):
        return self.email
