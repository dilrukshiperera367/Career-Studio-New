"""
Feature 13 — Candidate Messaging & Comms 2.0
Extra views: recruiter templates, message request inbox, interview scheduling,
anti-phishing link scanning, message categorization, follow-up suggestions,
SLA reminders, analytics, archive/spam handling, multilingual templates.
"""
import re
from datetime import timedelta
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import MessageThread, Message, VerifiedSenderBadge

# ── Phishing link patterns ────────────────────────────────────────────────────
PHISHING_PATTERNS = [
    r"bit\.ly/", r"tinyurl\.com/", r"wa\.me/", r"t\.me/",
    r"free.*money", r"whatsapp.*job", r"click.*earn",
    r"registration.*fee", r"western.*union", r"crypto.*pay",
    r"gift.*card", r"urgent.*hiring", r"earn.*daily",
]

TEMPLATE_LIBRARY = {
    "recruiter_intro": {
        "subject": "Opportunity at {company}",
        "body": "Hi {candidate_name},\n\nI came across your profile on Job Finder and I'm impressed by your background in {field}. We have an exciting opportunity at {company} that I think could be a great fit for you.\n\nWould you be open to a quick 15-minute call this week?\n\nBest regards,\n{recruiter_name}",
    },
    "interview_invite": {
        "subject": "Interview Invitation — {role} at {company}",
        "body": "Hi {candidate_name},\n\nThank you for applying for the {role} position at {company}. We'd like to invite you for an interview.\n\n📅 Date: {date}\n⏰ Time: {time}\n📍 Format: {format}\n\nPlease confirm your availability by replying to this message.\n\nLooking forward to speaking with you!\n{recruiter_name}",
    },
    "application_update": {
        "subject": "Update on your application — {role}",
        "body": "Hi {candidate_name},\n\nThank you for your interest in the {role} position at {company}. We wanted to update you on the status of your application.\n\n{status_message}\n\nThank you for your patience.\n\nBest regards,\n{recruiter_name}",
    },
    "follow_up": {
        "subject": "Following up on your application",
        "body": "Hi {candidate_name},\n\nI wanted to follow up on your application for {role}. We are still reviewing candidates and will get back to you shortly.\n\nBest regards,\n{recruiter_name}",
    },
    "rejection_respectful": {
        "subject": "Your application for {role} at {company}",
        "body": "Hi {candidate_name},\n\nThank you for taking the time to interview for the {role} position at {company}. After careful consideration, we have decided to move forward with another candidate.\n\nWe were impressed by your background and encourage you to apply for future openings.\n\nBest regards,\n{recruiter_name}",
    },
    "offer_letter_intro": {
        "subject": "Exciting News — Job Offer from {company}",
        "body": "Hi {candidate_name},\n\nWe are excited to offer you the position of {role} at {company}!\n\nOur HR team will send you the formal offer letter with full details. Please confirm receipt of this message.\n\nCongratulations!\n{recruiter_name}",
    },
}

SINHALA_TEMPLATES = {
    "recruiter_intro": {
        "subject": "{company} හිදී අවස්ථාවක්",
        "body": "ආයුබෝවන් {candidate_name},\n\nJob Finder හි ඔබේ profile දැකීමෙන් ප්‍රීතිමත් වෙමි. {company} සමාගමේ {role} තනතුරට ඔබ සුදුසු යැයි සිතමි.\n\nකෙටි සාකච්ඡාවකට ඉඩ ලැබෙනවාද?\n\n{recruiter_name}",
    },
}

MSG_CATEGORIES = {
    "interview": ["interview", "schedule", "meeting", "call", "zoom", "teams", "in-person", "panel"],
    "offer": ["offer", "salary", "package", "compensation", "joining", "start date", "contract"],
    "rejection": ["unfortunately", "not moving forward", "other candidates", "not selected"],
    "follow_up": ["follow up", "following up", "checking in", "update", "status"],
    "info_request": ["please share", "can you send", "attach", "resume", "portfolio", "certificate"],
}


