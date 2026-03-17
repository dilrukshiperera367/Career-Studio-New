"""Candidate utility services — data quality, validation, cleanup, and enrichment."""

import re
import logging
from typing import Optional
from django.utils import timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Contact Info Validation (Feature 128)
# ---------------------------------------------------------------------------

def validate_email(email: str) -> dict:
    """Validate email format and return result."""
    if not email:
        return {"valid": False, "reason": "empty"}
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    is_valid = bool(re.match(pattern, email.strip()))
    return {"valid": is_valid, "reason": "" if is_valid else "invalid_format"}


def validate_phone(phone: str) -> dict:
    """Validate phone number format."""
    if not phone:
        return {"valid": False, "reason": "empty"}
    cleaned = re.sub(r'[\s\-\(\)\+]', '', phone)
    is_valid = len(cleaned) >= 7 and cleaned.isdigit()
    return {"valid": is_valid, "reason": "" if is_valid else "invalid_format"}


def validate_candidate_contacts(tenant_id: str, candidate_id: str) -> dict:
    """Validate all contact info for a candidate."""
    from apps.candidates.models import Candidate

    try:
        c = Candidate.objects.get(id=candidate_id, tenant_id=tenant_id)
    except Candidate.DoesNotExist:
        return {"error": "Not found"}

    return {
        "candidate_id": str(c.id),
        "email": validate_email(c.primary_email or ""),
        "phone": validate_phone(c.primary_phone or ""),
        "has_linkedin": bool(c.linkedin_url),
    }


# ---------------------------------------------------------------------------
# Resume Completeness Score (Feature 123)
# ---------------------------------------------------------------------------

def compute_resume_completeness(tenant_id: str, candidate_id: str) -> float:
    """
    Calculate how complete a candidate's parsed profile is (0-100).
    Checks: email, phone, skills, experience, education, headline, location.
    """
    from apps.candidates.models import Candidate

    try:
        c = Candidate.objects.get(id=candidate_id, tenant_id=tenant_id)
    except Candidate.DoesNotExist:
        return 0.0

    score = 0.0
    checks = {
        "full_name": bool(c.full_name and len(c.full_name) > 1),
        "email": bool(c.primary_email),
        "phone": bool(c.primary_phone),
        "headline": bool(c.headline),
        "location": bool(c.location),
        "skills": c.skills.exists(),
        "experience": c.experiences.exists(),
        "education": c.education.exists(),
        "recent_title": bool(c.most_recent_title),
        "recent_company": bool(c.most_recent_company),
    }

    filled = sum(1 for v in checks.values() if v)
    score = round(filled / len(checks) * 100, 1)

    # Update the field
    if c.resume_completeness != score:
        c.resume_completeness = score
        c.save(update_fields=["resume_completeness", "updated_at"])

    return score


# ---------------------------------------------------------------------------
# Stale Data Flagging (Feature 130)
# ---------------------------------------------------------------------------

def flag_stale_candidates(tenant_id: str, stale_days: int = 365) -> int:
    """Flag candidates whose data hasn't been updated in stale_days."""
    from apps.candidates.models import Candidate
    import datetime

    cutoff = timezone.now() - datetime.timedelta(days=stale_days)
    stale = Candidate.objects.filter(
        tenant_id=tenant_id,
        status="active",
        updated_at__lt=cutoff,
    ).exclude(tags__contains=["stale_data"])

    flagged = 0
    for c in stale[:500]:
        c.tags = (c.tags or []) + ["stale_data"]
        c.save(update_fields=["tags", "updated_at"])
        flagged += 1

    logger.info(f"Flagged {flagged} stale candidates for tenant {tenant_id}")
    return flagged


# ---------------------------------------------------------------------------
# Bulk Data Cleanup (Feature 132)
# ---------------------------------------------------------------------------

def bulk_data_cleanup(tenant_id: str) -> dict:
    """Find and report data quality issues across all candidates."""
    from apps.candidates.models import Candidate

    candidates = Candidate.objects.filter(tenant_id=tenant_id, status="active")

    issues = {
        "empty_names": [],
        "empty_emails": [],
        "invalid_emails": [],
        "invalid_phones": [],
        "duplicate_emails": [],
        "no_skills": [],
    }

    # Find empty names
    issues["empty_names"] = list(
        candidates.filter(full_name="").values_list("id", flat=True)[:50]
    )

    # Find empty emails
    issues["empty_emails"] = list(
        candidates.filter(primary_email__isnull=True).values_list("id", flat=True)[:50]
    )

    # Find invalid emails
    for c in candidates.exclude(primary_email__isnull=True).exclude(primary_email="")[:500]:
        if not validate_email(c.primary_email)["valid"]:
            issues["invalid_emails"].append(str(c.id))

    # Find invalid phones
    for c in candidates.exclude(primary_phone="")[:500]:
        if not validate_phone(c.primary_phone)["valid"]:
            issues["invalid_phones"].append(str(c.id))

    # Duplicate emails
    from django.db.models import Count
    dupes = candidates.values("primary_email").annotate(
        cnt=Count("id")
    ).filter(cnt__gt=1).exclude(primary_email__isnull=True)
    issues["duplicate_emails"] = [d["primary_email"] for d in dupes[:20]]

    # Candidates with no skills parsed
    ids_with_skills = set(
        candidates.filter(skills__isnull=False).values_list("id", flat=True).distinct()[:500]
    )
    issues["no_skills"] = list(
        candidates.exclude(id__in=ids_with_skills).values_list("id", flat=True)[:50]
    )

    # Convert UUIDs to strings
    for key in issues:
        issues[key] = [str(x) for x in issues[key]]

    return {
        "tenant_id": tenant_id,
        "total_candidates": candidates.count(),
        "issues": issues,
        "issue_counts": {k: len(v) for k, v in issues.items()},
    }


