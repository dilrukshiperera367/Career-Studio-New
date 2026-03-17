"""Admin registration for the custom_objects app."""

from django.contrib import admin
from .models import CustomObjectDefinition, CustomObjectRecord


@admin.register(CustomObjectDefinition)
class CustomObjectDefinitionAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon', 'tenant', 'plural_name', 'is_active',
                    'record_count', 'enable_timeline', 'enable_workflows', 'created_at')
    list_filter = ('is_active', 'enable_timeline', 'enable_workflows', 'tenant')
    search_fields = ('name', 'slug', 'description', 'tenant__name')
    readonly_fields = ('id', 'created_at', 'updated_at', 'record_count')
    ordering = ('name',)


@admin.register(CustomObjectRecord)
class CustomObjectRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'definition', 'tenant', 'employee', 'created_at', 'updated_at')
    list_filter = ('definition', 'tenant')
    search_fields = ('definition__name', 'employee__first_name', 'employee__last_name', 'tenant__name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('employee', 'created_by', 'updated_by')
    ordering = ('-created_at',)
