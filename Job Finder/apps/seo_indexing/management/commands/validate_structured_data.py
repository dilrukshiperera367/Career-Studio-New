"""
Management command: validate_structured_data

Fetches the live structured data endpoint for each active job page
and validates it against Google's JobPosting schema requirements.
Results are stored in StructuredDataValidation records.

Usage:
    python manage.py validate_structured_data
    python manage.py validate_structured_data --limit 50
    python manage.py validate_structured_data --type job
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.jobs.models import JobListing
from apps.seo_indexing.models import StructuredDataValidation

REQUIRED_JOB_FIELDS = [
    "title", "description", "datePosted",
    "hiringOrganization", "jobLocation", "identifier",
]
RECOMMENDED_JOB_FIELDS = [
    "validThrough", "employmentType", "baseSalary",
    "applicantLocationRequirements",
]


def _validate_job_posting_data(data: dict) -> tuple[list, list]:
    """Returns (errors, warnings) lists for a JobPosting JSON-LD dict."""
    errors = []
    warnings = []

    if data.get("@type") != "JobPosting":
        errors.append("@type must be 'JobPosting'")

    for field in REQUIRED_JOB_FIELDS:
        if not data.get(field):
            errors.append(f"Required field missing: {field}")

    for field in RECOMMENDED_JOB_FIELDS:
        if not data.get(field):
            warnings.append(f"Recommended field missing: {field}")

    # Description should be at least 100 chars
    desc = (data.get("description") or "").strip().replace("<", "").replace(">", "")
    if len(desc) < 100:
        warnings.append(f"description too short ({len(desc)} chars); Google requires meaningful content")

    # datePosted should be ISO 8601
    dp = data.get("datePosted", "")
    if dp and len(dp) != 10:
        warnings.append("datePosted should be YYYY-MM-DD format")

    # baseSalary currency must be ISO 4217
    salary = data.get("baseSalary", {})
    if salary:
        currency = salary.get("currency", "")
        if len(currency) != 3:
            warnings.append(f"baseSalary.currency '{currency}' may not be ISO 4217")

    return errors, warnings


class Command(BaseCommand):
    help = "Validate JobPosting structured data for active job pages."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=200, help="Max jobs to validate")
        parser.add_argument("--type", choices=["job"], default="job")

    def handle(self, *args, **options):
        from apps.seo_indexing.views import build_job_posting_json_ld

        limit = options["limit"]
        jobs = JobListing.objects.filter(status="active").select_related(
            "employer", "district"
        )[:limit]

        valid_count = 0
        warning_count = 0
        error_count = 0

        for job in jobs:
            try:
                data = build_job_posting_json_ld(job)
                errors, warnings = _validate_job_posting_data(data)

                if errors:
                    sd_status = "errors"
                    error_count += 1
                elif warnings:
                    sd_status = "warnings"
                    warning_count += 1
                else:
                    sd_status = "valid"
                    valid_count += 1

                StructuredDataValidation.objects.update_or_create(
                    page_type="job", slug=job.slug,
                    defaults={
                        "status": sd_status,
                        "errors": errors,
                        "warnings": warnings,
                        "validated_at": timezone.now(),
                    },
                )
                if errors:
                    self.stdout.write(self.style.ERROR(f"  ERRORS {job.slug}: {errors}"))
                elif warnings:
                    self.stdout.write(f"  WARN {job.slug}: {warnings}")
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"  Exception on {job.slug}: {exc}"))
                error_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Validation complete: {valid_count} valid, {warning_count} warnings, {error_count} errors"
            )
        )
