"""Offer letter views — candidate-facing offer review and accept/decline endpoint."""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny


class PortalOfferReviewView(APIView):
    """Candidate reviews and accepts/declines offer."""
    permission_classes = [AllowAny]

    def get(self, request):
        """View offer details."""
        import jwt
        from django.conf import settings

        token = request.query_params.get("token")
        if not token:
            return Response({"error": "Token required"}, status=400)

        portal_secret = getattr(settings, 'PORTAL_SECRET_KEY', settings.SECRET_KEY)
        try:
            payload = jwt.decode(token, portal_secret, algorithms=["HS256"])
            if payload.get("purpose") != "offer_review":
                raise jwt.InvalidTokenError("Wrong purpose")
        except jwt.InvalidTokenError:
            return Response({"error": "Invalid token"}, status=401)

        from apps.applications.models import Offer

        try:
            offer = Offer.objects.select_related("application__job").get(
                application_id=payload.get("application_id"),
                tenant_id=payload["tenant_id"],
                status="pending",
            )
        except Offer.DoesNotExist:
            return Response({"error": "Offer not found"}, status=404)

        return Response({
            "offer_id": str(offer.id),
            "job_title": offer.application.job.title if offer.application and offer.application.job else "",
            "salary": str(offer.salary_amount) if offer.salary_amount else None,
            "currency": offer.salary_currency,
            "valid_until": offer.expires_at.isoformat() if offer.expires_at else None,
            "status": offer.status,
        })

    def post(self, request):
        """Accept or decline offer."""
        import jwt
        from django.conf import settings

        token = request.data.get("token")
        decision = request.data.get("decision")  # "accept" or "decline"

        if not token or decision not in ("accept", "decline"):
            return Response({"error": "Token and decision (accept/decline) required"}, status=400)

        portal_secret = getattr(settings, 'PORTAL_SECRET_KEY', settings.SECRET_KEY)
        try:
            payload = jwt.decode(token, portal_secret, algorithms=["HS256"])
            if payload.get("purpose") != "offer_review":
                raise jwt.InvalidTokenError("Wrong purpose")
        except jwt.InvalidTokenError:
            return Response({"error": "Invalid token"}, status=401)

        from apps.applications.models import Offer

        try:
            offer = Offer.objects.get(
                application_id=payload.get("application_id"),
                tenant_id=payload["tenant_id"],
                status="pending",
            )
        except Offer.DoesNotExist:
            return Response({"error": "Offer not found"}, status=404)

        if decision == "accept":
            offer.status = "accepted"
        else:
            offer.status = "declined"
            offer.decline_reason = request.data.get("reason", "")

        offer.save()
        return Response({"offer_id": str(offer.id), "status": offer.status})