# ---------------------------------------------------------------------------
# Right to Deletion / GDPR Purge (Feature 134)
# ---------------------------------------------------------------------------

def purge_candidate_data(tenant_id: str, candidate_id: str, actor_id: str = None) -> dict:
    """
    GDPR: purge all PII for a candidate. Anonymizes instead of hard-deleting
    to preserve referential integrity.
    """
    from apps.candidates.models import (
        Candidate, CandidateIdentity, ResumeDocument,
        CandidateNote, CandidateCertification,
    )
    from apps.messaging.models import Message

    try:
        candidate = Candidate.objects.get(id=candidate_id, tenant_id=tenant_id)
    except Candidate.DoesNotExist:
        return {"error": "Candidate not found"}

    # Anonymize candidate
    candidate.full_name = "[DELETED]"
    candidate.primary_email = None
    candidate.primary_phone = ""
    candidate.headline = ""
    candidate.location = ""
    candidate.linkedin_url = ""
    candidate.github_url = ""
    candidate.portfolio_url = ""
    candidate.most_recent_title = ""
    candidate.most_recent_company = ""
    candidate.tags = ["gdpr_purged"]
    candidate.status = "deleted"
    candidate.save()

    # Delete identities
    deleted_identities = CandidateIdentity.objects.filter(candidate=candidate).delete()[0]

    # Delete resume files/text
    deleted_resumes = ResumeDocument.objects.filter(candidate=candidate).update(
        raw_text="[PURGED]", clean_text="[PURGED]", parsed_json=None, file_url=""
    )

    # Delete notes
    deleted_notes = CandidateNote.objects.filter(candidate=candidate).delete()[0]

    # Delete certifications
    deleted_certs = CandidateCertification.objects.filter(candidate=candidate).delete()[0]

    # Anonymize messages
    Message.objects.filter(candidate=candidate).update(
        body="[PURGED]", subject="[PURGED]"
    )

    return {
        "candidate_id": str(candidate_id),
        "status": "purged",
        "deleted_identities": deleted_identities,
        "purged_resumes": deleted_resumes,
        "deleted_notes": deleted_notes,
        "deleted_certifications": deleted_certs,
    }


# ---------------------------------------------------------------------------
# @Mention Parsing (Feature 101)
# ---------------------------------------------------------------------------

def parse_mentions(text: str) -> list:
    """Parse @mentions from note text. Returns list of email-like strings."""
    pattern = r'@([a-zA-Z0-9._%+-]+(?:@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})?)'
    return re.findall(pattern, text)


def process_note_mentions(tenant_id: str, note_id: str):
    """Process @mentions in a note and create notifications."""
    from apps.candidates.models import CandidateNote
    from apps.accounts.models import User, Notification

    try:
        note = CandidateNote.objects.get(id=note_id, tenant_id=tenant_id)
    except CandidateNote.DoesNotExist:
        return

    mentions = parse_mentions(note.content)
    if not mentions:
        return

    # Find mentioned users
    user_ids = []
    for mention in mentions:
        users = User.objects.filter(
            tenant_id=tenant_id,
            email__icontains=mention,
            is_active=True,
        )
        for user in users:
            if str(user.id) not in user_ids:
                user_ids.append(str(user.id))
                Notification.objects.create(
                    tenant_id=tenant_id,
                    user=user,
                    type="mention",
                    title=f"You were mentioned in a note",
                    body=f"{note.author} mentioned you on {note.candidate.full_name}'s profile",
                    entity_type="candidate",
                    entity_id=note.candidate_id,
                )

    # Update note mentions field
    note.mentions = user_ids
    note.save(update_fields=["mentions"])


# ---------------------------------------------------------------------------
# Interview Conflict Detection (Feature 60)
# ---------------------------------------------------------------------------

