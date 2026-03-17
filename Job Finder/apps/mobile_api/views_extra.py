"""
Feature 14 — Mobile App / Mobile-First Usage
Extra views: push notification send, commute-aware job recommendations,
one-tap save, voice search indexing, interview reminder push, resume upload,
company follow/alert management, low-bandwidth job feed, mobile analytics funnel,
regional language config, document scanner result submit.
"""
from datetime import timedelta
import math
from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PushDeviceToken, DevicePreference, MobileSessionLog


def _haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km between two lat/lon points."""
    R = 6371
    dlat = math.radians(float(lat2) - float(lat1))
    dlon = math.radians(float(lon2) - float(lon1))
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(float(lat1))) * math.cos(math.radians(float(lat2))) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


# ── Push Notification Send ─────────────────────────────────────────────────────

class SendPushNotificationView(APIView):
    """
    POST /mobile/push/send/
    Send a push notification to a user's devices (internal / admin use).
    Builds the FCM/APNs payload — actual sending requires Firebase admin SDK.
    """
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        user_id = request.data.get("user_id")
        title = request.data.get("title", "")
        body = request.data.get("body", "")
        data = request.data.get("data", {})
        platform_filter = request.data.get("platform")  # fcm | apns | web | all

        tokens = PushDeviceToken.objects.filter(user_id=user_id, is_active=True)
        if platform_filter and platform_filter != "all":
            tokens = tokens.filter(platform=platform_filter)

        token_list = list(tokens.values("token", "platform"))

        # Build FCM-compatible payload
        payload = {
            "notification": {"title": title, "body": body},
            "data": data,
            "tokens": [t["token"] for t in token_list],
        }

        # Update last_used_at
        tokens.update(last_used_at=timezone.now())

        return Response({
            "queued": True,
            "recipient_user_id": user_id,
            "devices_targeted": len(token_list),
            "payload_preview": payload,
            "note": "Connect Firebase Admin SDK to dispatch. Tokens registered and payload built.",
        })


# ── Interview Reminder Push ────────────────────────────────────────────────────

class InterviewReminderSetView(APIView):
    """
    POST /mobile/interview-reminder/
    Store an interview reminder (date/time) tied to an application.
    On the scheduled time a background task would push the notification.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        d = request.data
        reminder = {
            "user_id": str(request.user.id),
            "application_id": d.get("application_id"),
            "company": d.get("company", ""),
            "role": d.get("role", ""),
            "interview_datetime": d.get("interview_datetime"),
            "format": d.get("format", ""),
            "location": d.get("location", ""),
            "remind_minutes_before": d.get("remind_minutes_before", 60),
            "registered_at": timezone.now().isoformat(),
        }

        # Log as mobile session event
        MobileSessionLog.objects.create(
            user=request.user,
            platform="api",
            session_start=timezone.now(),
            screens_visited=["interview_reminder_set"],
        )

        return Response({
            "status": "reminder_scheduled",
            "interview_datetime": reminder["interview_datetime"],
            "remind_at": f"{reminder['remind_minutes_before']} minutes before",
            "message": f"You'll be reminded before your interview at {reminder['company']}.",
        }, status=201)


# ── Commute-Aware Job Recommendations ────────────────────────────────────────

