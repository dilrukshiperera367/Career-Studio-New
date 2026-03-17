"""Additional Celery tasks for weekly report generation."""

from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task(name="apps.analytics.tasks.generate_weekly_report")
def generate_weekly_report():
    """Generate weekly recruitment report and notify admins."""
    try:
        from apps.analytics.services import compute_metrics
        from apps.tenants.models import Tenant

        reports = []
        for tenant in Tenant.objects.filter(is_active=True):
            metrics = compute_metrics(tenant)
            reports.append({
                "tenant": tenant.name,
                "metrics": metrics,
                "generated_at": timezone.now().isoformat(),
            })

        logger.info(f"generate_weekly_report: generated reports for {len(reports)} tenants")
        return {"reports_generated": len(reports)}
    except Exception as e:
        logger.error(f"generate_weekly_report: {e}")
        return {"error": str(e)}
