"""Celery tasks for analytics computation."""

import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task
def compute_daily_analytics():
    """
    Nightly batch: compute and store daily metrics for all tenants.
    Metrics: applications_per_day, time_in_stage_avg, funnel_conversion, source_quality.
    """
    from apps.tenants.models import Tenant
    from apps.applications.models import Application, StageHistory
    from apps.analytics.models import AnalyticsDaily

    yesterday = (timezone.now() - timedelta(days=1)).date()

    for tenant in Tenant.objects.filter(status="active"):
        tenant_id = tenant.id

        # 1) Applications per day
        app_count = Application.objects.filter(
            tenant=tenant,
            created_at__date=yesterday,
        ).count()

        AnalyticsDaily.objects.update_or_create(
            tenant=tenant,
            job=None,
            metric="applications_per_day",
            computed_date=yesterday,
            defaults={"value": app_count},
        )

        # 2) Time-in-stage (avg hours) across all transitions yesterday
        transitions = StageHistory.objects.filter(
            tenant=tenant,
            created_at__date=yesterday,
        ).select_related("from_stage", "to_stage")

        stage_durations = {}
        for t in transitions:
            if t.from_stage:
                # Find previous transition for this application
                prev = StageHistory.objects.filter(
                    application=t.application,
                    to_stage=t.from_stage,
                ).order_by("-created_at").first()
                if prev:
                    duration_hours = (t.created_at - prev.created_at).total_seconds() / 3600
                    stage_name = t.from_stage.name
                    if stage_name not in stage_durations:
                        stage_durations[stage_name] = []
                    stage_durations[stage_name].append(duration_hours)

        for stage_name, durations in stage_durations.items():
            avg_hours = sum(durations) / len(durations)
            AnalyticsDaily.objects.update_or_create(
                tenant=tenant,
                job=None,
                metric=f"avg_hours_in_{stage_name.lower().replace(' ', '_')}",
                computed_date=yesterday,
                defaults={
                    "value": round(avg_hours, 2),
                    "metadata": {"count": len(durations)},
                },
            )

        # 3) Source quality (applications per source)
        from django.db.models import Count
        sources = Application.objects.filter(
            tenant=tenant,
            created_at__date=yesterday,
        ).values("source").annotate(count=Count("id"))

        for src in sources:
            AnalyticsDaily.objects.update_or_create(
                tenant=tenant,
                job=None,
                metric="source_applications",
                computed_date=yesterday,
                defaults={
                    "value": src["count"],
                    "metadata": {"source": src["source"]},
                },
            )

        logger.info(f"Analytics computed for tenant {tenant_id} on {yesterday}")
