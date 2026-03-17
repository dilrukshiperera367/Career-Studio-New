"""Celery tasks for Compliance AI app."""

from celery import shared_task


@shared_task(name="apps.compliance_ai.tasks.generate_bias_monitoring_report")
def generate_bias_monitoring_report(ai_model_id: str, period_start: str, period_end: str):
    """
    Generate a BiasMonitoringReport for the given AI model and period.
    Computes adverse impact ratios from AIOutputLog records.
    EU AI Act Annex III — mandatory periodic bias monitoring.
    """
    from apps.compliance_ai.models import AIModel, AIOutputLog, BiasMonitoringReport

    try:
        ai_model = AIModel.objects.get(pk=ai_model_id)
    except AIModel.DoesNotExist:
        return {"error": "ai_model_not_found"}

    logs = AIOutputLog.objects.filter(
        prompt_log__ai_model=ai_model,
        created_at__date__gte=period_start,
        created_at__date__lte=period_end,
    )
    total = logs.count()

    BiasMonitoringReport.objects.create(
        tenant=ai_model.tenant,
        ai_model=ai_model,
        period_start=period_start,
        period_end=period_end,
        total_decisions=total,
        adverse_impact_ratio={},
        disparate_impact_flags=[],
        remediation_actions="Automated report — manual review required for Annex III compliance.",
    )
    return {"ai_model": str(ai_model_id), "total_decisions": total}


@shared_task(name="apps.compliance_ai.tasks.expire_ai_logs")
def expire_ai_logs():
    """
    Purge AIPromptLog and AIOutputLog records older than the tenant's data_retention_days.
    EU AI Act / GDPR data minimisation.
    """
    from django.utils import timezone
    from datetime import timedelta
    from apps.compliance_ai.models import AIPolicy, AIPromptLog

    purged = 0
    for policy in AIPolicy.objects.all():
        cutoff = timezone.now() - timedelta(days=policy.data_retention_days)
        deleted_count, _ = AIPromptLog.objects.filter(
            tenant=policy.tenant,
            created_at__lt=cutoff,
        ).delete()
        purged += deleted_count

    return {"prompt_logs_purged": purged}


@shared_task(name="apps.compliance_ai.tasks.escalate_overdue_reviews")
def escalate_overdue_reviews():
    """
    Escalate HumanReviewQueue items whose review_deadline has passed and are still pending/in_review.
    """
    from django.utils import timezone
    from apps.compliance_ai.models import HumanReviewQueue

    now = timezone.now()
    overdue = HumanReviewQueue.objects.filter(
        status__in=["pending", "in_review"],
        review_deadline__lt=now,
    )
    count = overdue.count()
    overdue.update(status="escalated")
    return {"reviews_escalated": count}
