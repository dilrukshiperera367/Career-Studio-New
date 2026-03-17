"""CampusOS — Shared permissions, mixins, and utilities."""

from rest_framework.permissions import BasePermission


class IsCampusAdmin(BasePermission):
    """Allow only campus_admin or super_admin roles."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in (
            "campus_admin", "super_admin"
        )


class IsSameCampus(BasePermission):
    """Allow authenticated users who belong to a campus."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.campus_id is not None


class IsPlacementOfficer(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in (
            "placement_officer", "campus_admin", "super_admin"
        )


class IsFacultyOrAdvisor(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in (
            "faculty_advisor", "career_center", "placement_officer",
            "campus_admin", "super_admin"
        )


class IsEmployerRecruiter(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "employer_recruiter"


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "student"


class IsAlumniMentor(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "alumni_mentor"


class IsOwnerOrCampusStaff(BasePermission):
    """Object-level: owner, or campus staff of the same campus."""

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        # Super admin always allowed
        if request.user.role == "super_admin":
            return True
        # Campus admin / placement officer of same campus
        if request.user.role in ("campus_admin", "placement_officer", "faculty_advisor"):
            owner_campus = getattr(obj, "campus_id", None) or getattr(
                getattr(obj, "user", None), "campus_id", None
            )
            return owner_campus == request.user.campus_id
        # Owner
        owner = getattr(obj, "user", None) or getattr(obj, "student", None)
        if owner:
            return owner == request.user
        return False
