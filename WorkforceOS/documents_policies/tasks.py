"""
Celery tasks for documents_policies app.
"""
from celery import shared_task


@shared_task(name='documents_policies.tasks.send_policy_acknowledgement_reminders')
def send_policy_acknowledgement_reminders():
    """
    Weekly task: check for outstanding policy acknowledgement requests
    across all tenants and send reminder notifications to employees.
    """
    # TODO: implement policy acknowledgement reminder logic
    pass
