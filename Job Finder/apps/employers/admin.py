"""Employers admin registrations."""
from django.contrib import admin
from .models import EmployerAccount, EmployerTeamMember, EmployerBranding


class EmployerTeamMemberInline(admin.TabularInline):
    model = EmployerTeamMember
    extra = 0


class EmployerBrandingInline(admin.StackedInline):
    model = EmployerBranding
    extra = 0


@admin.register(EmployerAccount)
class EmployerAccountAdmin(admin.ModelAdmin):
    list_display = ("company_name", "slug", "industry", "company_size", "plan", "is_verified")
    list_filter = ("is_verified", "plan", "company_size", "industry")
    search_fields = ("company_name", "slug", "registration_no")
    prepopulated_fields = {"slug": ("company_name",)}
    readonly_fields = ("created_at", "updated_at")
    inlines = [EmployerTeamMemberInline, EmployerBrandingInline]


@admin.register(EmployerTeamMember)
class EmployerTeamMemberAdmin(admin.ModelAdmin):
    list_display = ("user", "employer", "role", "invited_at")
    list_filter = ("role",)


@admin.register(EmployerBranding)
class EmployerBrandingAdmin(admin.ModelAdmin):
    list_display = ("employer",)
