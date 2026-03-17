import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_verification(self, user_id: str, token: str):
    """Send email verification link to user."""
    from apps.accounts.models import User
    try:
        user = User.objects.get(id=user_id)
        verify_url = f"{settings.FRONTEND_URL}/auth/verify-email?token={token}"
        html_message = render_to_string('emails/verify_email.html', {
            'user': user,
            'verify_url': verify_url,
        })
        send_mail(
            subject='Verify your email - JobFinder.lk',
            message=f'Verify your email: {verify_url}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f'Verification email sent to {user.email}')
    except Exception as exc:
        logger.error(f'Failed to send verification email: {exc}')
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_password_reset_email(self, user_id: str, token: str):
    """Send password reset email."""
    from apps.accounts.models import User
    try:
        user = User.objects.get(id=user_id)
        reset_url = f"{settings.FRONTEND_URL}/auth/reset-password?token={token}"
        html_message = render_to_string('emails/password_reset.html', {
            'user': user,
            'reset_url': reset_url,
        })
        send_mail(
            subject='Reset your password - JobFinder.lk',
            message=f'Reset your password: {reset_url}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f'Password reset email sent to {user.email}')
    except Exception as exc:
        logger.error(f'Failed to send password reset email: {exc}')
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_application_notification(self, application_id: str):
    """Notify employer about a new application."""
    from apps.applications.models import Application
    try:
        application = Application.objects.select_related('job__employer__user', 'candidate__user').get(id=application_id)
        employer_email = application.job.employer.email or application.job.employer.user.email
        html_message = render_to_string('emails/new_application.html', {
            'application': application,
            'job': application.job,
            'candidate_name': application.candidate.user.get_full_name(),
        })
        send_mail(
            subject=f'New Application: {application.job.title_en}',
            message=f'New application received for {application.job.title_en}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[employer_email],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as exc:
        logger.error(f'Failed to send application notification: {exc}')
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_application_status_update(self, application_id: str, new_status: str):
    """Notify candidate about application status change."""
    from apps.applications.models import Application
    try:
        application = Application.objects.select_related('job__employer', 'candidate__user').get(id=application_id)
        candidate_email = application.candidate.user.email
        html_message = render_to_string('emails/application_status.html', {
            'application': application,
            'job': application.job,
            'new_status': new_status,
            'company_name': application.job.employer.company_name,
        })
        send_mail(
            subject=f'Application Update: {application.job.title_en}',
            message=f'Your application for {application.job.title_en} has been updated to: {new_status}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[candidate_email],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as exc:
        logger.error(f'Failed to send status update email: {exc}')
        raise self.retry(exc=exc)


@shared_task
def send_job_alert_emails():
    """Process and send job alert digests."""
    from apps.notifications.models import JobAlert
    from apps.jobs.models import JobListing
    from django.utils import timezone
    from datetime import timedelta

    now = timezone.now()
    daily_alerts = JobAlert.objects.filter(is_active=True, frequency='daily')

    for alert in daily_alerts:
        jobs = JobListing.objects.filter(
            status='published',
            created_at__gte=now - timedelta(days=1),
        )
        if alert.keywords:
            jobs = jobs.filter(title_en__icontains=alert.keywords)
        if alert.category:
            jobs = jobs.filter(category=alert.category)

        matching_jobs = jobs[:10]
        if matching_jobs.exists():
            html_message = render_to_string('emails/job_alert.html', {
                'alert': alert,
                'jobs': matching_jobs,
            })
            send_mail(
                subject=f'Job Alert: {alert.name}',
                message=f'{matching_jobs.count()} new jobs matching your alert "{alert.name}"',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[alert.user.email],
                html_message=html_message,
                fail_silently=True,
            )

    logger.info(f'Processed {daily_alerts.count()} daily job alerts')


@shared_task
def cleanup_expired_jobs():
    """Mark expired jobs as closed."""
    from apps.jobs.models import JobListing
    from django.utils import timezone

    expired = JobListing.objects.filter(
        status='published',
        deadline__lt=timezone.now(),
    ).update(status='expired')

    logger.info(f'Marked {expired} jobs as expired')


@shared_task
def update_search_index():
    """Rebuild OpenSearch index for jobs."""
    logger.info('Search index update triggered')
    # TODO: Implement OpenSearch indexing
