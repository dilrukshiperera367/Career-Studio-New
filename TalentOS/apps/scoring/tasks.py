"""
Celery tasks for async batch processing.

Pipeline per batch:
  1. process_batch(batch_id) — entry point, queues item tasks
  2. parse_batch_item(item_id) — extract + parse CV
  3. score_batch_item(item_id) — compute score against JD
"""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def process_batch(self, batch_id: str):
    """Queue parsing tasks for all items in a batch."""
    from apps.scoring.models import JobScoreBatch
    from apps.scoring.jd_parser import parse_jd, build_taxonomy_lookup

    try:
        batch = JobScoreBatch.objects.get(id=batch_id)
        batch.status = "processing"

        # Parse JD if not already parsed
        if not batch.jd_requirements_json:
            taxonomy = build_taxonomy_lookup()
            batch.jd_requirements_json = parse_jd(batch.jd_text, taxonomy)

        batch.save()

        # Queue parsing for each item
        items = batch.items.filter(status="uploaded")
        for item in items:
            parse_batch_item.delay(str(item.id))

        logger.info(f"Queued {items.count()} items for batch {batch_id}")
    except Exception as exc:
        logger.error(f"process_batch failed: {exc}")
        raise self.retry(exc=exc, countdown=10)


@shared_task(bind=True, max_retries=2)
def parse_batch_item(self, item_id: str):
    """Parse a single CV file."""
    from apps.scoring.models import BatchItem, JobScoreBatch
    from apps.parsing.services import parse_resume_full
    from apps.scoring.jd_parser import build_taxonomy_lookup

    try:
        item = BatchItem.objects.select_related("batch").get(id=item_id)
        item.status = "parsing"
        item.save(update_fields=["status"])

        # Build taxonomy for parsing
        taxonomy = build_taxonomy_lookup()

        # Parse the CV
        if item.file and item.file.name:
            item.file.seek(0)
            file_content = item.file.read()
        else:
            file_content = b""
        result = parse_resume_full(file_content, item.file_type, taxonomy)

        item.raw_text = result.get("raw_text", "")
        item.parsed_json = result
        item.status = "parsed"

        # Extract candidate name/email
        contact = result.get("contact", {})
        item.candidate_email = contact.get("email", [""])[0] if contact.get("email") else ""
        # Try name from header
        derived = result.get("derived", {})
        item.candidate_name = derived.get("recent_title", "")[:300]

        item.save()

        # Update batch progress
        batch = item.batch
        batch.parsed_items = batch.items.filter(status__in=["parsed", "scoring", "done"]).count()
        batch.save(update_fields=["parsed_items"])

        # Queue scoring
        score_batch_item.delay(item_id)

    except Exception as exc:
        logger.error(f"parse_batch_item failed for {item_id}: {exc}")
        try:
            item = BatchItem.objects.get(id=item_id)
            item.status = "failed"
            item.error_message = str(exc)[:500]
            item.save(update_fields=["status", "error_message"])
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=10)


