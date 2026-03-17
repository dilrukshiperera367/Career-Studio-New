"""
Celery tasks for global_workforce app.
"""
from celery import shared_task


@shared_task(name='global_workforce.tasks.send_visa_permit_expiry_reminders')
def send_visa_permit_expiry_reminders():
    """
    Daily task: check for visa/work permit records expiring within 30, 60,
    and 90 days across all tenants and send reminder notifications.
    """
    # TODO: implement visa/permit expiry reminder logic
    pass