def _categorize_message(body: str) -> str:
    body_lower = body.lower()
    for cat, keywords in MSG_CATEGORIES.items():
        if any(kw in body_lower for kw in keywords):
            return cat
    return "general"


def _scan_phishing(body: str) -> list:
    signals = []
    for pattern in PHISHING_PATTERNS:
        if re.search(pattern, body, re.IGNORECASE):
            signals.append(pattern)
    return signals


# ── Message Request Inbox ─────────────────────────────────────────────────────

class MessageRequestInboxView(APIView):
    """
    GET /messaging/requests/
    Returns all unaccepted message request threads for the current user.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        threads = MessageThread.objects.filter(
            Q(participant_two=request.user),
            is_message_request=True,
            request_accepted_at__isnull=True,
        ).select_related("participant_one", "job")

        return Response([{
            "id": str(t.id),
            "from_user": {
                "id": str(t.participant_one.id),
                "name": t.participant_one.get_full_name() or t.participant_one.username,
                "is_verified": hasattr(t.participant_one, "verified_sender_badge") and t.participant_one.verified_sender_badge.is_active,
            },
            "job_title": t.job.title if t.job else None,
            "subject": t.subject,
            "created_at": t.created_at,
            "preview": t.messages.first().body[:120] if t.messages.exists() else "",
        } for t in threads])

    def post(self, request):
        """Accept or decline a message request."""
        thread_id = request.data.get("thread_id")
        action = request.data.get("action")  # accept | decline

        try:
            thread = MessageThread.objects.get(pk=thread_id, participant_two=request.user)
        except MessageThread.DoesNotExist:
            return Response(status=404)

        if action == "accept":
            thread.request_accepted_at = timezone.now()
            thread.is_message_request = False
            thread.save(update_fields=["request_accepted_at", "is_message_request"])
            return Response({"status": "accepted"})
        elif action == "decline":
            thread.is_archived_two = True
            thread.save(update_fields=["is_archived_two"])
            return Response({"status": "declined"})
        else:
            return Response({"detail": "action must be accept or decline"}, status=400)


# ── Recruiter Message Templates ────────────────────────────────────────────────

class MessageTemplateListView(APIView):
    """
    GET /messaging/templates/?lang=en
    Returns templated message library (recruiter intro, interview invite, etc.)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        lang = request.query_params.get("lang", "en")
        templates = SINHALA_TEMPLATES if lang == "si" else TEMPLATE_LIBRARY
        return Response({
            key: {
                "id": key,
                "name": key.replace("_", " ").title(),
                "subject": tpl["subject"],
                "body": tpl["body"],
                "variables": re.findall(r"\{(\w+)\}", tpl["body"] + tpl["subject"]),
            }
            for key, tpl in templates.items()
        })


class MessageTemplateRenderView(APIView):
    """
    POST /messaging/templates/render/
    Render a template with provided variables.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        template_id = request.data.get("template_id", "")
        variables = request.data.get("variables", {})
        lang = request.data.get("lang", "en")

        templates = SINHALA_TEMPLATES if lang == "si" else TEMPLATE_LIBRARY
        tpl = templates.get(template_id)
        if not tpl:
            return Response({"detail": "Template not found."}, status=404)

        try:
            subject = tpl["subject"].format(**variables)
            body = tpl["body"].format(**variables)
        except KeyError as e:
            return Response({"detail": f"Missing variable: {e}"}, status=400)

        return Response({"subject": subject, "body": body, "template_id": template_id})


# ── Anti-Phishing Link Scanner ────────────────────────────────────────────────

class MessagePhishingScanView(APIView):
    """
    POST /messaging/scan-phishing/
    Scan message body for suspicious links and scam language before sending.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        body = request.data.get("body", "")
        signals = _scan_phishing(body)

        if signals:
            return Response({
                "safe": False,
                "signals_found": len(signals),
                "warning": "This message contains suspicious patterns that may indicate phishing or scam activity.",
                "patterns_matched": signals,
                "recommendation": "Review this message carefully before sending or report it to trust & safety.",
            })
        return Response({"safe": True, "signals_found": 0})


