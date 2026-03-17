"""Moderation views — Reports, moderation actions, employer verification queue."""
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.shared.permissions import IsModerator, IsAdmin
from apps.employers.models import EmployerAccount
from .models import Report, ModerationAction
from .serializers import (
    ReportCreateSerializer, ReportSerializer,
    ReportResolveSerializer, ModerationActionSerializer,
)


class ReportCreateView(generics.CreateAPIView):
    """Any authenticated user can submit a report."""
    serializer_class = ReportCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)


class ReportListView(generics.ListAPIView):
    """Moderators/admins can view all reports."""
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated, IsModerator | IsAdmin]

    def get_queryset(self):
        qs = Report.objects.all().order_by("-created_at")
        stat = self.request.query_params.get("status")
        if stat:
            qs = qs.filter(status=stat)
        content_type = self.request.query_params.get("content_type")
        if content_type:
            qs = qs.filter(content_type=content_type)
        return qs


class ReportDetailView(generics.RetrieveAPIView):
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated, IsModerator | IsAdmin]
    queryset = Report.objects.all()


class ReportResolveView(APIView):
    """Resolve a pending report."""
    permission_classes = [permissions.IsAuthenticated, IsModerator | IsAdmin]

    def post(self, request, pk):
        try:
            report = Report.objects.get(pk=pk)
        except Report.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = ReportResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report.status = serializer.validated_data["status"]
        report.resolution_notes = serializer.validated_data.get("resolution_notes", "")
        report.reviewed_by = request.user
        report.resolved_at = timezone.now()
        report.save()

        action_type = serializer.validated_data.get("action", "")
        if action_type:
            ModerationAction.objects.create(
                moderator=request.user,
                report=report,
                action=action_type,
                target_type=report.content_type,
                target_id=report.content_id,
            )
        return Response(ReportSerializer(report).data)


class ModerationActionListView(generics.ListAPIView):
    serializer_class = ModerationActionSerializer
    permission_classes = [permissions.IsAuthenticated, IsModerator | IsAdmin]
    queryset = ModerationAction.objects.all().order_by("-created_at")


class EmployerVerificationQueueView(generics.ListAPIView):
    """Queue of employer profiles pending verification (#35)."""
    permission_classes = [permissions.IsAuthenticated, IsModerator | IsAdmin]

    def get_queryset(self):
        return EmployerAccount.objects.filter(
            is_verified=False,
            registration_no__gt="",
        ).order_by("-created_at")

    def get(self, request, *args, **kwargs):
        qs = self.get_queryset()
        data = [
            {
                "id": str(ep.id),
                "company_name": ep.company_name,
                "registration_no": ep.registration_no,
                "created_at": ep.created_at.isoformat(),
            }
            for ep in qs[:50]
        ]
        return Response(data)


class EmployerVerificationActionView(APIView):
    """Approve or reject an employer verification request (#35)."""
    permission_classes = [permissions.IsAuthenticated, IsModerator | IsAdmin]

    def post(self, request, pk):
        try:
            account = EmployerAccount.objects.get(pk=pk)
        except EmployerAccount.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        action = request.data.get("action")
        if action not in ("approve", "reject"):
            return Response({"detail": "action must be 'approve' or 'reject'"}, status=status.HTTP_400_BAD_REQUEST)

        if action == "approve":
            account.is_verified = True
            account.verification_badge = "basic"
            account.save(update_fields=["is_verified", "verification_badge"])

            ModerationAction.objects.create(
                moderator=request.user,
                action="approve",
                target_type="employer",
                target_id=str(account.id),
                notes=request.data.get("notes", ""),
            )
        else:
            ModerationAction.objects.create(
                moderator=request.user,
                action="reject",
                target_type="employer",
                target_id=str(account.id),
                notes=request.data.get("notes", ""),
            )

        return Response({"detail": f"Employer {action}d successfully."})
