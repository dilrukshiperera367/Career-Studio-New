"""Django signals: notify Google Indexing API on job publish/close."""
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.jobs.models import JobListing


@receiver(post_save, sender=JobListing)
def job_post_save_handler(sender, instance, created, **kwargs):
    """
    After a job is saved:
    - If status changed to 'active': notify URL_UPDATED
    - If status changed to 'expired'/'closed'/'filled': notify URL_DELETED + mark sitemap entry
    """
    try:
        _handle_job_indexing(instance)
    except Exception:
        pass  # Never let signal errors affect the save path


def _handle_job_indexing(job):
    from apps.seo_indexing.models import SitemapEntry
    from apps.seo_indexing.indexing_api_client import notify_job_published, notify_job_removed

    if job.status == "active" and job.published_at:
        # Upsert sitemap entry
        SitemapEntry.objects.update_or_create(
            page_type="job", slug=job.slug,
            defaults={
                "url": f"https://jobfinder.lk/en/jobs/{job.slug}",
                "priority": 0.9 if job.is_featured else 0.8,
                "change_frequency": "daily",
                "is_indexable": True,
                "is_expired": False,
            },
        )
        notify_job_published(job.slug)

    elif job.status in ("expired", "closed", "filled", "rejected"):
        # Mark as expired in sitemap
        SitemapEntry.objects.filter(page_type="job", slug=job.slug).update(
            is_expired=True, is_indexable=False
        )
        notify_job_removed(job.slug)
