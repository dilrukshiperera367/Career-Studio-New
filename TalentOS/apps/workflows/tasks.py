"""Celery tasks for workflow automation and idle detection."""

import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task
def process_automation_event(event_data: dict):
    """Process a workflow trigger event asynchronously."""
    from apps.workflows.services import process_event
    process_event(event_data)


@shared_task
def check_idle_applications():
    """
    Daily scheduled task: detect applications idle for >N days.
    Fires 'application_idle' event for each.
    """
    from apps.tenants.models import Tenant, TenantSettings
    from apps.applications.models import Application

    for tenant in Tenant.objects.filter(status="active"):
        settings = TenantSettings.objects.filter(tenant=tenant).first()
        threshold_days = settings.idle_threshold_days if settings else 7
        cutoff = timezone.now() - timedelta(days=threshold_days)

        idle_apps = Application.objects.filter(
            tenant=tenant,
            status="active",
            updated_at__lt=cutoff,
        ).exclude(
            current_stage__is_terminal=True,
        )

        for app in idle_apps[:100]:  # cap per tenant per run
            from apps.workflows.services import process_event
            process_event({
                "tenant_id": str(tenant.id),
                "event_type": "application_idle",
                "event_id": f"idle-{app.id}-{timezone.now().date().isoformat()}",
                "payload": {
                    "application_id": str(app.id),
                    "candidate_id": str(app.candidate_id),
                    "job_id": str(app.job_id),
                    "idle_days": threshold_days,
                },
            })

        logger.info(f"Tenant {tenant.id}: {idle_apps.count()} idle applications detected")


@shared_task
def execute_pending_workflow_steps():
    """
    Every-5-minutes scheduled task: execute delayed WorkflowExecution steps
    whose execute_at time has passed.
    """
    from apps.workflows.services import execute_pending_workflow_steps as _run
    _run()
