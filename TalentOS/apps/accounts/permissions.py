"""
RBAC Permission Classes for DRF.

Enforces the permission matrix from the spec:
- Admin: full access
- Recruiter: jobs, candidates, applications, evaluations, messages, analytics
- Hiring Manager: own jobs + assigned candidates
- Interviewer: submit evaluations only
"""

import logging
from rest_framework.permissions import BasePermission, SAFE_METHODS

logger = logging.getLogger(__name__)

# ─── Role Constants ────────────────────────────────────────────────────────────
ROLE_SUPER_ADMIN = 'super_admin'
ROLE_ADMIN = 'admin'
ROLE_RECRUITER = 'recruiter'
ROLE_HIRING_MANAGER = 'hiring_manager'
ROLE_INTERVIEWER = 'interviewer'
ROLE_VIEWER = 'viewer'

ADMIN_ROLES = {ROLE_SUPER_ADMIN, ROLE_ADMIN}
RECRUITER_ROLES = {ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_RECRUITER}
MANAGER_ROLES = {ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_RECRUITER, ROLE_HIRING_MANAGER}


class IsTenantMember(BasePermission):
    """User must be authenticated and belong to a tenant."""
    message = 'You must be part of a tenant to access this resource.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'tenant_id', None)
        )


class HasTenantAccess(BasePermission):
    """Ensure user belongs to the tenant in the request."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return (
            hasattr(request, "tenant_id") and
            request.tenant_id and
            str(request.user.tenant_id) == str(request.tenant_id)
        )

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        user_tenant = getattr(request.user, 'tenant_id', None)
        if not user_tenant:
            return False
        # Check common tenant field patterns
        for field in ('tenant_id', 'tenant'):
            obj_tenant = getattr(obj, field, None)
            if obj_tenant:
                obj_tenant_id = getattr(obj_tenant, 'id', obj_tenant)
                if str(obj_tenant_id) == str(user_tenant):
                    return True
        # Check via job for applications/evaluations
        job = getattr(obj, 'job', None)
        if job:
            job_tenant = getattr(job, 'tenant_id', None) or getattr(
                getattr(job, 'tenant', None), 'id', None
            )
            if job_tenant and str(job_tenant) == str(user_tenant):
                return True
        return False


class HasPermission(BasePermission):
    """
    Check if the user has a specific permission.
    Usage: permission_classes = [HasPermission]
    View must define `required_permission` attribute.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True

        required = getattr(view, "required_permission", None)
        if not required:
            return True

        return _user_has_permission(request.user, required)


class IsTenantAdmin(BasePermission):
    """User must have the 'admin' role in their tenant."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return _user_has_role(request.user, "admin")


class IsAdminUser(BasePermission):
    """Fine-grained RBAC: user must have admin or super_admin role."""
    message = 'You must be an administrator to perform this action.'

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return has_role(request.user, ROLE_SUPER_ADMIN, ROLE_ADMIN)


class IsRecruiter(BasePermission):
    """User must have recruiter or admin role."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return _user_has_role(request.user, "recruiter") or _user_has_role(request.user, "admin")


class IsHiringManager(BasePermission):
    """User must have hiring_manager, recruiter, or admin role."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return (
            _user_has_role(request.user, "hiring_manager") or
            _user_has_role(request.user, "recruiter") or
            _user_has_role(request.user, "admin")
        )


class IsInterviewer(BasePermission):
    """User must have interviewer role or higher."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return (
            _user_has_role(request.user, "interviewer") or
            _user_has_role(request.user, "hiring_manager") or
            _user_has_role(request.user, "recruiter") or
            _user_has_role(request.user, "admin")
        )


class ReadOnlyOrRecruiter(BasePermission):
    """
    Safe methods (GET, HEAD, OPTIONS) allowed for any authenticated user.
    Mutating methods require recruiter or higher role.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return has_role(request.user, *RECRUITER_ROLES)


class IsOwnerOrAdmin(BasePermission):
    """Allow owners of a resource or admin users to mutate it."""
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if has_role(request.user, ROLE_SUPER_ADMIN, ROLE_ADMIN):
            return True
        # Check common owner field patterns
        for field in ('created_by', 'owner', 'user', 'recruiter'):
            owner = getattr(obj, field, None)
            if owner and str(getattr(owner, 'id', None)) == str(request.user.id):
                return True
        return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user_roles(user) -> set:
    """Return the set of role names for a user."""
    if not user or not user.is_authenticated:
        return set()
    if user.is_superuser:
        return {ROLE_SUPER_ADMIN}
    if not hasattr(user, "_role_name_cache"):
        user._role_name_cache = set(
            user.user_roles.values_list("role__name", flat=True)
        )
    return user._role_name_cache


def has_role(user, *roles) -> bool:
    """True if user has any of the given roles."""
    return bool(_user_roles(user) & set(roles))


def _user_has_role(user, role_name: str) -> bool:
    """Check if user has a specific role (cached on first call)."""
    if not hasattr(user, "_role_cache"):
        user._role_cache = set(
            user.user_roles.values_list("role__name", flat=True)
        )
    return role_name in user._role_cache


def _user_has_permission(user, permission: str) -> bool:
    """Check if any of the user's roles grant the permission."""
    if not hasattr(user, "_permission_cache"):
        roles = user.user_roles.select_related("role").all()
        perms = set()
        for ur in roles:
            for perm in ur.role.permissions:
                perms.add(perm)
        user._permission_cache = perms
    return permission in user._permission_cache
