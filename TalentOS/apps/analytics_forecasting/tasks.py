"""Celery tasks for Analytics Forecasting app."""

from celery import shared_task


@shared_task(name="apps.analytics_forecasting.tasks.compute_fill_time_forecasts")
def compute_fill_time_forecasts():
    """
    Compute FillTimeForecast for all open jobs.
    Simple heuristic: use the tenant's historical average days-to-fill.
    In production, replace with an ML model call.
    EU AI Act Annex III — feature_importances exposed for explainability.
    """
    from django.db.models import Avg
    from apps.analytics_forecasting.models import FillTimeForecast
    from apps.jobs.models import Job

    open_jobs = Job.objects.filter(status="open").select_related("tenant")
    created = 0

    for job in open_jobs:
        # Historical average for tenant
        historical_avg = (
            FillTimeForecast.objects.filter(
                tenant=job.tenant,
                actual_days_to_fill__isnull=False,
            ).aggregate(avg=Avg("actual_days_to_fill"))["avg"]
            or 30.0  # default fallback
        )

        FillTimeForecast.objects.create(
            tenant=job.tenant,
            job=job,
            predicted_days_to_fill=historical_avg,
            confidence_interval_low=historical_avg * 0.75,
            confidence_interval_high=historical_avg * 1.5,
            model_version="heuristic-v1",
            feature_importances={
                "historical_avg_days": 1.0,
                "note": "Heuristic model — replace with ML for production",
            },
        )
        created += 1

    return {"forecasts_created": created}


@shared_task(name="apps.analytics_forecasting.tasks.detect_pipeline_bottlenecks")
def detect_pipeline_bottlenecks():
    """
    Detect stages where candidates have been stuck longer than the benchmark.
    Creates PipelineBottleneck records for any anomalies found.
    """
    from django.utils import timezone
    from django.db.models import Avg, Count
    from apps.analytics_forecasting.models import PipelineBottleneck

    # We use StageHistory from analytics app to compute avg time in stage
    try:
        from apps.analytics.models import StageHistory
    except ImportError:
        return {"error": "StageHistory model not available"}

    BENCHMARK_DAYS = {
        "applied": 2,
        "screening": 5,
        "interview": 10,
        "offer": 3,
    }

    bottlenecks_created = 0
    from apps.tenants.models import Tenant

    for tenant in Tenant.objects.all():
        for stage_name, benchmark in BENCHMARK_DAYS.items():
            histories = StageHistory.objects.filter(
                tenant=tenant,
                stage_name__iexact=stage_name,
                exited_at__isnull=True,
            )
            stuck_count = histories.count()
            avg_days_result = histories.aggregate(
                avg=Avg("days_in_stage")
            )["avg"]
            avg_days = avg_days_result or 0

            if avg_days > benchmark and stuck_count > 0:
                severity = "critical" if avg_days > benchmark * 2 else "high" if avg_days > benchmark * 1.5 else "medium"

                # Don't create duplicate open bottlenecks for same tenant+stage
                existing = PipelineBottleneck.objects.filter(
                    tenant=tenant,
                    stage_name__iexact=stage_name,
                    resolved_at__isnull=True,
                ).exists()

                if not existing:
                    PipelineBottleneck.objects.create(
                        tenant=tenant,
                        stage_name=stage_name,
                        avg_days_in_stage=avg_days,
                        benchmark_days=float(benchmark),
                        candidates_stuck=stuck_count,
                        severity=severity,
                        suggested_action=(
                            f"Review {stage_name} stage — avg {avg_days:.1f} days "
                            f"exceeds {benchmark}d benchmark with {stuck_count} candidates stuck."
                        ),
                    )
                    bottlenecks_created += 1

    return {"bottlenecks_created": bottlenecks_created}


@shared_task(name="apps.analytics_forecasting.tasks.generate_fairness_reports")
def generate_fairness_reports():
    """
    Weekly task: generate FairnessReport snapshots for all tenants.
    Produces tenant-wide combined equity reports.
    EU AI Act Annex III — mandatory periodic fairness monitoring.
    """
    from datetime import date, timedelta
    from apps.analytics_forecasting.models import FairnessReport
    from apps.tenants.models import Tenant

    today = date.today()
    period_start = today - timedelta(days=7)
    reports_created = 0

    for tenant in Tenant.objects.all():
        # Avoid duplicate reports for the same period
        already_exists = FairnessReport.objects.filter(
            tenant=tenant,
            report_type="combined",
            period_start=period_start,
        ).exists()

        if not already_exists:
            FairnessReport.objects.create(
                tenant=tenant,
                report_type="combined",
                period_start=period_start,
                period_end=today,
                funnel_data={},
                adverse_impact_flags=[],
                summary=(
                    "Auto-generated weekly fairness snapshot. "
                    "Manual review required per EU AI Act Annex III."
                ),
            )
            reports_created += 1

    return {"fairness_reports_created": reports_created}
