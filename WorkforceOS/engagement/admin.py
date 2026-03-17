"""Admin registration for the engagement app."""

from django.contrib import admin
from .models import Survey, SurveyResponse, RecognitionEntry


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ('title', 'tenant', 'type', 'status', 'anonymous', 'start_date', 'end_date',
                    'created_by', 'created_at')
    list_filter = ('type', 'status', 'anonymous', 'tenant')
    search_fields = ('title', 'description', 'tenant__name')
    readonly_fields = ('id', 'created_at')
    date_hierarchy = 'created_at'


@admin.register(SurveyResponse)
class SurveyResponseAdmin(admin.ModelAdmin):
    list_display = ('id', 'survey', 'tenant', 'employee', 'nps_score', 'submitted_at')
    list_filter = ('survey', 'tenant')
    search_fields = ('survey__title', 'employee__first_name', 'employee__last_name')
    readonly_fields = ('id', 'submitted_at')
    raw_id_fields = ('employee',)
    date_hierarchy = 'submitted_at'


@admin.register(RecognitionEntry)
class RecognitionEntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'from_employee', 'to_employee', 'tenant', 'category', 'likes_count', 'created_at')
    list_filter = ('category', 'tenant')
    search_fields = ('message', 'from_employee__first_name', 'from_employee__last_name',
                     'to_employee__first_name', 'to_employee__last_name')
    readonly_fields = ('id', 'created_at')
    raw_id_fields = ('from_employee', 'to_employee')
    date_hierarchy = 'created_at'
