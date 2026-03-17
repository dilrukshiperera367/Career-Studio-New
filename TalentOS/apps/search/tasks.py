"""Additional Celery tasks for search index refresh."""

from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(name="apps.search.tasks.refresh_search_index")
def refresh_search_index():
    """Reindex all candidates into OpenSearch."""
    try:
        from apps.search.services import reindex_all_candidates
        count = reindex_all_candidates()
        logger.info(f"refresh_search_index: reindexed {count} candidates")
        return {"reindexed": count}
    except ImportError:
        logger.warning("refresh_search_index: search services not available")
        return {"reindexed": 0, "error": "service not available"}
    except Exception as e:
        logger.error(f"refresh_search_index: {e}")
        return {"error": str(e)}
