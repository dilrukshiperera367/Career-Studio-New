"""Custom User model and RBAC (Roles + Permissions)."""

import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, tenant_id=None, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, tenant_id=tenant_id, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model — every user belongs to a tenant."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='users', null=True, blank=True
    )
    email = models.EmailField(max_length=320, unique=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    avatar_url = models.URLField(max_length=500, blank=True)
    status = models.CharField(max_length=20, default='active', choices=[
        ('active', 'Active'),
        ('invited', 'Invited'),
        ('disabled', 'Disabled'),
    ])
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'users'
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'email'], name='unique_tenant_email')
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} <{self.email}>"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class Role(models.Model):
    """RBAC roles — system roles are seeded, tenants can create custom roles."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='roles', null=True, blank=True,
        help_text="NULL for system-wide roles"
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_system_role = models.BooleanField(default=False, help_text="System roles cannot be deleted")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'roles'
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'name'], name='unique_tenant_role')
        ]

    def __str__(self):
        return self.name


class Permission(models.Model):
    """Granular permissions (e.g., 'employees.view', 'payroll.run')."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codename = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, help_text="Module category: core_hr, leave, payroll, etc.")

    class Meta:
        db_table = 'hrm_permissions'
        ordering = ['category', 'codename']

    def __str__(self):
        return self.codename


class RolePermission(models.Model):
    """Junction: role ↔ permission with optional scope."""
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name='role_permissions')
    scope = models.CharField(max_length=20, default='all', choices=[
        ('own', 'Own records only'),
        ('team', 'Direct reports'),
        ('department', 'Department'),
        ('branch', 'Branch'),
        ('company', 'Company'),
        ('all', 'All records'),
    ])
    scope_values = models.JSONField(default=list, blank=True, help_text="Specific dept/branch IDs if scoped")

    class Meta:
        db_table = 'role_permissions'
        unique_together = ['role', 'permission']


class UserRole(models.Model):
    """Junction: user ↔ role (a user can have multiple roles)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='user_roles')
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    class Meta:
        db_table = 'user_roles'
        unique_together = ['user', 'role']

    def __str__(self):
        return f"{self.user.email} → {self.role.name}"


# ---------------------------------------------------------------------------
# Password reset and invite tokens
# ---------------------------------------------------------------------------

class PasswordResetToken(models.Model):
    """Secure one-use token for HRM password reset."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token = models.CharField(max_length=128, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        db_table = 'hrm_password_reset_tokens'

    def __str__(self):
        return f"PasswordResetToken({self.user.email})"


class InviteToken(models.Model):
    """Invitation token for HRM users."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='invites')
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sent_invites')
    email = models.EmailField()
    role_name = models.CharField(max_length=100, default='Employee')
    token = models.CharField(max_length=128, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'hrm_invite_tokens'
        unique_together = [('tenant', 'email')]

    def __str__(self):
        return f"Invite({self.email} → {self.tenant.name})"

