"""
Feature 19 — Accessibility, Privacy & Account Safety
Views for consent app (views_extra.py).
"""
from datetime import timedelta
from collections import defaultdict

from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ConsentRecord, DataExportRequest, DataDeletionRequest, PrivacySetting


# ─── Privacy Center ────────────────────────────────────────────────────────────

class PrivacyCenterView(APIView):
    """GET /privacy/center/ — master state: consents + visibility + data requests."""
    permission_classes = [permissions.IsAuthenticated]

    ALL_CONSENT_TYPES = [
        {"key": "profile_processing", "label": "Profile Data Processing", "required": True},
        {"key": "job_matching", "label": "AI Job Matching"},
        {"key": "analytics", "label": "Analytics & Insights"},
        {"key": "marketing", "label": "Marketing Communications"},
        {"key": "third_party", "label": "Third-Party Data Sharing"},
        {"key": "employer_visibility", "label": "Profile Visible to Employers"},
        {"key": "ai_screening", "label": "AI-Assisted Screening"},
        {"key": "cookies", "label": "Cookie & Tracking"},
    ]

    def get(self, request):
        user = request.user
        consents = {
            c["consent_type"]: c
            for c in ConsentRecord.objects.filter(user=user)
            .values("consent_type", "is_granted", "version", "granted_at", "revoked_at", "updated_at")
        }
        ps, _ = PrivacySetting.objects.get_or_create(user=user)
        exports = DataExportRequest.objects.filter(user=user).order_by("-requested_at")[:5]
        deletions = DataDeletionRequest.objects.filter(user=user).order_by("-requested_at")[:5]

        return Response({
            "consent_status": [
                {
                    **ct,
                    "is_granted": consents.get(ct["key"], {}).get("is_granted", False),
                    "version": consents.get(ct["key"], {}).get("version"),
                    "granted_at": consents.get(ct["key"], {}).get("granted_at"),
                }
                for ct in self.ALL_CONSENT_TYPES
            ],
            "visibility": {
                "profile_visibility": ps.profile_visibility,
                "show_email": ps.show_email,
                "show_phone": ps.show_phone,
                "show_salary_expectation": ps.show_salary_expectation,
                "show_in_search": ps.show_in_search,
                "allow_ai_matching": ps.allow_ai_matching,
                "allow_data_enrichment": ps.allow_data_enrichment,
            },
            "contact_controls": {
                "allow_recruiter_messages": ps.allow_recruiter_messages,
                "allow_agency_access": ps.allow_agency_access,
                "email_notification_frequency": ps.email_notification_frequency,
            },
            "data_requests": {
                "exports": [
                    {"id": str(e.id), "status": e.status, "format": e.format, "requested_at": e.requested_at}
                    for e in exports
                ],
                "deletions": [
                    {"id": str(d.id), "status": d.status, "scope": d.scope, "requested_at": d.requested_at}
                    for d in deletions
                ],
            },
        })


# ─── Consent Manage ────────────────────────────────────────────────────────────

class ConsentUpdateView(APIView):
    """POST /privacy/consent/update/ — batch grant/revoke consents."""
    permission_classes = [permissions.IsAuthenticated]
    IMMUTABLE = {"profile_processing"}

    def post(self, request):
        user = request.user
        now = timezone.now()
        results = []
        for item in request.data.get("consents", []):
            ct = item.get("type")
            granted = bool(item.get("granted", False))
            if ct in self.IMMUTABLE and not granted:
                results.append({"type": ct, "status": "skipped", "reason": "Required consent"})
                continue
            ConsentRecord.objects.update_or_create(
                user=user, consent_type=ct, version="1.0",
                defaults={
                    "is_granted": granted,
                    "granted_at": now if granted else None,
                    "revoked_at": None if granted else now,
                    "ip_address": request.META.get("REMOTE_ADDR"),
                },
            )
            results.append({"type": ct, "status": "granted" if granted else "revoked"})
        return Response({"updated": len(results), "results": results})


