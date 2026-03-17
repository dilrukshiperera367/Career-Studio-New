"""CampusOS — Placements views."""

from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, filters, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from apps.shared.permissions import IsPlacementOfficer, IsCampusAdmin
from apps.students.models import StudentProfile
from .models import (
    DriveOffer,
    DriveSlot,
    PlacementDrive,
    PlacementSeason,
    StudentDriveRegistration,
)
from .serializers import (
    DriveOfferSerializer,
    DriveSlotSerializer,
    PlacementDriveSerializer,
    PlacementSeasonSerializer,
    StudentDriveRegistrationSerializer,
)


class PlacementSeasonListCreateView(generics.ListCreateAPIView):
    serializer_class = PlacementSeasonSerializer
    permission_classes = [permissions.IsAuthenticated, IsPlacementOfficer]

    def get_queryset(self):
        return PlacementSeason.objects.filter(campus=self.request.user.campus)

    def perform_create(self, serializer):
        serializer.save(campus=self.request.user.campus)


class PlacementSeasonDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = PlacementSeasonSerializer
    permission_classes = [permissions.IsAuthenticated, IsPlacementOfficer]

    def get_queryset(self):
        return PlacementSeason.objects.filter(campus=self.request.user.campus)


class PlacementDriveListView(generics.ListAPIView):
    """Students browse open placement drives."""
    serializer_class = PlacementDriveSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["status", "drive_type", "is_dream_company"]
    search_fields = ["company_name", "role_title"]

    def get_queryset(self):
        return PlacementDrive.objects.filter(
            campus=self.request.user.campus,
            status__in=["announced", "open", "shortlisting", "testing", "interviewing"],
        )


class PlacementDriveManageView(generics.ListCreateAPIView):
    """Placement officers manage all drives."""
    serializer_class = PlacementDriveSerializer
    permission_classes = [permissions.IsAuthenticated, IsPlacementOfficer]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["status", "season", "drive_type"]
    search_fields = ["company_name", "role_title"]

    def get_queryset(self):
        return PlacementDrive.objects.filter(campus=self.request.user.campus)

    def perform_create(self, serializer):
        serializer.save(campus=self.request.user.campus, created_by=self.request.user)


class PlacementDriveDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PlacementDriveSerializer
    permission_classes = [permissions.IsAuthenticated, IsPlacementOfficer]

    def get_queryset(self):
        return PlacementDrive.objects.filter(campus=self.request.user.campus)


class StudentDriveRegistrationListView(generics.ListCreateAPIView):
    """Student registers for a drive; staff views all registrations."""
    serializer_class = StudentDriveRegistrationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["status", "is_eligible"]
    search_fields = ["student__user__first_name", "student__user__last_name"]

    def get_queryset(self):
        user = self.request.user
        if user.role in ("placement_officer", "campus_admin", "super_admin"):
            qs = StudentDriveRegistration.objects.filter(drive__campus=user.campus)
            drive_id = self.kwargs.get("drive_id")
            if drive_id:
                qs = qs.filter(drive_id=drive_id)
            return qs
        return StudentDriveRegistration.objects.filter(student__user=user)

    def perform_create(self, serializer):
        student = get_object_or_404(StudentProfile, user=self.request.user)
        serializer.save(student=student)


class ShortlistStudentView(APIView):
    """Placement officer shortlists a student for a drive."""
    permission_classes = [permissions.IsAuthenticated, IsPlacementOfficer]

    def post(self, request, registration_id):
        reg = get_object_or_404(
            StudentDriveRegistration,
            id=registration_id,
            drive__campus=request.user.campus,
        )
        reg.status = StudentDriveRegistration.Status.SHORTLISTED
        import django.utils.timezone as tz
        reg.shortlisted_at = tz.now()
        reg.save(update_fields=["status", "shortlisted_at"])
        return Response({"detail": "Student shortlisted."})


class DriveSlotListCreateView(generics.ListCreateAPIView):
    serializer_class = DriveSlotSerializer
    permission_classes = [permissions.IsAuthenticated, IsPlacementOfficer]

    def get_queryset(self):
        return DriveSlot.objects.filter(drive_id=self.kwargs["drive_id"])

    def perform_create(self, serializer):
        drive = get_object_or_404(PlacementDrive, id=self.kwargs["drive_id"])
        serializer.save(drive=drive)


class DriveOfferListCreateView(generics.ListCreateAPIView):
    serializer_class = DriveOfferSerializer
    permission_classes = [permissions.IsAuthenticated, IsPlacementOfficer]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status"]

    def get_queryset(self):
        user = self.request.user
        if user.role in ("placement_officer", "campus_admin"):
            return DriveOffer.objects.filter(drive__campus=user.campus)
        return DriveOffer.objects.filter(student__user=user)

    def perform_create(self, serializer):
        serializer.save()


class AcceptOfferView(APIView):
    """Student accepts a placement offer."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        offer = get_object_or_404(DriveOffer, id=pk, student__user=request.user)
        if offer.status != DriveOffer.Status.EXTENDED:
            return Response({"detail": "Offer cannot be accepted."}, status=status.HTTP_400_BAD_REQUEST)
        import django.utils.timezone as tz
        offer.status = DriveOffer.Status.ACCEPTED
        offer.accepted_at = tz.now()
        offer.is_final_offer = True
        offer.save(update_fields=["status", "accepted_at", "is_final_offer"])
        # Mark student as placed
        student = offer.student
        student.placement_eligibility = "placed"
        student.placed_at_company = offer.drive.company_name
        student.placed_package_lkr = offer.ctc_lkr
        student.placement_date = offer.accepted_at.date()
        student.save(update_fields=[
            "placement_eligibility", "placed_at_company",
            "placed_package_lkr", "placement_date",
        ])
        return Response({"detail": "Offer accepted."})
