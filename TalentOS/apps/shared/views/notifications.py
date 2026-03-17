"""Notification API views — in-app notifications and unified ATS+HRM feed."""

from rest_framework import serializers, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from django.urls import path

from apps.accounts.permissions import HasTenantAccess


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        from apps.accounts.models import Notification
        model = Notification
        fields = ["id", "type", "title", "body",
                  "entity_type", "entity_id", "is_read", "created_at"]
        read_only_fields = ["id", "created_at"]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        from apps.accounts.models import UserNotificationPreference
        model = UserNotificationPreference
        fields = ["id", "event_type", "email_enabled", "in_app_enabled"]
        read_only_fields = ["id"]


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

class NotificationListView(APIView):
    """Notification center: list, mark read, unread count."""
    permission_classes = [IsAuthenticated, HasTenantAccess]

    def get(self, request):
        from apps.accounts.models import Notification

        qs = Notification.objects.filter(
            user=request.user, tenant_id=request.tenant_id
        ).order_by("-created_at")

        unread_only = request.query_params.get("unread")
        if unread_only == "true":
            qs = qs.filter(is_read=False)

        notifications = qs[:50]
        unread_count = Notification.objects.filter(
            user=request.user, tenant_id=request.tenant_id, is_read=False
        ).count()

        return Response({
            "unread_count": unread_count,
            "notifications": NotificationSerializer(notifications, many=True).data,
        })

    def post(self, request):
        """Mark notifications as read."""
        from apps.accounts.models import Notification

        notification_ids = request.data.get("notification_ids", [])
        mark_all = request.data.get("mark_all", False)

        if mark_all:
            count = Notification.objects.filter(
                user=request.user, tenant_id=request.tenant_id, is_read=False
            ).update(is_read=True)
        elif notification_ids:
            count = Notification.objects.filter(
                id__in=notification_ids, user=request.user, tenant_id=request.tenant_id
            ).update(is_read=True)
        else:
            count = 0

        return Response({"marked_read": count})


class NotificationPreferencesView(APIView):
    """Manage notification preferences per user."""
    permission_classes = [IsAuthenticated, HasTenantAccess]

    def get(self, request):
        from apps.accounts.models import UserNotificationPreference

        prefs = UserNotificationPreference.objects.filter(
            user=request.user,
        )
        return Response(NotificationPreferenceSerializer(prefs, many=True).data)

    def post(self, request):
        """Bulk update notification preferences."""
        from apps.accounts.models import UserNotificationPreference

        preferences = request.data.get("preferences", [])
        updated = 0
        for pref in preferences:
            obj, created = UserNotificationPreference.objects.update_or_create(
                user=request.user,
                event_type=pref.get("event_type", ""),
                defaults={
                    "email_enabled": pref.get("email_enabled", True),
                    "in_app_enabled": pref.get("in_app_enabled", True),
                },
            )
            updated += 1

        return Response({"updated": updated})


class UnifiedNotificationView(APIView):
    """
    GET /api/v1/notifications/unified/

    Returns merged notifications from both ATS (local) and HRM (remote).
    Each notification carries a 'source' field: 'ats' | 'hrm'.

    The HRM fetch is best-effort: if it fails (network issue, HRM down),
    only ATS notifications are returned.

    Query params:
      - unread_only: boolean (default false)
      - limit: integer (default 50, max 200)
    """
    permission_classes = [IsAuthenticated, HasTenantAccess]

    def get(self, request):
        import urllib.request, urllib.error, json as _json

        unread_only = request.query_params.get('unread_only', '').lower() in ('1', 'true', 'yes')
        limit = min(int(request.query_params.get('limit', 50)), 200)

        # ── ATS notifications ─────────────────────────────────────────────
        from apps.accounts.models import Notification

        ats_qs = Notification.objects.filter(
            user=request.user,
            tenant_id=request.tenant_id,
        ).order_by('-created_at')
        if unread_only:
            ats_qs = ats_qs.filter(is_read=False)

        ats_notifications = [
            {
                'id': str(n.id),
                'source': 'ats',
                'type': n.type,
                'title': n.title,
                'body': n.body,
                'is_read': n.is_read,
                'created_at': n.created_at.isoformat(),
                'metadata': {},
                'link': '',
            }
            for n in ats_qs[:limit]
        ]

        # ── HRM notifications (best-effort remote fetch) ──────────────────
        hrm_notifications = []
        hrm_url = getattr(settings, 'HRM_BASE_URL', '')
        if hrm_url:
            try:
                # Forward the Authorization header so HRM validates the same JWT
                auth_header = request.META.get('HTTP_AUTHORIZATION', '')
                params = f'?limit={limit}'
                if unread_only:
                    params += '&unread_only=true'

                req = urllib.request.Request(
                    hrm_url.rstrip('/') + '/api/v1/platform/notifications/' + params,
                    headers={
                        'Authorization': auth_header,
                        'X-Tenant-ID': str(request.tenant_id),
                        'Accept': 'application/json',
                    },
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    hrm_data = _json.loads(resp.read())
                    for n in hrm_data.get('results', hrm_data if isinstance(hrm_data, list) else []):
                        hrm_notifications.append({
                            'id': str(n.get('id', '')),
                            'source': 'hrm',
                            'type': n.get('notification_type', n.get('type', 'info')),
                            'title': n.get('title', ''),
                            'body': n.get('body', n.get('message', '')),
                            'is_read': n.get('is_read', False),
                            'created_at': n.get('created_at', ''),
                            'metadata': n.get('metadata', {}),
                            'link': n.get('link', ''),
                        })
            except (urllib.error.URLError, Exception):
                # HRM unreachable — return ATS-only silently
                pass

        # ── Merge and sort by created_at desc ─────────────────────────────
        merged = ats_notifications + hrm_notifications
        try:
            merged.sort(key=lambda x: x.get('created_at') or '', reverse=True)
        except Exception:
            pass

        merged = merged[:limit]

        ats_unread = sum(1 for n in ats_notifications if not n['is_read'])
        hrm_unread = sum(1 for n in hrm_notifications if not n['is_read'])

        return Response({
            'notifications': merged,
            'total_unread': ats_unread + hrm_unread,
            'ats_unread': ats_unread,
            'hrm_unread': hrm_unread,
            'hrm_available': bool(hrm_url),
        })


# ---------------------------------------------------------------------------
# URL patterns
# ---------------------------------------------------------------------------

notification_urlpatterns = [
    path("", NotificationListView.as_view(), name="notifications"),
    path("preferences/", NotificationPreferencesView.as_view(), name="notification-preferences"),
    path("unified/", UnifiedNotificationView.as_view(), name="notifications-unified"),
]