class ConsentHistoryView(APIView):
    """GET /privacy/consent/history/ — full audit trail."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        records = ConsentRecord.objects.filter(user=request.user).order_by("-updated_at")
        return Response({
            "consent_history": [
                {
                    "consent_type": r.consent_type,
                    "is_granted": r.is_granted,
                    "version": r.version,
                    "granted_at": r.granted_at,
                    "revoked_at": r.revoked_at,
                    "last_changed": r.updated_at,
                }
                for r in records
            ],
        })


# ─── Visibility & Contact ──────────────────────────────────────────────────────

class VisibilityControlsView(APIView):
    """GET/PATCH /privacy/visibility/ — profile and search visibility."""
    permission_classes = [permissions.IsAuthenticated]
    UPDATABLE = ["profile_visibility", "show_email", "show_phone",
                 "show_salary_expectation", "show_in_search",
                 "allow_ai_matching", "allow_data_enrichment"]

    def get(self, request):
        ps, _ = PrivacySetting.objects.get_or_create(user=request.user)
        return Response({f: getattr(ps, f) for f in self.UPDATABLE} | {
            "profile_visibility_choices": ["public", "registered", "employers", "private"]
        })

    def patch(self, request):
        ps, _ = PrivacySetting.objects.get_or_create(user=request.user)
        for f in self.UPDATABLE:
            if f in request.data:
                setattr(ps, f, request.data[f])
        ps.save()
        return Response({f: getattr(ps, f) for f in self.UPDATABLE})


class EmployerContactControlsView(APIView):
    """GET/PATCH /privacy/contact-controls/ — recruiter message and frequency controls."""
    permission_classes = [permissions.IsAuthenticated]
    FIELDS = ["allow_recruiter_messages", "allow_agency_access", "email_notification_frequency"]

    def get(self, request):
        ps, _ = PrivacySetting.objects.get_or_create(user=request.user)
        return Response({f: getattr(ps, f) for f in self.FIELDS} | {
            "frequency_choices": ["realtime", "daily", "weekly", "off"]
        })

    def patch(self, request):
        ps, _ = PrivacySetting.objects.get_or_create(user=request.user)
        for f in self.FIELDS:
            if f in request.data:
                setattr(ps, f, request.data[f])
        ps.save()
        return Response({f: getattr(ps, f) for f in self.FIELDS})


# ─── Data Export / Deletion ────────────────────────────────────────────────────

class DataExportRequestView(APIView):
    """GET/POST /privacy/data-export/ — request and list data exports."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            "exports": list(
                DataExportRequest.objects.filter(user=request.user)
                .order_by("-requested_at")[:10]
                .values("id", "status", "format", "file_url", "expires_at", "requested_at")
            )
        })

    def post(self, request):
        if DataExportRequest.objects.filter(
            user=request.user, status__in=["pending", "processing"]
        ).exists():
            return Response({"detail": "Export already in progress."}, status=400)
        exp = DataExportRequest.objects.create(
            user=request.user,
            format=request.data.get("format", "json"),
            expires_at=timezone.now() + timedelta(days=7),
        )
        return Response({
            "id": str(exp.id), "status": exp.status, "format": exp.format,
            "expires_at": exp.expires_at,
            "message": "Export requested. Ready in ~5 minutes. Link emailed to you. Expires 7 days.",
        }, status=201)


