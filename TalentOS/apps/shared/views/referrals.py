"""Referral views — employee referral submission endpoint."""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny


class PortalReferralView(APIView):
    """Employee refers a candidate through a form."""
    permission_classes = [AllowAny]

    def post(self, request):
        import jwt
        from django.conf import settings

        token = request.data.get("token")
        if not token:
            return Response({"error": "Token required"}, status=400)

        portal_secret = getattr(settings, 'PORTAL_SECRET_KEY', settings.SECRET_KEY)
        try:
            payload = jwt.decode(token, portal_secret, algorithms=["HS256"])
            if payload.get("purpose") != "referral":
                raise jwt.InvalidTokenError("Wrong purpose")
        except jwt.InvalidTokenError:
            return Response({"error": "Invalid token"}, status=401)

        from apps.candidates.models import Candidate
        from apps.candidates.services import resolve_candidate

        full_name = request.data.get("full_name", "")
        email = request.data.get("email", "")
        phone = request.data.get("phone", "")
        job_id = request.data.get("job_id")
        referrer_note = request.data.get("note", "")

        if not full_name or not email:
            return Response({"error": "full_name and email required"}, status=400)

        # Resolve or create candidate — resolve_candidate returns a dict, not a model instance
        result = resolve_candidate(
            tenant_id=payload["tenant_id"],
            full_name=full_name,
            email=email,
            phone=phone,
        )

        tenant_id = payload["tenant_id"]
        if result["candidate_id"] is not None:
            try:
                candidate = Candidate.objects.get(id=result["candidate_id"], tenant_id=tenant_id)
            except Candidate.DoesNotExist:
                candidate = None
        else:
            candidate = None

        if candidate is None:
            candidate = Candidate.objects.create(
                tenant_id=tenant_id,
                full_name=full_name,
                primary_email=email,
                primary_phone=phone,
                source="referral",
            )

        # Add referrer info as tag
        referrer_id = payload.get("referrer_id", "")
        candidate.tags = list(set((candidate.tags or []) + [f"referral:{referrer_id}"]))
        candidate.save(update_fields=["tags", "updated_at"])

        return Response({
            "candidate_id": str(candidate.id),
            "status": "referred",
            "referrer_id": referrer_id,
        }, status=201)
