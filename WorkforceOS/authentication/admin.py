"""Admin registration for the authentication app."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Role, Permission, RolePermission, UserRole, PasswordResetToken, InviteToken


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'tenant', 'status', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('status', 'is_staff', 'is_active', 'tenant')
    search_fields = ('email', 'first_name', 'last_name', 'tenant__name')
    readonly_fields = ('id', 'date_joined', 'last_login_at')
    ordering = ('-date_joined',)
    fieldsets = (
        (None, {'fields': ('id', 'email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'avatar_url')}),
        ('Tenant & Status', {'fields': ('tenant', 'status')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
        ('Timestamps', {'fields': ('date_joined', 'last_login_at')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'tenant', 'password1', 'password2'),
        }),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'is_system_role', 'created_at')
    list_filter = ('is_system_role', 'tenant')
    search_fields = ('name', 'description', 'tenant__name')
    readonly_fields = ('id', 'created_at')


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('codename', 'category', 'description')
    list_filter = ('category',)
    search_fields = ('codename', 'description', 'category')
    readonly_fields = ('id',)
    ordering = ('category', 'codename')


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ('role', 'permission', 'scope')
    list_filter = ('scope', 'role')
    search_fields = ('role__name', 'permission__codename')
    autocomplete_fields = ('role', 'permission')


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'assigned_at', 'assigned_by')
    list_filter = ('role',)
    search_fields = ('user__email', 'role__name')
    readonly_fields = ('assigned_at',)


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'expires_at', 'used')
    list_filter = ('used',)
    search_fields = ('user__email',)
    readonly_fields = ('id', 'created_at', 'token')


@admin.register(InviteToken)
class InviteTokenAdmin(admin.ModelAdmin):
    list_display = ('email', 'tenant', 'invited_by', 'role_name', 'accepted', 'created_at', 'expires_at')
    list_filter = ('accepted', 'tenant')
    search_fields = ('email', 'tenant__name', 'role_name')
    readonly_fields = ('id', 'created_at', 'token', 'accepted_at')
