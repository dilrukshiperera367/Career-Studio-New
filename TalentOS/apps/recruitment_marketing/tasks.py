"""Celery tasks for Recruitment Marketing app."""

from celery import shared_task


@shared_task(name="apps.recruitment_marketing.tasks.publish_scheduled_social_posts")
def publish_scheduled_social_posts():
    """
    Hourly task: mark scheduled SocialPosts as published when scheduled_at <= now.
    In a real integration this would call the social media platform API.
    """
    from django.utils import timezone
    from apps.recruitment_marketing.models import SocialPost

    now = timezone.now()
    due_posts = SocialPost.objects.filter(
        status="scheduled",
        scheduled_at__lte=now,
    )
    count = due_posts.count()
    due_posts.update(status="published", published_at=now)
    return {"posts_published": count}


@shared_task(name="apps.recruitment_marketing.tasks.aggregate_utm_stats")
def aggregate_utm_stats():
    """
    Daily rollup: count UTM hits per campaign and update CampaignLanding conversion counts.
    """
    from django.db.models import Count
    from apps.recruitment_marketing.models import UTMTracking, CampaignLanding

    # Aggregate hits per landing page
    landing_hits = (
        UTMTracking.objects.filter(landing__isnull=False)
        .values("landing_id")
        .annotate(hit_count=Count("id"))
    )

    updated = 0
    for row in landing_hits:
        landing_id = row["landing_id"]
        hit_count = row["hit_count"]
        try:
            landing = CampaignLanding.objects.get(pk=landing_id)
            landing.view_count = hit_count
            landing.save(update_fields=["view_count"])
            updated += 1
        except CampaignLanding.DoesNotExist:
            pass

    return {"landings_updated": updated}
