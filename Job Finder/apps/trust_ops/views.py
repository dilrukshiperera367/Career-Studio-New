"""Trust Ops — views."""
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import StrikeRecord, SuspensionRecord, ScamAlert, PhishingMessageReport, IdentityProofRequest
from .serializers import (
    StrikeRecordSerializer, SuspensionRecordSerializer, ScamAlertSerializer,
    PhishingMessageReportSerializer, IdentityProofRequestSerializer,
)


class StrikeListView(APIView):
    """Admin: list and issue strikes."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        strikes = StrikeRecord.objects.all().select_related("target_user", "target_employer")[:100]
        return Response(StrikeRecordSerializer(strikes, many=True).data)

    def post(self, request):
        user_id = request.data.get("user_id")
        employer_id = request.data.get("employer_id")
        reason = request.data.get("reason", "policy")
        description = request.data.get("description", "")
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            target_user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        strike_count = StrikeRecord.objects.filter(target_user=target_user, is_active=True).count() + 1
        strike = StrikeRecord.objects.create(
            target_user=target_user,
            employer_id=employer_id,
            issued_by=request.user,
            reason=reason,
            description=description,
            strike_number=strike_count,
        )
        return Response(StrikeRecordSerializer(strike).data, status=status.HTTP_201_CREATED)


class SuspendUserView(APIView):
    """Admin: suspend an employer/user account."""
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user_id = request.data.get("user_id")
        try:
            target_user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        suspension = SuspensionRecord.objects.create(
            target_user=target_user,
            employer_id=request.data.get("employer_id"),
            suspension_type=request.data.get("suspension_type", "temporary"),
            reason=request.data.get("reason", ""),
            suspended_by=request.user,
            starts_at=timezone.now(),
            ends_at=request.data.get("ends_at"),
        )
        # Deactivate user
        target_user.is_active = False
        target_user.save(update_fields=["is_active"])
        return Response(SuspensionRecordSerializer(suspension).data, status=status.HTTP_201_CREATED)


class RiskScoreView(APIView):
    """Get dynamic risk score for an employer."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, employer_id):
        from apps.employers.models import EmployerAccount
        try:
            employer = EmployerAccount.objects.get(pk=employer_id)
        except EmployerAccount.DoesNotExist:
            return Response({"detail": "Employer not found."}, status=status.HTTP_404_NOT_FOUND)
        strikes = StrikeRecord.objects.filter(target_employer=employer, is_active=True).count()
        fraud_reports = ScamAlert.objects.filter(employer=employer, is_resolved=False).count()
        risk = min(100, strikes * 20 + fraud_reports * 15)
        return Response({
            "employer_id": str(employer_id),
            "company_name": employer.company_name,
            "risk_score": risk,
            "active_strikes": strikes,
            "open_fraud_reports": fraud_reports,
            "is_verified": employer.is_verified,
        })


class PhishingReportView(APIView):
    """Report a phishing message."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ser = PhishingMessageReportSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        report = ser.save(reporter=request.user)
        return Response(PhishingMessageReportSerializer(report).data, status=status.HTTP_201_CREATED)


class ScamAlertListView(APIView):
    """List active scam alerts (public view shows only is_public=True)."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        filters = {"is_resolved": False}
        if not (request.user.is_authenticated and request.user.is_staff):
            filters["is_public"] = True
        alerts = ScamAlert.objects.filter(**filters).order_by("-created_at")[:50]
        return Response(ScamAlertSerializer(alerts, many=True).data)