# ── Interview Scheduling Inside Thread ────────────────────────────────────────

class InterviewScheduleInThreadView(APIView):
    """
    POST /messaging/threads/<uuid:thread_id>/schedule-interview/
    Send a structured interview invitation system message in a thread.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, thread_id):
        try:
            thread = MessageThread.objects.get(pk=thread_id)
        except MessageThread.DoesNotExist:
            return Response(status=404)

        d = request.data
        interview_date = d.get("date", "")
        interview_time = d.get("time", "")
        format_ = d.get("format", "Video Call")
        location = d.get("location", "")
        notes = d.get("notes", "")

        body = (
            f"📅 **Interview Invitation**\n\n"
            f"Date: {interview_date}\n"
            f"Time: {interview_time}\n"
            f"Format: {format_}\n"
            + (f"Location: {location}\n" if location else "")
            + (f"\nNotes: {notes}" if notes else "")
            + "\n\nPlease reply to confirm your availability."
        )

        msg = Message.objects.create(
            thread=thread,
            sender=request.user,
            body=body,
            is_system_message=False,
        )
        thread.last_message_at = timezone.now()
        thread.save(update_fields=["last_message_at"])

        return Response({
            "message_id": str(msg.id),
            "interview_date": interview_date,
            "interview_time": interview_time,
            "format": format_,
            "status": "sent",
        }, status=201)


# ── Message Categorization ────────────────────────────────────────────────────

class MessageCategorizationView(APIView):
    """
    GET /messaging/threads/<uuid:thread_id>/categorize/
    Auto-categorize messages in a thread (interview/offer/rejection/follow_up/info_request/general).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, thread_id):
        try:
            thread = MessageThread.objects.get(pk=thread_id)
        except MessageThread.DoesNotExist:
            return Response(status=404)

        messages = thread.messages.order_by("-created_at")[:20]
        categorized = [
            {
                "id": str(m.id),
                "category": _categorize_message(m.body),
                "sender_id": str(m.sender_id),
                "snippet": m.body[:100],
                "created_at": m.created_at,
            }
            for m in messages
        ]

        # Thread-level category = most common message category
        from collections import Counter
        cats = [c["category"] for c in categorized]
        thread_category = Counter(cats).most_common(1)[0][0] if cats else "general"

        return Response({
            "thread_id": str(thread.id),
            "thread_category": thread_category,
            "messages": categorized,
        })


# ── Follow-Up Suggestions & SLA Reminders ─────────────────────────────────────

