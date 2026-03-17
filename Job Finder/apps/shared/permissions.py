from rest_framework import permissions


class IsSeeker(permissions.BasePermission):
    """Allow access to job seekers only."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == "seeker"


class IsEmployer(permissions.BasePermission):
    """Allow access to employer users only."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == "employer"


class IsAdmin(permissions.BasePermission):
    """Allow access to platform admins only."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type in ("admin", "moderator")


class IsModerator(permissions.BasePermission):
    """Allow access to moderators and admins."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type in ("admin", "moderator")


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Object owners can edit; others read only."""
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if hasattr(obj, "user"):
            return obj.user == request.user
        if hasattr(obj, "seeker"):
            return obj.seeker.user == request.user
        if hasattr(obj, "employer"):
            return request.user in obj.employer.team_members.values_list("user", flat=True)
        return False
