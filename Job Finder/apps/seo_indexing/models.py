"""SEO Indexing — structured data, sitemap entries, Indexing API logs, validation."""
import uuid
from django.db import models


class SitemapEntry(models.Model):
    """Tracks sitemap-indexed public pages."""
    class PageType(models.TextChoices):
        JOB = "job", "Job Listing"
        COMPANY = "company", "Company Page"
        CATEGORY = "category", "Category Page"
        CITY = "city", "City Page"
        SALARY = "salary", "Salary Page"
        BLOG = "blog", "Blog Post"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    page_type = models.CharField(max_length=10, choices=PageType.choices)
    slug = models.CharField(max_length=300)
    url = models.URLField(max_length=500)
    last_modified = models.DateTimeField(auto_now=True)
    change_frequency = models.CharField(
        max_length=10,
        choices=[("always", "Always"), ("hourly", "Hourly"), ("daily", "Daily"),
                 ("weekly", "Weekly"), ("monthly", "Monthly"), ("never", "Never")],
        default="daily",
    )
    priority = models.FloatField(default=0.5)
    is_indexable = models.BooleanField(default=True)
    is_expired = models.BooleanField(default=False)

    class Meta:
        db_table = "jf_sitemap_entries"
        unique_together = ["page_type", "slug"]
        ordering = ["-last_modified"]

    def __str__(self):
        return f"{self.get_page_type_display()}: {self.slug}"


class IndexingAPILog(models.Model):
    """Logs Google Indexing API calls for job additions and removals."""
    class Action(models.TextChoices):
        URL_UPDATED = "URL_UPDATED", "URL Updated (Added/Modified)"
        URL_DELETED = "URL_DELETED", "URL Deleted (Removed)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url = models.URLField(max_length=500)
    action = models.CharField(max_length=15, choices=Action.choices)
    http_status = models.IntegerField(null=True, blank=True)
    response_body = models.JSONField(default=dict, blank=True)
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_indexing_api_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["url", "-created_at"], name="idx_indexing_url"),
        ]

    def __str__(self):
        return f"{self.action} {self.url[:60]} ({'OK' if self.success else 'FAIL'})"


class StructuredDataValidation(models.Model):
    """Validation results for job/company structured data."""
    class Status(models.TextChoices):
        VALID = "valid", "Valid"
        WARNINGS = "warnings", "Has Warnings"
        ERRORS = "errors", "Has Errors"
        PENDING = "pending", "Pending Validation"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    page_type = models.CharField(max_length=10)
    slug = models.CharField(max_length=300)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    warnings = models.JSONField(default=list)
    errors = models.JSONField(default=list)
    validated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_structured_data_validations"
        unique_together = ["page_type", "slug"]
        ordering = ["-validated_at"]

    def __str__(self):
        return f"SDV {self.page_type}/{self.slug}: {self.status}"


class CrawlHealthSnapshot(models.Model):
    """Daily crawl health snapshot for monitoring."""
    date = models.DateField(unique=True)
    total_indexed = models.IntegerField(default=0)
    total_expired_removed = models.IntegerField(default=0)
    total_new_added = models.IntegerField(default=0)
    validation_errors = models.IntegerField(default=0)
    indexing_api_successes = models.IntegerField(default=0)
    indexing_api_failures = models.IntegerField(default=0)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "jf_crawl_health_snapshots"
        ordering = ["-date"]

    def __str__(self):
        return f"Crawl health {self.date}: {self.total_indexed} indexed"