class FollowUpSuggestionsView(APIView):
    """
    GET /messaging/follow-up-suggestions/
    Returns threads that are overdue for follow-up (employer SLA reminders).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cutoff_48h = timezone.now() - timedelta(hours=48)
        cutoff_7d = timezone.now() - timedelta(days=7)

        # Threads where user is participant_one (employer/recruiter) and hasn't replied
        overdue = MessageThread.objects.filter(
            participant_one=request.user,
            last_message_at__lt=cutoff_48h,
            is_archived_one=False,
            request_accepted_at__isnull=False,
        ).select_related("participant_two", "job")

        results = []
        for t in overdue[:20]:
            last_msg = t.messages.order_by("-created_at").first()
            is_last_from_candidate = last_msg and last_msg.sender_id != request.user.id
            days_silent = (timezone.now() - t.last_message_at).days if t.last_message_at else 0

            if is_last_from_candidate:
                results.append({
                    "thread_id": str(t.id),
                    "candidate_name": t.participant_two.get_full_name() or t.participant_two.username,
                    "job_title": t.job.title if t.job else "General",
                    "days_since_last_message": days_silent,
                    "urgency": "critical" if days_silent >= 7 else "high" if days_silent >= 3 else "medium",
                    "suggested_action": "Send follow-up message" if days_silent < 7 else "Candidate response overdue — send update or close thread",
                    "suggested_template": "follow_up",
                })

        return Response({
            "overdue_count": len(results),
            "threads": results,
            "sla_policy": "Respond to candidate messages within 48 hours for best hiring outcomes.",
        })


# ── Message Quality & Response Analytics ──────────────────────────────────────

class MessageAnalyticsView(APIView):
    """
    GET /messaging/analytics/
    Per-user message response analytics for employer/recruiter dashboard.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        total_threads = MessageThread.objects.filter(
            Q(participant_one=user) | Q(participant_two=user)
        ).count()

        total_sent = Message.objects.filter(sender=user).count()
        unread = Message.objects.filter(
            thread__participant_two=user,
            is_read=False,
        ).count()

        # Phishing flags in received messages
        phishing_received = Message.objects.filter(
            thread__participant_two=user,
            is_phishing_flagged=True,
        ).count()

        # Avg response time (hours) for threads user is in
        # Approximate: measure time between consecutive messages in threads
        threads = MessageThread.objects.filter(
            Q(participant_one=user) | Q(participant_two=user)
        ).prefetch_related("messages")

        response_times = []
        for t in threads[:50]:
            msgs = list(t.messages.order_by("created_at"))
            for i in range(1, len(msgs)):
                if msgs[i].sender_id == user.id and msgs[i - 1].sender_id != user.id:
                    delta_hours = (msgs[i].created_at - msgs[i - 1].created_at).total_seconds() / 3600
                    response_times.append(delta_hours)

        avg_response_h = round(sum(response_times) / len(response_times), 1) if response_times else None

        return Response({
            "total_threads": total_threads,
            "total_sent": total_sent,
            "unread_messages": unread,
            "phishing_flags_received": phishing_received,
            "avg_response_time_hours": avg_response_h,
            "response_speed_label": (
                "Excellent" if avg_response_h and avg_response_h < 4
                else "Good" if avg_response_h and avg_response_h < 24
                else "Needs improvement" if avg_response_h
                else "No data"
            ),
        })


# ── Auto-Archive and Spam Handling ────────────────────────────────────────────

class ThreadArchiveView(APIView):
    """
    POST /messaging/threads/<uuid:thread_id>/archive/
    Archive or unarchive a thread for the current user.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, thread_id):
        try:
            thread = MessageThread.objects.get(pk=thread_id)
        except MessageThread.DoesNotExist:
            return Response(status=404)

        action = request.data.get("action", "archive")  # archive | unarchive | mark_spam
        is_one = thread.participant_one_id == request.user.id

        if action == "archive":
            if is_one:
                thread.is_archived_one = True
            else:
                thread.is_archived_two = True
            thread.save(update_fields=["is_archived_one" if is_one else "is_archived_two"])

        elif action == "unarchive":
            if is_one:
                thread.is_archived_one = False
            else:
                thread.is_archived_two = False
            thread.save(update_fields=["is_archived_one" if is_one else "is_archived_two"])

        elif action == "mark_spam":
            # Flag all messages from the other party as phishing
            other_id = thread.participant_two_id if is_one else thread.participant_one_id
            Message.objects.filter(thread=thread, sender_id=other_id).update(is_phishing_flagged=True)
            if is_one:
                thread.is_archived_one = True
            else:
                thread.is_archived_two = True
            thread.save(update_fields=["is_archived_one" if is_one else "is_archived_two"])

        return Response({"status": action, "thread_id": str(thread_id)})


# ── Verified Sender Badge Info ────────────────────────────────────────────────

class VerifiedSenderInfoView(APIView):
    """
    GET /messaging/verified-sender/<uuid:user_id>/
    Returns verification badge info for a sender — used in thread header.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, user_id):
        badge = VerifiedSenderBadge.objects.filter(user_id=user_id, is_active=True).first()
        if not badge:
            return Response({"is_verified": False, "badge_type": None})
        return Response({
            "is_verified": True,
            "badge_type": badge.badge_type,
            "badge_label": badge.get_badge_type_display(),
            "issued_at": badge.issued_at,
            "expires_at": badge.expires_at,
        })