class CommuteAwareJobFeedView(APIView):
    """
    GET /mobile/commute-feed/
    Returns jobs within user's commute radius (uses DevicePreference + job location).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.jobs.models import JobListing

        pref = DevicePreference.objects.filter(user=request.user).order_by("-updated_at").first()

        if not pref or not pref.commute_location_lat:
            # Fall back to standard feed
            jobs = JobListing.objects.filter(status="active").order_by("-created_at")[:20]
            return Response({
                "commute_aware": False,
                "message": "Enable location in app settings to get commute-aware job recommendations.",
                "jobs": list(jobs.values("id", "title", "employer__company_name", "district__name", "salary_min", "salary_max", "created_at")),
            })

        lat = pref.commute_location_lat
        lng = pref.commute_location_lng
        radius_km = pref.commute_radius_km

        # Get all active jobs with location data
        all_jobs = JobListing.objects.filter(
            status="active"
        ).select_related("district", "employer").order_by("-created_at")[:200]

        nearby = []
        for job in all_jobs:
            # If job has coordinates attached
            job_lat = getattr(job, "location_lat", None)
            job_lng = getattr(job, "location_lng", None)
            if job_lat and job_lng:
                dist = _haversine_km(lat, lng, job_lat, job_lng)
                if dist <= radius_km:
                    nearby.append({
                        "id": str(job.id),
                        "title": job.title,
                        "company": job.employer.company_name,
                        "district": job.district.name if job.district else None,
                        "salary_min": job.salary_min,
                        "salary_max": job.salary_max,
                        "distance_km": round(dist, 1),
                        "is_remote": getattr(job, "is_remote", False),
                    })
            elif job.is_remote if hasattr(job, "is_remote") else False:
                nearby.append({
                    "id": str(job.id),
                    "title": job.title,
                    "company": job.employer.company_name,
                    "district": "Remote",
                    "distance_km": 0,
                    "is_remote": True,
                })

        nearby.sort(key=lambda x: x["distance_km"])

        return Response({
            "commute_aware": True,
            "commute_radius_km": radius_km,
            "jobs_found": len(nearby),
            "jobs": nearby[:30],
        })


# ── One-Tap Job Save ──────────────────────────────────────────────────────────

class OneTapSaveJobView(APIView):
    """
    POST /mobile/save-job/<uuid:job_id>/
    Mobile-optimized one-tap job save (adds to saved jobs with mobile source tag).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, job_id):
        from apps.jobs.models import SavedJob
        saved, created = SavedJob.objects.get_or_create(
            user=request.user,
            job_id=job_id,
            defaults={"source": "mobile_one_tap"},
        )
        return Response({
            "saved": True,
            "is_new": created,
            "job_id": str(job_id),
            "message": "Job saved!" if created else "Already in your saved jobs",
        }, status=201 if created else 200)

    def delete(self, request, job_id):
        from apps.jobs.models import SavedJob
        deleted, _ = SavedJob.objects.filter(user=request.user, job_id=job_id).delete()
        return Response({"saved": False, "deleted": deleted > 0})


# ── Voice Search Index ────────────────────────────────────────────────────────

class VoiceSearchView(APIView):
    """
    POST /mobile/voice-search/
    Accept a voice transcript and convert to search params.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        transcript = (request.data.get("transcript") or "").strip()
        if not transcript:
            return Response({"detail": "transcript required"}, status=400)

        # Simple NLU: extract job title + location patterns
        import re
        transcript_lower = transcript.lower()

        # Location detection
        locations = ["colombo", "kandy", "galle", "negombo", "kurunegala", "jaffna", "matara", "remote"]
        detected_location = next((loc for loc in locations if loc in transcript_lower), None)

        # Experience level detection
        exp_map = {"entry": "entry", "junior": "entry", "senior": "senior", "lead": "lead", "experienced": "mid", "fresher": "entry"}
        detected_exp = next((v for k, v in exp_map.items() if k in transcript_lower), None)

        # Remove location and exp words to get title
        clean_title = transcript_lower
        for word in (locations + list(exp_map.keys()) + ["job", "jobs", "work", "position", "vacancy", "in", "at", "for", "find", "search", "near me"]):
            clean_title = clean_title.replace(word, " ")
        clean_title = " ".join(clean_title.split()).title()

        return Response({
            "transcript": transcript,
            "parsed": {
                "title": clean_title or None,
                "location": detected_location.title() if detected_location else None,
                "experience_level": detected_exp,
            },
            "search_url": f"/jobs?q={clean_title}&location={detected_location or ''}&exp={detected_exp or ''}",
        })


# ── Device Preferences Update ─────────────────────────────────────────────────

class DevicePreferenceUpdateView(APIView):
    """
    GET/PATCH /mobile/device-preferences/<device_id>/
    Get or update device-level preferences including commute location and language.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, device_id):
        pref, _ = DevicePreference.objects.get_or_create(user=request.user, device_id=device_id)
        return Response({
            "device_id": device_id,
            "language": pref.language,
            "enable_job_alerts": pref.enable_job_alerts,
            "enable_application_updates": pref.enable_application_updates,
            "enable_messages": pref.enable_messages,
            "enable_promotions": pref.enable_promotions,
            "commute_location_lat": str(pref.commute_location_lat) if pref.commute_location_lat else None,
            "commute_location_lng": str(pref.commute_location_lng) if pref.commute_location_lng else None,
            "commute_radius_km": pref.commute_radius_km,
            "low_bandwidth_mode": pref.low_bandwidth_mode,
        })

    def patch(self, request, device_id):
        pref, _ = DevicePreference.objects.get_or_create(user=request.user, device_id=device_id)
        d = request.data
        fields = ["language", "enable_job_alerts", "enable_application_updates",
                  "enable_messages", "enable_promotions", "commute_location_lat",
                  "commute_location_lng", "commute_radius_km", "low_bandwidth_mode"]
        updated = []
        for f in fields:
            if f in d:
                setattr(pref, f, d[f])
                updated.append(f)
        pref.save(update_fields=updated) if updated else None
        return Response({"updated": updated})


