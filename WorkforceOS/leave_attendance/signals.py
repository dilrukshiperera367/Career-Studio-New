"""
Django signals for automatic leave balance updates.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction

from .models import LeaveRequest, LeaveBalance


@receiver(post_save, sender=LeaveRequest)
def update_leave_balance_on_request_change(sender, instance, created, **kwargs):
    """
    Auto-update LeaveBalance when a LeaveRequest is created or status changes.
    - created: increment pending
    - approved: move from pending → taken
    - rejected/cancelled: decrement pending
    """
    try:
        balance = LeaveBalance.objects.select_for_update().get(
            employee=instance.employee,
            leave_type=instance.leave_type,
        )
    except LeaveBalance.DoesNotExist:
        return
    except Exception:
        return

    # Calculate working days (simple calendar days for now)
    if instance.start_date and instance.end_date:
        days = max(0, (instance.end_date - instance.start_date).days + 1)
    else:
        days = getattr(instance, 'number_of_days', 0) or 0

    if created and instance.status == 'pending':
        # New request
        with transaction.atomic():
            LeaveBalance.objects.filter(pk=balance.pk).update(
                pending=balance.pending + days
            )
    elif not created:
        prev_status = getattr(instance, '_previous_status', None)
        if instance.status == 'approved' and prev_status == 'pending':
            with transaction.atomic():
                LeaveBalance.objects.filter(pk=balance.pk).update(
                    taken=balance.taken + days,
                    pending=max(0, balance.pending - days),
                )
        elif instance.status in ('rejected', 'cancelled') and prev_status == 'pending':
            with transaction.atomic():
                LeaveBalance.objects.filter(pk=balance.pk).update(
                    pending=max(0, balance.pending - days),
                )
