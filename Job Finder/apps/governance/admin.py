from django.contrib import admin
from .models import AIDecisionLog, BiasMetric, Guardrail


@admin.register(AIDecisionLog)
class AIDecisionLogAdmin(admin.ModelAdmin):
    list_display = ["decision_type", "action", "candidate_name", "is_reviewed", "created_at"]
    list_filter = ["decision_type", "is_reviewed"]
    search_fields = ["candidate_name", "job_title", "action"]


@admin.register(BiasMetric)
class BiasMetricAdmin(admin.ModelAdmin):
    list_display = ["group", "metric_name", "value", "status", "measured_at"]
    list_filter = ["status", "group"]


@admin.register(Guardrail)
class GuardrailAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active", "category", "updated_at"]
    list_filter = ["is_active", "category"]