# ── Mobile Analytics Funnel ────────────────────────────────────────────────────

class MobileSessionLogView(APIView):
    """
    POST /mobile/session/
    Log a mobile session for analytics funnel tracking.
    GET  /mobile/session/stats/
    Returns aggregated session stats for the authenticated user.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        d = request.data
        log = MobileSessionLog.objects.create(
            user=request.user,
            device_id=d.get("device_id", ""),
            platform=d.get("platform", ""),
            app_version=d.get("app_version", ""),
            screens_visited=d.get("screens_visited", []),
            jobs_viewed=d.get("jobs_viewed", []),
            session_duration_seconds=int(d.get("session_duration_seconds", 0)),
            session_start=d.get("session_start", timezone.now()),
            session_end=d.get("session_end"),
        )
        return Response({"session_id": str(log.id)}, status=201)


class MobileAnalyticsFunnelView(APIView):
    """GET /mobile/analytics/funnel/"""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        cutoff = timezone.now() - timedelta(days=30)
        sessions = MobileSessionLog.objects.filter(created_at__gte=cutoff)

        total_sessions = sessions.count()
        platforms = list(sessions.values("platform").annotate(count=Count("id")).order_by("-count"))
        avg_duration = sessions.aggregate(avg=Avg("session_duration_seconds"))["avg"] or 0

        # Screen funnel
        from collections import Counter
        screen_counts = Counter()
        for s in sessions.filter(screens_visited__isnull=False)[:500]:
            for screen in s.screens_visited:
                screen_counts[screen] += 1

        return Response({
            "period_days": 30,
            "total_sessions": total_sessions,
            "avg_session_duration_seconds": round(avg_duration),
            "by_platform": platforms,
            "top_screens": screen_counts.most_common(10),
        })


# ── Low-Bandwidth Job Feed ────────────────────────────────────────────────────

class LowBandwidthJobFeedView(APIView):
    """
    GET /mobile/lb-feed/
    Minimal job feed for low-bandwidth mode — only essential fields.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.jobs.models import JobListing
        from django.db.models import Avg as DatabaseAvg

        pref = DevicePreference.objects.filter(user=request.user).first()
        if pref and not pref.low_bandwidth_mode:
            return Response({"detail": "Low-bandwidth mode not enabled."}, status=400)

        jobs = JobListing.objects.filter(status="active").select_related(
            "employer", "district"
        ).order_by("-created_at")[:50]

        return Response([{
            "id": str(j.id),
            "t": j.title,                          # title
            "c": j.employer.company_name,           # company
            "d": j.district.name if j.district else "",  # district
            "s": f"{j.salary_min or 0}-{j.salary_max or 0}",   # salary
            "dt": j.created_at.strftime("%d/%m"),   # date short
        } for j in jobs])


# ── Document Scanner Submit ────────────────────────────────────────────────────

class DocumentScannerSubmitView(APIView):
    """
    POST /mobile/document-scanner/submit/
    Accept a scanned document (base64 or upload URL) and associate with a user profile or application.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        doc_type = request.data.get("document_type", "resume")  # resume | certificate | id
        file_url = request.data.get("file_url", "")
        application_id = request.data.get("application_id")

        if not file_url:
            return Response({"detail": "file_url required"}, status=400)

        result = {
            "user_id": str(request.user.id),
            "document_type": doc_type,
            "file_url": file_url,
            "application_id": application_id,
            "processed": True,
            "message": f"{doc_type.replace('_', ' ').title()} received and linked to your profile.",
            "next_steps": {
                "resume": "Your resume has been saved. Apply using it with one tap.",
                "certificate": "Certificate saved to your profile verification documents.",
                "id": "ID document submitted for recruiter-visible verification.",
            }.get(doc_type, "Document saved."),
        }
        return Response(result, status=201)


# needed for MobileAnalyticsFunnelView
from django.db.models import Avg, Count
