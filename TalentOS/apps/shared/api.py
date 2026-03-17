"""
apps/shared/api.py
==================
Thin delegation shim — all views and URL patterns now live in the
``apps/shared/views/`` package.

This module re-exports every public name so that existing consumers
(apps/messaging/urls.py, apps/analytics/urls.py, apps/portal/urls.py,
apps/notifications/urls.py, apps/notifications/compliance_urls.py) continue
to work without any changes.
"""

from apps.shared.views import *  # noqa: F401,F403
from apps.shared.views import (  # noqa: F401  (explicit for static analysers)
    # URL pattern lists consumed by other apps' urls.py
    messaging_urlpatterns,
    analytics_urlpatterns,
    portal_urlpatterns,
    notification_urlpatterns,
    compliance_urlpatterns,
)
