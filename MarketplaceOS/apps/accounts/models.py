"""MarketplaceOS User model — supports all platform roles."""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Extended user model for MarketplaceOS.
    Roles: provider (coach/mentor/etc.), buyer (candidate/employee/employer), admin.
    """

    class Role(models.TextChoices):
        PROVIDER = "provider", "Service Provider"
        BUYER = "buyer", "Service Buyer (Candidate / Employee)"
        EMPLOYER = "employer", "Employer / Enterprise Buyer"
        ADMIN = "admin", "Platform Admin"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.BUYER)
    phone = models.CharField(max_length=30, blank=True, default="")
    avatar_url = models.URLField(blank=True, default="")
    bio = models.TextField(blank=True, default="")
    linkedin_url = models.URLField(blank=True, default="")
    timezone = models.CharField(max_length=50, default="Asia/Colombo")
    preferred_language = models.CharField(max_length=10, default="en")
    is_verified = models.BooleanField(default=False)
    last_active = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mp_user"
        verbose_name = "User"

    def __str__(self):
        return self.email
