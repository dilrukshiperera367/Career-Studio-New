"""Workflow utility services — auto-rejection, auto-advance, reminders, digest, probation."""

import logging
import datetime
from django.utils import timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Auto-Rejection After SLA (Feature 27)
# ---------------------------------------------------------------------------

def process_sla_auto_rejections(tenant_id: str = None) -> int:
    """
    Auto-reject candidates who sit in a stage beyond SLA days.
    Sends 'we'll keep your resume on file' email.
    """
    from apps.applications.models import Application
    from apps.jobs.models import PipelineStage
    from apps.messaging.services import queue_email

    filters = {"status": "active"}
    if tenant_id:
        filters["tenant_id"] = tenant_id

    rejected = 0
    # Find stages with SLA configured
    stages = PipelineStage.objects.filter(sla_days__isnull=False, sla_days__gt=0)

    for stage in stages:
        cutoff = timezone.now() - datetime.timedelta(days=stage.sla_days)
        stale_apps = Application.objects.filter(
            job=stage.job,
            current_stage=stage.name,
            status="active",
            updated_at__lt=cutoff,
            tenant_id=stage.tenant_id,
        )

        for app in stale_apps[:100]:
            app.status = "rejected"
            app.rejection_reason = "sla_expired"
            app.rejection_notes = f"Auto-rejected: exceeded {stage.sla_days}-day SLA in {stage.name}"
            app.save(update_fields=["status", "rejection_reason", "rejection_notes", "updated_at"])

            # Send auto-rejection email
            try:
                queue_email(
                    tenant_id=str(app.tenant_id),
                    template_slug="sla_auto_rejection",
                    candidate_id=str(app.candidate_id),
                    context={"job_title": app.job.title if app.job else "", "stage": stage.name},
                )
            except Exception as e:
                logger.error(f"SLA rejection email failed for {app.id}: {e}")

            rejected += 1

    logger.info(f"SLA auto-rejected {rejected} applications")
    return rejected


# ---------------------------------------------------------------------------
# Auto-Advance on Scorecard (Features 48, 149)
# ---------------------------------------------------------------------------

def process_auto_advance(tenant_id: str = None) -> int:
    """
    After all interviewers submit feedback, auto-advance if avg rating >= 4.
    Also: score > threshold → skip screening.
    """
    from apps.applications.models import Application, Interview, InterviewPanel
    from apps.applications.models import StageHistory

    filters = {"status__in": ["scheduled", "confirmed", "completed"]}
    if tenant_id:
        filters["tenant_id"] = tenant_id

    advanced = 0
    # Find completed interviews where all panelists submitted
    interviews = Interview.objects.filter(
        status="completed",
        decision__isnull=True,
        **({k: v for k, v in filters.items() if k != "status__in"})
    )

    for interview in interviews[:200]:
        panels = InterviewPanel.objects.filter(interview=interview)
        if not panels.exists():
            continue

        all_submitted = all(p.status == "submitted" for p in panels)
        if not all_submitted:
            continue

        ratings = [p.rating for p in panels if p.rating is not None]
        if not ratings:
            continue

        avg_rating = sum(ratings) / len(ratings)

        app = interview.application
        if not app or app.status != "active":
            continue

        if avg_rating >= 4.0:
            # Auto-advance to next stage
            from apps.jobs.models import PipelineStage
            next_stage = PipelineStage.objects.filter(
                job=app.job,
                order__gt=PipelineStage.objects.filter(
                    job=app.job, name=app.current_stage
                ).values_list("order", flat=True).first() or 0,
            ).order_by("order").first()

            if next_stage:
                old_stage = app.current_stage
                app.current_stage = next_stage.name
                app.save(update_fields=["current_stage", "updated_at"])

                StageHistory.objects.create(
                    tenant_id=app.tenant_id,
                    application=app,
                    from_stage=old_stage,
                    to_stage=next_stage.name,
                    changed_by=None,
                    reason=f"Auto-advanced: avg interview rating {avg_rating:.1f}/5",
                )

                interview.decision = "advance"
                interview.save(update_fields=["decision", "updated_at"])
                advanced += 1

    logger.info(f"Auto-advanced {advanced} applications")
    return advanced


# ---------------------------------------------------------------------------
# Interview Reminders (Feature 61)
# ---------------------------------------------------------------------------

