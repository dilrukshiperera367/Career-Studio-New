"""Management command: detect and group duplicate job listings across ATS feeds and direct posts."""
import hashlib
import re
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.jobs.models import JobListing
from apps.job_quality.models import DuplicateJobGroup, JobQualityScore


def _normalize_title(title: str) -> str:
    """Lowercase, remove punctuation, strip common noise words."""
    title = title.lower()
    title = re.sub(r"[^a-z0-9\s]", "", title)
    noise = {"a", "an", "the", "for", "at", "in", "to", "and", "of", "or", "is", "we", "are"}
    words = [w for w in title.split() if w not in noise]
    return " ".join(sorted(words))  # sorted for canonical form


def _title_hash(title: str, employer_id) -> str:
    normalized = _normalize_title(title)
    return hashlib.md5(f"{normalized}::{employer_id}".encode()).hexdigest()


def _location_key(job) -> str:
    return str(job.district_id or "remote") + str(job.work_arrangement or "")


class Command(BaseCommand):
    help = "Detect duplicate job listings and group them. Marks duplicates in JobQualityScore."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Print duplicate groups without saving."
        )
        parser.add_argument(
            "--employer-id", type=int,
            help="Limit dedup to a single employer."
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        employer_filter = options.get("employer_id")

        qs = JobListing.objects.filter(status__in=["active", "closed"]).select_related(
            "employer", "district"
        )
        if employer_filter:
            qs = qs.filter(employer_id=employer_filter)

        self.stdout.write(f"Scanning {qs.count()} jobs for duplicates...")

        # Group by (title_hash, employer_id, location_key)
        groups: dict[str, list] = {}
        for job in qs.iterator(chunk_size=500):
            key = f"{_title_hash(job.title or '', job.employer_id)}::{_location_key(job)}"
            groups.setdefault(key, []).append(job)

        dup_count = 0
        group_count = 0

        for key, jobs in groups.items():
            if len(jobs) < 2:
                continue

            group_count += 1
            dup_count += len(jobs) - 1

            if dry_run:
                self.stdout.write(
                    f"  DUP GROUP [{len(jobs)} jobs]: "
                    f"{jobs[0].title[:60]} @ {jobs[0].employer.company_name}"
                )
                for j in jobs:
                    self.stdout.write(f"    - {j.id} published={j.published_at}")
                continue

            # Save group — canonical = most recent
            canonical = max(jobs, key=lambda j: j.published_at or j.id.int)
            job_ids = [str(j.id) for j in jobs]

            with transaction.atomic():
                group, _ = DuplicateJobGroup.objects.update_or_create(
                    canonical_job=canonical,
                    defaults={
                        "job_ids": job_ids,
                        "detection_method": "title_similarity",
                        "similarity_score": 0.95,
                    },
                )

                # Mark all non-canonical as duplicates in quality score
                for job in jobs:
                    is_dup = job.id != canonical.id
                    JobQualityScore.objects.update_or_create(
                        job=job,
                        defaults={
                            "is_duplicate": is_dup,
                            "duplicate_group_id": group.id,
                        },
                    )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY RUN] Found {group_count} duplicate groups ({dup_count} duplicates)."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Dedup complete: {group_count} groups, {dup_count} duplicates marked."
                )
            )