def check_interview_conflicts(
    tenant_id: str, interviewer_id: str, date, start_time, end_time=None
) -> list:
    """Check if interviewer has conflicts at the proposed time."""
    from apps.applications.models import Interview

    conflicts = Interview.objects.filter(
        tenant_id=tenant_id,
        interviewer_id=interviewer_id,
        date=date,
        status__in=["scheduled", "confirmed"],
    ).exclude(
        status__in=["cancelled", "no_show"]
    )

    # If we have times, check overlap
    if start_time:
        conflicts = conflicts.filter(time__isnull=False)
        overlap = []
        for interview in conflicts:
            if interview.time:
                # Simple: if same date and time within 1 hour
                from datetime import timedelta
                interview_end = (
                    timezone.datetime.combine(date, interview.time) + timedelta(hours=1)
                ).time()
                if start_time < interview_end and (end_time or start_time) > interview.time:
                    overlap.append({
                        "interview_id": str(interview.id),
                        "candidate": interview.candidate.full_name if interview.candidate else "",
                        "time": str(interview.time),
                        "type": interview.interview_type,
                    })
        return overlap

    return [
        {
            "interview_id": str(i.id),
            "candidate": i.candidate.full_name if i.candidate else "",
            "time": str(i.time) if i.time else None,
            "type": i.interview_type,
        }
        for i in conflicts
    ]


# ---------------------------------------------------------------------------
# Cost-per-Hire Tracking (Feature 16)
# ---------------------------------------------------------------------------

def calculate_cost_per_hire(tenant_id: str, job_id: str = None) -> dict:
    """Estimate cost-per-hire based on recruiter time and process metrics."""
    from apps.applications.models import Application, Interview
    from apps.jobs.models import Job
    from django.db.models import Count

    filters = {"tenant_id": tenant_id}
    if job_id:
        filters["job_id"] = job_id

    hired = Application.objects.filter(**filters, status="hired")
    total_hired = hired.count()

    if total_hired == 0:
        return {"total_hired": 0, "estimated_cost_per_hire": None}

    # Estimate based on interviews conducted
    interview_filters = {"tenant_id": tenant_id}
    if job_id:
        interview_filters["job_id"] = job_id
    total_interviews = Interview.objects.filter(**interview_filters).count()

    # Rough estimation: 2h per interview * hourly cost estimate
    hourly_cost = 75  # configurable per tenant
    interview_cost = total_interviews * 2 * hourly_cost

    # Screening time estimate: 15 min per application
    total_apps = Application.objects.filter(**filters).count()
    screening_cost = total_apps * 0.25 * hourly_cost

    total_cost = interview_cost + screening_cost
    cost_per_hire = round(total_cost / total_hired, 2)

    return {
        "total_hired": total_hired,
        "total_applications": total_apps,
        "total_interviews": total_interviews,
        "estimated_total_cost": total_cost,
        "estimated_cost_per_hire": cost_per_hire,
    }


# ---------------------------------------------------------------------------
# Buddy/Mentor Auto-Suggest (Feature 176)
# ---------------------------------------------------------------------------

def suggest_buddy(tenant_id: str, employee_id: str) -> list:
    """Suggest buddy/mentor from same department who joined 6+ months ago."""
    from apps.applications.models import Employee
    import datetime

    try:
        new_hire = Employee.objects.get(id=employee_id, tenant_id=tenant_id)
    except Employee.DoesNotExist:
        return []

    six_months_ago = timezone.now().date() - datetime.timedelta(days=180)

    suggestions = Employee.objects.filter(
        tenant_id=tenant_id,
        department=new_hire.department,
        status="active",
        hire_date__lte=six_months_ago,
    ).exclude(id=employee_id).order_by("hire_date")[:5]

    return [
        {
            "employee_id": str(e.id),
            "name": e.candidate.full_name,
            "title": e.title,
            "hire_date": str(e.hire_date) if e.hire_date else None,
            "department": e.department,
        }
        for e in suggestions
    ]


# ---------------------------------------------------------------------------
# Early Attrition Alert (Feature 179)
# ---------------------------------------------------------------------------

def check_early_attrition(tenant_id: str) -> list:
    """Find employees who left within 90 days — flag for review."""
    from apps.applications.models import Employee
    import datetime

    alerts = []
    terminated = Employee.objects.filter(
        tenant_id=tenant_id,
        status__in=["terminated", "resigned"],
        termination_date__isnull=False,
        hire_date__isnull=False,
    )

    for emp in terminated:
        tenure_days = (emp.termination_date - emp.hire_date).days
        if tenure_days <= 90:
            alerts.append({
                "employee_id": str(emp.id),
                "name": emp.candidate.full_name,
                "hire_date": str(emp.hire_date),
                "termination_date": str(emp.termination_date),
                "tenure_days": tenure_days,
                "reason": emp.termination_reason,
                "source": emp.application.source if emp.application else "unknown",
            })

    return alerts