def send_interview_reminders() -> int:
    """Send reminder emails 24h and 1h before interviews."""
    from apps.applications.models import Interview
    from apps.messaging.services import queue_email

    sent = 0
    now = timezone.now()

    # 24-hour reminders
    tomorrow = now + datetime.timedelta(hours=24)
    upcoming_24h = Interview.objects.filter(
        date=tomorrow.date(),
        status__in=["scheduled", "confirmed"],
    ).select_related("candidate", "application__job")

    for interview in upcoming_24h[:200]:
        try:
            queue_email(
                tenant_id=str(interview.tenant_id),
                template_slug="interview_reminder_24h",
                candidate_id=str(interview.candidate_id),
                context={
                    "interview_date": str(interview.date),
                    "interview_time": str(interview.time) if interview.time else "TBD",
                    "interview_type": interview.interview_type,
                    "job_title": interview.application.job.title if interview.application and interview.application.job else "",
                },
            )
            sent += 1
        except Exception as e:
            logger.error(f"Interview reminder failed: {e}")

    # 1-hour reminders (same logic but for today)
    one_hour = now + datetime.timedelta(hours=1)
    upcoming_1h = Interview.objects.filter(
        date=one_hour.date(),
        time__lte=one_hour.time(),
        time__gt=now.time(),
        status__in=["scheduled", "confirmed"],
    ).select_related("candidate")

    for interview in upcoming_1h[:200]:
        try:
            queue_email(
                tenant_id=str(interview.tenant_id),
                template_slug="interview_reminder_1h",
                candidate_id=str(interview.candidate_id),
                context={
                    "interview_time": str(interview.time) if interview.time else "TBD",
                    "interview_type": interview.interview_type,
                },
            )
            sent += 1
        except Exception as e:
            logger.error(f"1h reminder failed: {e}")

    logger.info(f"Sent {sent} interview reminders")
    return sent


# ---------------------------------------------------------------------------
# Feedback Deadline Nudge (Feature 63)
# ---------------------------------------------------------------------------

def send_feedback_nudges() -> int:
    """Nudge interviewers who haven't submitted feedback within 48h."""
    from apps.applications.models import Interview, InterviewPanel
    from apps.accounts.models import Notification

    sent = 0
    cutoff = timezone.now() - datetime.timedelta(hours=48)

    overdue_panels = InterviewPanel.objects.filter(
        interview__status="completed",
        interview__updated_at__lt=cutoff,
        status="pending",
    ).select_related("interview", "interviewer")

    for panel in overdue_panels[:200]:
        Notification.objects.get_or_create(
            tenant_id=panel.interview.tenant_id,
            user=panel.interviewer,
            type="feedback_overdue",
            entity_type="interview",
            entity_id=panel.interview_id,
            defaults={
                "title": "Interview Feedback Overdue",
                "body": f"Please submit your feedback for the interview on {panel.interview.date}. "
                        f"It has been over 48 hours.",
            },
        )
        sent += 1

    logger.info(f"Sent {sent} feedback nudges")
    return sent


# ---------------------------------------------------------------------------
# Weekly Digest Email (Feature 111)
# ---------------------------------------------------------------------------

def send_weekly_digest(tenant_id: str = None) -> int:
    """Send weekly summary to each recruiter: new applicants, pending actions, upcoming interviews."""
    from apps.accounts.models import User
    from apps.applications.models import Application, Interview
    from apps.messaging.services import queue_email

    sent = 0
    now = timezone.now()
    week_ago = now - datetime.timedelta(days=7)
    next_week = now + datetime.timedelta(days=7)

    filters = {"user_type__in": ["recruiter", "company_admin"], "is_active": True}
    if tenant_id:
        filters["tenant_id"] = tenant_id

    recruiters = User.objects.filter(**filters)

    for recruiter in recruiters[:100]:
        # New applicants this week
        new_apps = Application.objects.filter(
            tenant_id=recruiter.tenant_id,
            created_at__gte=week_ago,
        ).count()

        # Pending actions (applications in active status assigned to recruiter)
        pending = Application.objects.filter(
            tenant_id=recruiter.tenant_id,
            assigned_recruiter=recruiter,
            status="active",
        ).count()

        # Upcoming interviews
        upcoming = Interview.objects.filter(
            tenant_id=recruiter.tenant_id,
            interviewer=recruiter,
            date__gte=now.date(),
            date__lte=next_week.date(),
            status__in=["scheduled", "confirmed"],
        ).count()

        context = {
            "recruiter_name": recruiter.first_name,
            "new_applications": new_apps,
            "pending_actions": pending,
            "upcoming_interviews": upcoming,
            "week_start": week_ago.strftime("%b %d"),
            "week_end": now.strftime("%b %d, %Y"),
        }

        try:
            queue_email(
                tenant_id=str(recruiter.tenant_id),
                template_slug="weekly_digest",
                candidate_id=None,
                context=context,
                sender_id=str(recruiter.id),
            )
            sent += 1
        except Exception as e:
            logger.error(f"Weekly digest failed for {recruiter.email}: {e}")

    logger.info(f"Sent {sent} weekly digests")
    return sent


# ---------------------------------------------------------------------------
# Auto-Acknowledgment (Feature 74)
# ---------------------------------------------------------------------------

