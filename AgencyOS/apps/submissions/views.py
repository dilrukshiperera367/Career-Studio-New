"""Submissions views."""
from django.utils import timezone
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import CandidateProfile, Submission, SubmissionStatusHistory, Shortlist, SendToClientLog
from .serializers import (
    CandidateProfileSerializer, CandidateProfileListSerializer,
    SubmissionSerializer, SubmissionListSerializer,
    ShortlistSerializer, SendToClientLogSerializer,
)


def get_agency_ids(user):
    from apps.agencies.models import Agency, AgencyRecruiter
    owned = Agency.objects.filter(owner=user).values_list("id", flat=True)
    staff = AgencyRecruiter.objects.filter(user=user, is_active=True).values_list("agency_id", flat=True)
    return list(set(list(owned) + list(staff)))


def get_first_agency(user):
    from apps.agencies.models import Agency
    return Agency.objects.filter(id__in=get_agency_ids(user)).first()


class CandidateProfileViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["first_name", "last_name", "email", "skills"]
    filterset_fields = [
        "ownership_status", "contract_preference", "work_auth_status",
        "do_not_submit", "do_not_rehire", "is_redeployable",
    ]
    ordering_fields = ["created_at", "quality_score", "available_from"]

    def get_queryset(self):
        return CandidateProfile.objects.filter(
            agency_id__in=get_agency_ids(self.request.user)
        ).select_related("owning_recruiter")

    def get_serializer_class(self):
        if self.action == "list":
            return CandidateProfileListSerializer
        return CandidateProfileSerializer

    def perform_create(self, serializer):
        serializer.save(
            agency=get_first_agency(self.request.user),
            owning_recruiter=self.request.user,
        )

    @action(detail=True, methods=["post"])
    def merge(self, request, pk=None):
        target = self.get_object()
        source_id = request.data.get("source_id")
        if not source_id:
            return Response({"error": "source_id required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            source = CandidateProfile.objects.get(id=source_id, agency=target.agency)
        except CandidateProfile.DoesNotExist:
            return Response({"error": "Source candidate not found"}, status=status.HTTP_404_NOT_FOUND)
        source.merged_into = target
        source.is_duplicate = True
        source.save()
        return Response({"status": "merged", "target_id": str(target.id)})


class SubmissionViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["candidate__first_name", "candidate__last_name", "recruiter_pitch"]
    filterset_fields = ["status", "job_order", "candidate", "ownership_verified"]
    ordering_fields = ["created_at", "match_score", "rank_in_shortlist"]

    def get_queryset(self):
        return Submission.objects.filter(
            agency_id__in=get_agency_ids(self.request.user)
        ).select_related("candidate", "job_order", "submitted_by")

    def get_serializer_class(self):
        if self.action == "list":
            return SubmissionListSerializer
        return SubmissionSerializer

    def perform_create(self, serializer):
        serializer.save(
            agency=get_first_agency(self.request.user),
            submitted_by=self.request.user,
        )

    @action(detail=True, methods=["post"])
    def advance_status(self, request, pk=None):
        sub = self.get_object()
        new_status = request.data.get("status")
        if new_status not in [s[0] for s in Submission.Status.choices]:
            return Response({"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)
        old = sub.status
        sub.status = new_status
        sub.save()
        SubmissionStatusHistory.objects.create(
            submission=sub,
            previous_status=old,
            new_status=new_status,
            changed_by=request.user,
            reason=request.data.get("reason", ""),
        )
        return Response({"status": new_status})

    @action(detail=True, methods=["post"])
    def send_to_client(self, request, pk=None):
        sub = self.get_object()
        sub.sent_to_client_at = timezone.now()
        sub.sent_to_client_by = request.user
        sub.status = Submission.Status.SUBMITTED
        sub.save()
        SendToClientLog.objects.create(
            agency=sub.agency,
            submission=sub,
            sent_by=request.user,
            recipient_email=request.data.get("recipient_email", ""),
            method=request.data.get("method", "email"),
        )
        return Response({"status": "sent"})


class ShortlistViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status", "job_order"]
    ordering_fields = ["created_at", "sent_at"]

    def get_queryset(self):
        return Shortlist.objects.filter(
            agency_id__in=get_agency_ids(self.request.user)
        ).prefetch_related("submissions")

    def get_serializer_class(self):
        return ShortlistSerializer

    def perform_create(self, serializer):
        serializer.save(
            agency=get_first_agency(self.request.user),
            sent_by=self.request.user,
        )
