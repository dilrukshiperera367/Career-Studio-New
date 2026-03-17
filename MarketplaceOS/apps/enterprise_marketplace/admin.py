from django.contrib import admin
from .models import (
    EnterpriseAccount, EnterpriseTeamMember, EnterpriseBudget,
    EnterpriseApprovedProvider, InternalMentorProgram, InternalMentorMatch,
)


@admin.register(EnterpriseAccount)
class EnterpriseAccountAdmin(admin.ModelAdmin):
    list_display = ["company_name", "tier", "status", "primary_admin", "created_at"]
    list_filter = ["tier", "status"]
    search_fields = ["company_name", "primary_admin__email"]
    prepopulated_fields = {"slug": ("company_name",)}


@admin.register(EnterpriseTeamMember)
class EnterpriseTeamMemberAdmin(admin.ModelAdmin):
    list_display = ["user", "enterprise", "role", "department", "is_active", "joined_at"]
    list_filter = ["role", "is_active"]
    search_fields = ["user__email", "enterprise__company_name"]


@admin.register(EnterpriseBudget)
class EnterpriseBudgetAdmin(admin.ModelAdmin):
    list_display = ["enterprise", "name", "budget_type", "total_amount_lkr", "spent_amount_lkr", "is_active"]
    list_filter = ["budget_type", "is_active"]


@admin.register(EnterpriseApprovedProvider)
class EnterpriseApprovedProviderAdmin(admin.ModelAdmin):
    list_display = ["enterprise", "provider", "is_active", "approved_at"]
    list_filter = ["is_active"]


@admin.register(InternalMentorProgram)
class InternalMentorProgramAdmin(admin.ModelAdmin):
    list_display = ["enterprise", "name", "status", "start_date", "end_date"]
    list_filter = ["status"]


@admin.register(InternalMentorMatch)
class InternalMentorMatchAdmin(admin.ModelAdmin):
    list_display = ["mentor", "mentee", "program", "status", "sessions_completed", "matched_at"]
    list_filter = ["status"]