def send_application_acknowledgment(tenant_id: str, application_id: str):
    """Instantly send 'Application Received' email upon application submission."""
    from apps.applications.models import Application
    from apps.messaging.services import queue_email

    try:
        app = Application.objects.select_related("job", "candidate").get(
            id=application_id, tenant_id=tenant_id
        )
    except Application.DoesNotExist:
        return

    queue_email(
        tenant_id=tenant_id,
        template_slug="application_received",
        candidate_id=str(app.candidate_id),
        context={
            "candidate_name": app.candidate.full_name if app.candidate else "",
            "job_title": app.job.title if app.job else "",
        },
    )
    logger.info(f"Sent application acknowledgment for {application_id}")


# ---------------------------------------------------------------------------
# Probation Check-In (Feature 18)
# ---------------------------------------------------------------------------

def process_probation_milestones(tenant_id: str = None) -> int:
    """Send reminders at 30/60/90 day check-ins after hire."""
    from apps.applications.models import Employee
    from apps.accounts.models import Notification

    sent = 0
    today = timezone.now().date()

    filters = {"status": "probation", "hire_date__isnull": False}
    if tenant_id:
        filters["tenant_id"] = tenant_id

    employees = Employee.objects.filter(**filters).select_related("candidate", "manager")

    for emp in employees:
        days_since_hire = (today - emp.hire_date).days

        for milestone in [30, 60, 90]:
            if days_since_hire == milestone and emp.manager:
                Notification.objects.get_or_create(
                    tenant_id=emp.tenant_id,
                    user=emp.manager,
                    type="probation_milestone",
                    entity_type="employee",
                    entity_id=emp.id,
                    defaults={
                        "title": f"{milestone}-Day Check-In Due",
                        "body": f"{emp.candidate.full_name}'s {milestone}-day probation check-in is due today.",
                    },
                )
                sent += 1

    logger.info(f"Sent {sent} probation milestone reminders")
    return sent


# ---------------------------------------------------------------------------
# Training Assignment Logic (Feature 174)
# ---------------------------------------------------------------------------

def auto_assign_training(tenant_id: str, employee_id: str) -> int:
    """Auto-assign mandatory training tasks based on role/department."""
    from apps.applications.models import Employee, OnboardingTask

    try:
        emp = Employee.objects.get(id=employee_id, tenant_id=tenant_id)
    except Employee.DoesNotExist:
        return 0

    # Default mandatory training modules
    mandatory_training = [
        {"title": "Security Awareness Training", "category": "training", "description": "Complete mandatory security awareness course."},
        {"title": "Code of Conduct", "category": "training", "description": "Review and acknowledge the company code of conduct."},
        {"title": "Data Privacy (GDPR/CCPA)", "category": "training", "description": "Complete data privacy compliance training."},
    ]

    # Department-specific training
    dept_training = {
        "engineering": [
            {"title": "Development Environment Setup", "category": "it", "description": "Set up local dev environment, access repositories."},
            {"title": "Code Review Guidelines", "category": "training", "description": "Review the team's code review standards."},
        ],
        "sales": [
            {"title": "CRM System Training", "category": "training", "description": "Learn the CRM system and processes."},
            {"title": "Product Knowledge Course", "category": "training", "description": "Complete product knowledge certification."},
        ],
    }

    created = 0
    all_training = mandatory_training + dept_training.get(emp.department.lower(), [])

    due_date = None
    if emp.start_date:
        due_date = emp.start_date + datetime.timedelta(days=30)

    for t in all_training:
        _, was_created = OnboardingTask.objects.get_or_create(
            tenant_id=tenant_id,
            employee=emp,
            title=t["title"],
            defaults={
                "description": t["description"],
                "category": t["category"],
                "due_date": due_date,
            },
        )
        if was_created:
            created += 1

    return created


# ---------------------------------------------------------------------------
# New Hire Satisfaction Survey (Feature 177)
# ---------------------------------------------------------------------------

def trigger_satisfaction_survey(tenant_id: str = None) -> int:
    """At 30 days, auto-send survey to new hires."""
    from apps.applications.models import Employee
    from apps.messaging.services import queue_email

    sent = 0
    today = timezone.now().date()

    filters = {"status__in": ["probation", "active"], "hire_date__isnull": False}
    if tenant_id:
        filters["tenant_id"] = tenant_id

    employees = Employee.objects.filter(**filters).select_related("candidate")

    for emp in employees:
        days_since_hire = (today - emp.hire_date).days
        if days_since_hire == 30 and emp.satisfaction_score is None:
            try:
                queue_email(
                    tenant_id=str(emp.tenant_id),
                    template_slug="new_hire_survey_30d",
                    candidate_id=str(emp.candidate_id),
                    context={
                        "employee_name": emp.candidate.full_name,
                        "hire_date": str(emp.hire_date),
                    },
                )
                sent += 1
            except Exception as e:
                logger.error(f"Survey send failed for employee {emp.id}: {e}")

    logger.info(f"Sent {sent} satisfaction surveys")
    return sent