class DataDeletionRequestView(APIView):
    """GET/POST /privacy/data-deletion/ — right-to-erasure requests."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            "deletions": list(
                DataDeletionRequest.objects.filter(user=request.user)
                .order_by("-requested_at")[:10]
                .values("id", "status", "scope", "requested_at", "processed_at")
            )
        })

    def post(self, request):
        if DataDeletionRequest.objects.filter(
            user=request.user, status__in=["pending", "approved", "processing"]
        ).exists():
            return Response({"detail": "A deletion request is already pending."}, status=400)
        req = DataDeletionRequest.objects.create(
            user=request.user,
            scope=request.data.get("scope", "full"),
            reason=request.data.get("reason", ""),
        )
        return Response({
            "id": str(req.id), "status": req.status, "scope": req.scope,
            "message": "Deletion request received. Processed within 30 days. Legal retention may apply.",
        }, status=201)


# ─── Accessibility ─────────────────────────────────────────────────────────────

class AccessibilityPreferencesView(APIView):
    """GET/PATCH /privacy/accessibility/ — reduced motion, screen reader, font size."""
    permission_classes = [permissions.IsAuthenticated]

    def _get_prefs(self, user):
        try:
            from apps.mobile_api.models import DevicePreference
            return DevicePreference.objects.filter(user=user).first()
        except Exception:
            return None

    def get(self, request):
        prefs = self._get_prefs(request.user)
        return Response({
            "reduced_motion": getattr(prefs, "reduced_motion", False),
            "high_contrast": getattr(prefs, "high_contrast", False),
            "font_size": getattr(prefs, "font_size", "default"),
            "screen_reader_optimized": getattr(prefs, "screen_reader_mode", False),
            "wcag_compliance_target": "WCAG 2.2 AA",
            "keyboard_shortcuts": {
                "search": "Ctrl+K",
                "save_job": "Ctrl+S",
                "apply": "Ctrl+Enter",
                "open_menu": "Alt+M",
                "go_back": "Alt+Left",
            },
            "alternatives_to_drag": [
                "All drag-and-drop resume uploads support keyboard file selection.",
                "Job comparison table supports arrow-key navigation.",
                "Saved jobs can be reordered via keyboard in /seeker/saved/.",
            ],
        })

    def patch(self, request):
        try:
            from apps.mobile_api.models import DevicePreference
            prefs, _ = DevicePreference.objects.get_or_create(user=request.user)
            updates = {}
            field_map = {
                "reduced_motion": ("reduced_motion", bool),
                "high_contrast": ("high_contrast", bool),
                "font_size": ("font_size", str),
                "screen_reader_optimized": ("screen_reader_mode", bool),
            }
            for req_key, (model_field, cast) in field_map.items():
                if req_key in request.data and hasattr(prefs, model_field):
                    setattr(prefs, model_field, cast(request.data[req_key]))
                    updates[req_key] = request.data[req_key]
            prefs.save()
            return Response({"updated": updates})
        except Exception as e:
            return Response({"updated": {}, "note": str(e)})


# ─── Help Center ───────────────────────────────────────────────────────────────

class HelpCenterContentView(APIView):
    """GET /privacy/help-center/?lang=en|si|ta&category=privacy|accessibility|safety"""
    permission_classes = [permissions.AllowAny]

    ARTICLES = {
        "privacy": {
            "en": [
                {"id": "p1", "title": "How we use your data", "url": "/help/privacy/data-use/"},
                {"id": "p2", "title": "Download your data", "url": "/help/privacy/data-export/"},
                {"id": "p3", "title": "Delete your account", "url": "/help/privacy/delete-account/"},
                {"id": "p4", "title": "Recruiter visibility controls", "url": "/help/privacy/visibility/"},
                {"id": "p5", "title": "Opt out of AI matching", "url": "/help/privacy/ai-opt-out/"},
            ],
            "si": [
                {"id": "p1", "title": "ඔබේ දත්ත භාවිතා කරන ආකාරය", "url": "/help/privacy/data-use/"},
                {"id": "p2", "title": "ඔබේ දත්ත බාගත කරන්නේ කෙසේද", "url": "/help/privacy/data-export/"},
            ],
            "ta": [
                {"id": "p1", "title": "உங்கள் தரவை எவ்வாறு பயன்படுத்துகிறோம்", "url": "/help/privacy/data-use/"},
            ],
        },
        "accessibility": {
            "en": [
                {"id": "a1", "title": "Keyboard shortcuts", "url": "/help/accessibility/keyboard/"},
                {"id": "a2", "title": "Screen reader guide", "url": "/help/accessibility/screen-reader/"},
                {"id": "a3", "title": "Enable reduced motion", "url": "/help/accessibility/reduced-motion/"},
                {"id": "a4", "title": "Report an accessibility issue", "url": "/feedback/a11y/"},
                {"id": "a5", "title": "WCAG 2.2 compliance statement", "url": "/help/accessibility/wcag/"},
            ],
            "si": [{"id": "a1", "title": "යතුරු කෙටිමඟ", "url": "/help/accessibility/keyboard/"}],
        },
        "safety": {
            "en": [
                {"id": "s1", "title": "Enable two-factor authentication", "url": "/help/safety/mfa/"},
                {"id": "s2", "title": "Recognising job scams", "url": "/help/safety/scam-recognition/"},
                {"id": "s3", "title": "Report a suspicious recruiter", "url": "/help/safety/report-recruiter/"},
                {"id": "s4", "title": "Account recovery", "url": "/help/safety/account-recovery/"},
            ],
            "si": [
                {"id": "s1", "title": "ද්වි-සාධක සත්‍යාපනය", "url": "/help/safety/mfa/"},
                {"id": "s2", "title": "රැකියා වංචා හඳුනා ගැනීම", "url": "/help/safety/scam-recognition/"},
            ],
        },
    }

    def get(self, request):
        lang = request.query_params.get("lang", "en")
        cat_filter = request.query_params.get("category")
        result = {}
        for cat, langs in self.ARTICLES.items():
            if cat_filter and cat != cat_filter:
                continue
            result[cat] = langs.get(lang, langs.get("en", []))
        return Response({
            "lang": lang,
            "available_languages": ["en", "si", "ta"],
            "articles": result,
            "help_entry_points": [
                {"label": "Privacy Center", "url": "/privacy/"},
                {"label": "Accessibility Settings", "url": "/settings/accessibility/"},
                {"label": "Account Security", "url": "/account/security/"},
                {"label": "Report a Scam", "url": "/trust-safety/"},
            ],
        })


class AccountSafetyStatusView(APIView):
    """GET /privacy/account-safety/ — MFA status, safety score, recommendations."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        mfa_enabled = False
        try:
            mfa_enabled = user.totpdevice_set.filter(confirmed=True).exists()
        except Exception:
            pass

        score = 100 if mfa_enabled and user.email else 60 if user.email else 30
        return Response({
            "email": user.email,
            "email_verified": bool(user.email),
            "mfa_enabled": mfa_enabled,
            "last_login": user.last_login,
            "safety_score": score,
            "safety_label": "Secured" if score >= 80 else "Basic" if score >= 50 else "At Risk",
            "recommendations": [
                r for r in [
                    None if mfa_enabled else {
                        "priority": "high",
                        "action": "Enable two-factor authentication",
                        "url": "/account/security/mfa/",
                    },
                    None if user.email else {
                        "priority": "high",
                        "action": "Add a verified email address",
                        "url": "/account/email/",
                    },
                ] if r
            ],
        })