@shared_task(bind=True, max_retries=2)
def score_batch_item(self, item_id: str):
    """Compute ATS score for a parsed CV."""
    from apps.scoring.models import BatchItem, BatchItemScore
    from apps.scoring.scorer import compute_score

    try:
        item = BatchItem.objects.select_related("batch").get(id=item_id)
        item.status = "scoring"
        item.save(update_fields=["status"])

        batch = item.batch
        jd_requirements = batch.jd_requirements_json
        weights = batch.scoring_weights or None

        # Extract inner parsed_json for scorer
        cv_signals = item.parsed_json
        if isinstance(cv_signals, dict) and "parsed_json" in cv_signals:
            cv_signals = cv_signals["parsed_json"]

        result = compute_score(
            cv_parsed=cv_signals,
            jd_requirements=jd_requirements,
            file_type=item.file_type,
            raw_text=item.raw_text,
            weights=weights,
            jd_target_title=batch.job_title or "",
        )

        # Save score
        BatchItemScore.objects.update_or_create(
            batch_item=item,
            defaults={
                "score_total": result["score_total"],
                "content_score": result["content_score"],
                "title_score": result["title_score"],
                "experience_score": result["experience_score"],
                "recency_score": result["recency_score"],
                "format_score": result["format_score"],
                "breakdown_json": result["breakdown"],
            },
        )

        item.status = "done"
        item.save(update_fields=["status"])

        # Update batch progress
        batch.scored_items = batch.items.filter(status="done").count()
        if batch.scored_items >= batch.total_items:
            batch.status = "completed"
        batch.save(update_fields=["scored_items", "status"])

        logger.info(f"Scored item {item_id}: {result['score_total']}/100")

    except Exception as exc:
        logger.error(f"score_batch_item failed for {item_id}: {exc}")
        try:
            item = BatchItem.objects.get(id=item_id)
            item.status = "failed"
            item.error_message = str(exc)[:500]
            item.save(update_fields=["status", "error_message"])
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=10)


def process_batch_sync(batch_id: str):
    """
    Synchronous batch processing — for environments without Celery.
    Parses and scores all items sequentially.
    """
    from apps.scoring.models import JobScoreBatch, BatchItem
    from apps.parsing.services import parse_resume_full
    from apps.scoring.jd_parser import parse_jd, build_taxonomy_lookup
    from apps.scoring.scorer import compute_score
    from apps.scoring.models import BatchItemScore

    batch = JobScoreBatch.objects.get(id=batch_id)
    taxonomy = build_taxonomy_lookup()

    # Parse JD
    if not batch.jd_requirements_json:
        batch.jd_requirements_json = parse_jd(batch.jd_text, taxonomy)
    batch.status = "processing"
    batch.save()

    items = batch.items.filter(status="uploaded")
    for item in items:
        try:
            # Parse
            item.status = "parsing"
            item.save(update_fields=["status"])

            if item.file and item.file.name:
                item.file.seek(0)
                file_content = item.file.read()
            else:
                file_content = b""
            result = parse_resume_full(file_content, item.file_type, taxonomy)

            item.raw_text = result.get("raw_text", "")
            item.parsed_json = result
            item.status = "parsed"

            contact = result.get("contact", {})
            item.candidate_email = contact.get("email", [""])[0] if contact.get("email") else ""
            item.save()

            batch.parsed_items += 1
            batch.save(update_fields=["parsed_items"])

            # Score
            item.status = "scoring"
            item.save(update_fields=["status"])

            # Extract inner parsed_json for scorer
            cv_signals = item.parsed_json
            if isinstance(cv_signals, dict) and "parsed_json" in cv_signals:
                cv_signals = cv_signals["parsed_json"]

            score_result = compute_score(
                cv_parsed=cv_signals,
                jd_requirements=batch.jd_requirements_json,
                file_type=item.file_type,
                raw_text=item.raw_text,
                weights=batch.scoring_weights or None,
                jd_target_title=batch.job_title or "",
            )

            BatchItemScore.objects.update_or_create(
                batch_item=item,
                defaults={
                    "score_total": score_result["score_total"],
                    "content_score": score_result["content_score"],
                    "title_score": score_result["title_score"],
                    "experience_score": score_result["experience_score"],
                    "recency_score": score_result["recency_score"],
                    "format_score": score_result["format_score"],
                    "breakdown_json": score_result["breakdown"],
                },
            )

            item.status = "done"
            item.save(update_fields=["status"])
            batch.scored_items += 1
            batch.save(update_fields=["scored_items"])

        except Exception as exc:
            logger.error(f"Sync processing failed for item {item.id}: {exc}")
            item.status = "failed"
            item.error_message = str(exc)[:500]
            item.save(update_fields=["status", "error_message"])

    batch.status = "completed"
    batch.save(update_fields=["status"])
