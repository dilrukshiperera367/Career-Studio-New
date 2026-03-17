"""
RBAC Permission checking — per-endpoint permission enforcement.
Usage:
    @require_permission('employees.view')
    def list(self, request):
        ...

    class MyViewSet(PermissionViewSetMixin, viewsets.ModelViewSet):
        required_permissions = {
            'list': 'employees.view',
            'create': 'employees.create',
            'update': 'employees.edit',
            'destroy': 'employees.delete',
        }
"""

from functools import wraps
from rest_framework import permissions, status
from rest_framework.response import Response


class HasTenantPermission(permissions.BasePermission):
    """
    DRF permission class that checks RBAC permissions from UserRole → RolePermission.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Superusers bypass permission checks
        if request.user.is_superuser:
            return True

        # Get required permission from view
        required = getattr(view, 'required_permissions', {})
        action = getattr(view, 'action', None)

        if not required or action not in required:
            return True  # No specific permission required for this action

        permission_codename = required[action]
        return user_has_permission(request.user, permission_codename)


def user_has_permission(user, permission_codename):
    """Check if a user has a specific permission via their roles."""
    if user.is_superuser:
        return True

    from authentication.models import RolePermission, UserRole

    user_role_ids = UserRole.objects.filter(user=user).values_list('role_id', flat=True)
    return RolePermission.objects.filter(
        role_id__in=user_role_ids,
        permission__codename=permission_codename
    ).exists()


def user_permissions(user):
    """Get all permission codenames for a user."""
    if user.is_superuser:
        from authentication.models import Permission
        return list(Permission.objects.values_list('codename', flat=True))

    from authentication.models import RolePermission, UserRole
    user_role_ids = UserRole.objects.filter(user=user).values_list('role_id', flat=True)
    return list(
        RolePermission.objects.filter(role_id__in=user_role_ids)
        .values_list('permission__codename', flat=True)
        .distinct()
    )


def require_permission(permission_codename):
    """Decorator for view methods that require a specific permission."""
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Authentication required'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            if not user_has_permission(request.user, permission_codename):
                return Response(
                    {'error': f'Permission denied: {permission_codename}'},
                    status=status.HTTP_403_FORBIDDEN
                )
            return func(self, request, *args, **kwargs)
        return wrapper
    return decorator


class PermissionViewSetMixin:
    """
    Mixin that automatically checks permissions based on `required_permissions` dict.
    Add to your ViewSet:
        required_permissions = {
            'list': 'module.view',
            'create': 'module.create',
            'update': 'module.edit',
            'destroy': 'module.delete',
        }
    """
    permission_classes = [HasTenantPermission]
