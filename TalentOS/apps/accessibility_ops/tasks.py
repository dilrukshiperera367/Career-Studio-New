"""Celery tasks for Accessibility Ops app."""

from celery import shared_task


@shared_task(name="apps.accessibility_ops.tasks.flag_overdue_accessibility_reviews")
def flag_overdue_accessibility_reviews():
    """
    Flag AccessibilityReviews whose next_review_date has passed and are not yet in_progress or planned.
    Creates process alerts for overdue reviews to ensure WCAG 2.2 compliance cadence is maintained.
    """
    from django.utils import timezone
    from datetime import date
    from apps.accessibility_ops.models import AccessibilityReview

    today = date.today()

    # Find reviews that were completed but next_review_date has now passed
    overdue_reviews = AccessibilityReview.objects.filter(
        status__in=["complete"],
        next_review_date__lt=today,
        next_review_date__isnull=False,
    ).select_related("tenant")

    flagged = 0
    for review in overdue_reviews:
        # Create a new planned review for the tenant
        AccessibilityReview.objects.create(
            tenant=review.tenant,
            scope=review.scope,
            scope_detail=review.scope_detail,
            review_date=today,
            status="planned",
            conformance_level_target=review.conformance_level_target,
            notes=(
                f"Auto-created: follow-up to review from {review.review_date} "
                f"(next_review_date was {review.next_review_date})."
            ),
        )
        flagged += 1

    return {"overdue_reviews_flagged": flagged}
