"""
Google Indexing API client for notifying Google when job pages are added or removed.

Documentation: https://developers.google.com/search/apis/indexing-api/v3/quickstart

Setup:
1. Create a service account in Google Cloud Console
2. Add the service account email as an owner in Google Search Console
3. Store the JSON key as GOOGLE_INDEXING_API_KEY_JSON env var

Without credentials, all calls are no-ops (logged but not sent).
"""
import json
import logging
import os
from typing import Literal

from django.utils import timezone

from apps.seo_indexing.models import IndexingAPILog

logger = logging.getLogger(__name__)

ACTION = Literal["URL_UPDATED", "URL_DELETED"]


def _get_credentials():
    """Load Google service account credentials from environment."""
    key_json = os.environ.get("GOOGLE_INDEXING_API_KEY_JSON", "")
    if not key_json:
        return None
    try:
        import google.oauth2.service_account as sa
        import google.auth.transport.requests as ga_requests
        info = json.loads(key_json)
        creds = sa.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/indexing"],
        )
        creds.refresh(ga_requests.Request())
        return creds
    except Exception as exc:
        logger.warning("Google Indexing API: credentials load failed — %s", exc)
        return None


def notify_google(url: str, action: ACTION = "URL_UPDATED") -> bool:
    """
    Send a URL_UPDATED or URL_DELETED notification to the Google Indexing API.

    Returns True on success, False on failure or no credentials.
    """
    creds = _get_credentials()
    if not creds:
        logger.info("Google Indexing API: no credentials — skipping notify for %s", url)
        IndexingAPILog.objects.create(
            url=url, action=action, success=False,
            error_message="No GOOGLE_INDEXING_API_KEY_JSON configured",
        )
        return False

    try:
        import requests as req
        endpoint = "https://indexing.googleapis.com/v3/urlNotifications:publish"
        headers = {
            "Authorization": f"Bearer {creds.token}",
            "Content-Type": "application/json",
        }
        payload = {"url": url, "type": action}
        resp = req.post(endpoint, headers=headers, json=payload, timeout=10)
        success = resp.status_code == 200
        IndexingAPILog.objects.create(
            url=url, action=action,
            http_status=resp.status_code,
            response_body=resp.json() if resp.content else {},
            success=success,
            error_message="" if success else resp.text[:500],
        )
        if success:
            logger.info("Google Indexing API: %s %s → 200 OK", action, url)
        else:
            logger.warning("Google Indexing API: %s %s → %d", action, url, resp.status_code)
        return success
    except Exception as exc:
        logger.error("Google Indexing API: exception for %s — %s", url, exc)
        IndexingAPILog.objects.create(
            url=url, action=action, success=False,
            error_message=str(exc)[:500],
        )
        return False


def notify_job_published(job_slug: str, site_url: str = "https://jobfinder.lk") -> bool:
    """Called when a job is published or updated."""
    url = f"{site_url}/en/jobs/{job_slug}"
    return notify_google(url, "URL_UPDATED")


def notify_job_removed(job_slug: str, site_url: str = "https://jobfinder.lk") -> bool:
    """Called when a job expires or is closed."""
    url = f"{site_url}/en/jobs/{job_slug}"
    return notify_google(url, "URL_DELETED")
