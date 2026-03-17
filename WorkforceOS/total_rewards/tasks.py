"""
Celery tasks for total_rewards app.
"""
from celery import shared_task


@shared_task(name='total_rewards.tasks.send_merit_cycle_deadline_reminders')
def send_merit_cycle_deadline_reminders():
    """
    Daily task: check merit cycles with approaching deadlines and send
    reminder notifications to managers and HR admins.
    """
    # TODO: implement merit cycle deadline reminder logic
    pass
