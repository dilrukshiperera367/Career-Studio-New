"""Employers TalentOS views — JD Builder, Interview Kits, Silver Medalists, Referrals, CRM, Career Site, Debriefs."""
import uuid
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    JobDescription, InterviewKit, SilverMedalist,
    ReferralCampaign, Referral, RecruiterContact,
    CareerSitePage, InterviewDebrief,
)
from .serializers import (
    JobDescriptionSerializer, InterviewKitSerializer, SilverMedalistSerializer,
    ReferralCampaignSerializer, ReferralSerializer, RecruiterContactSerializer,
    CareerSitePageSerializer, InterviewDebriefSerializer,
)


def _get_employer_for_user(request):
    m = request.user.employer_memberships.filter(role__in=["owner", "admin"]).select_related("employer").first()
    return m.employer if m else None


# ── JD Builder ────────────────────────────────────────────────────────────────

class JobDescriptionListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        employer = _get_employer_for_user(request)
        if not employer:
            return Response({"detail": "No employer account."}, status=status.HTTP_404_NOT_FOUND)
        jds = JobDescription.objects.filter(employer=employer).order_by("-created_at")
        return Response(JobDescriptionSerializer(jds, many=True).data)

    def post(self, request):
        employer = _get_employer_for_user(request)
        if not employer:
            return Response({"detail": "No employer account."}, status=status.HTTP_400_BAD_REQUEST)
        ser = JobDescriptionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        jd = ser.save(employer=employer, created_by=request.user)
        return Response(JobDescriptionSerializer(jd).data, status=status.HTTP_201_CREATED)


class JobDescriptionDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _get(self, request, pk):
        employer = _get_employer_for_user(request)
        if not employer:
            return None, Response({"detail": "No employer account."}, status=status.HTTP_404_NOT_FOUND)
        try:
            return JobDescription.objects.get(pk=pk, employer=employer), None
        except JobDescription.DoesNotExist:
            return None, Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    def get(self, request, pk):
        obj, err = self._get(request, pk)
        return err or Response(JobDescriptionSerializer(obj).data)

    def patch(self, request, pk):
        obj, err = self._get(request, pk)
        if err:
            return err
        ser = JobDescriptionSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)

    def delete(self, request, pk):
        obj, err = self._get(request, pk)
        if err:
            return err
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Interview Kits ────────────────────────────────────────────────────────────

class InterviewKitListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        employer = _get_employer_for_user(request)
        if not employer:
            return Response({"detail": "No employer account."}, status=status.HTTP_404_NOT_FOUND)
        kits = InterviewKit.objects.filter(employer=employer).order_by("-created_at")
        return Response(InterviewKitSerializer(kits, many=True).data)

    def post(self, request):
        employer = _get_employer_for_user(request)
        if not employer:
            return Response({"detail": "No employer account."}, status=status.HTTP_400_BAD_REQUEST)
        ser = InterviewKitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        kit = ser.save(employer=employer, created_by=request.user)
        return Response(InterviewKitSerializer(kit).data, status=status.HTTP_201_CREATED)


class InterviewKitDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        employer = _get_employer_for_user(request)
        if not employer:
            return Response({"detail": "No employer account."}, status=status.HTTP_404_NOT_FOUND)
        try:
            kit = InterviewKit.objects.get(pk=pk, employer=employer)
        except InterviewKit.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(InterviewKitSerializer(kit).data)

    def delete(self, request, pk):
        employer = _get_employer_for_user(request)
        if not employer:
            return Response({"detail": "No employer account."}, status=status.HTTP_404_NOT_FOUND)
        try:
            kit = InterviewKit.objects.get(pk=pk, employer=employer)
        except InterviewKit.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        kit.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class InterviewQuestionListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, kit_id):
        try:
            kit = InterviewKit.objects.get(pk=kit_id)
        except InterviewKit.DoesNotExist:
            return Response({"detail": "Kit not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"kit_id": str(kit_id), "questions": kit.questions})

    def post(self, request, kit_id):
        try:
            kit = InterviewKit.objects.get(pk=kit_id)
        except InterviewKit.DoesNotExist:
            return Response({"detail": "Kit not found."}, status=status.HTTP_404_NOT_FOUND)
        question = request.data.get("question", "")
        if not question:
            return Response({"detail": "question is required."}, status=status.HTTP_400_BAD_REQUEST)
        questions = kit.questions or []
        questions.append({"id": str(uuid.uuid4()), "question": question, "notes": request.data.get("notes", "")})
        kit.questions = questions
        kit.save(update_fields=["questions"])
        return Response({"questions": kit.questions}, status=status.HTTP_201_CREATED)


# ── Silver Medalists ──────────────────────────────────────────────────────────

class SilverMedalistListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        employer = _get_employer_for_user(request)
        if not employer:
            return Response({"detail": "No employer account."}, status=status.HTTP_404_NOT_FOUND)
        medals = SilverMedalist.objects.filter(employer=employer).order_by("-created_at")
        return Response(SilverMedalistSerializer(medals, many=True).data)

    def post(self, request):
        employer = _get_employer_for_user(request)
        if not employer:
            return Response({"detail": "No employer account."}, status=status.HTTP_400_BAD_REQUEST)
        ser = SilverMedalistSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = ser.save(employer=employer)
        return Response(SilverMedalistSerializer(obj).data, status=status.HTTP_201_CREATED)


class SilverMedalistDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        employer = _get_employer_for_user(request)
        if not employer:
            return Response({"detail": "No employer account."}, status=status.HTTP_404_NOT_FOUND)
        try:
            obj = SilverMedalist.objects.get(pk=pk, employer=employer)
        except SilverMedalist.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Referral Campaigns ────────────────────────────────────────────────────────

class ReferralCampaignListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        employer = _get_employer_for_user(request)
        if not employer:
            return Response({"detail": "No employer account."}, status=status.HTTP_404_NOT_FOUND)
        campaigns = ReferralCampaign.objects.filter(employer=employer)
        return Response(ReferralCampaignSerializer(campaigns, many=True).data)

    def post(self, request):
        employer = _get_employer_for_user(request)
        if not employer:
            return Response({"detail": "No employer account."}, status=status.HTTP_400_BAD_REQUEST)
        ser = ReferralCampaignSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = ser.save(employer=employer)
        return Response(ReferralCampaignSerializer(obj).data, status=status.HTTP_201_CREATED)


class ReferralCampaignDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            obj = ReferralCampaign.objects.get(pk=pk)
        except ReferralCampaign.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ReferralCampaignSerializer(obj).data)


class ReferralCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ser = ReferralSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = ser.save(referrer=request.user)
        return Response(ReferralSerializer(obj).data, status=status.HTTP_201_CREATED)


# ── Recruiter CRM ─────────────────────────────────────────────────────────────

class RecruiterContactListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        employer = _get_employer_for_user(request)
        if not employer:
            return Response([])
        contacts = RecruiterContact.objects.filter(employer=employer).order_by("name")
        return Response(RecruiterContactSerializer(contacts, many=True).data)

    def post(self, request):
        employer = _get_employer_for_user(request)
        if not employer:
            return Response({"detail": "No employer account."}, status=status.HTTP_400_BAD_REQUEST)
        ser = RecruiterContactSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = ser.save(employer=employer, added_by=request.user)
        return Response(RecruiterContactSerializer(obj).data, status=status.HTTP_201_CREATED)


class RecruiterContactDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        try:
            obj = RecruiterContact.objects.get(pk=pk)
        except RecruiterContact.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Career Site CMS ──────────────────────────────────────────────────────────

class CareerSitePageListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        employer = _get_employer_for_user(request)
        if not employer:
            return Response([])
        pages = CareerSitePage.objects.filter(employer=employer).order_by("sort_order")
        return Response(CareerSitePageSerializer(pages, many=True).data)

    def post(self, request):
        employer = _get_employer_for_user(request)
        if not employer:
            return Response({"detail": "No employer account."}, status=status.HTTP_400_BAD_REQUEST)
        ser = CareerSitePageSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = ser.save(employer=employer)
        return Response(CareerSitePageSerializer(obj).data, status=status.HTTP_201_CREATED)


class CareerSitePageDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            obj = CareerSitePage.objects.get(pk=pk)
        except CareerSitePage.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(CareerSitePageSerializer(obj).data)

    def delete(self, request, pk):
        try:
            obj = CareerSitePage.objects.get(pk=pk)
        except CareerSitePage.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Interview Debriefs ────────────────────────────────────────────────────────

class InterviewDebriefListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        employer = _get_employer_for_user(request)
        if not employer:
            return Response([])
        debriefs = InterviewDebrief.objects.filter(employer=employer).order_by("-created_at")
        return Response(InterviewDebriefSerializer(debriefs, many=True).data)

    def post(self, request):
        employer = _get_employer_for_user(request)
        if not employer:
            return Response({"detail": "No employer account."}, status=status.HTTP_400_BAD_REQUEST)
        ser = InterviewDebriefSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = ser.save(employer=employer, interviewer=request.user)
        return Response(InterviewDebriefSerializer(obj).data, status=status.HTTP_201_CREATED)


class InterviewDebriefDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, debrief_id):
        try:
            obj = InterviewDebrief.objects.get(pk=debrief_id)
        except InterviewDebrief.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(InterviewDebriefSerializer(obj).data)


class DebriefFeedbackCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, debrief_id):
        try:
            debrief = InterviewDebrief.objects.get(pk=debrief_id)
        except InterviewDebrief.DoesNotExist:
            return Response({"detail": "Debrief not found."}, status=status.HTTP_404_NOT_FOUND)
        # Add feedback to debrief notes
        feedback_text = request.data.get("feedback", "")
        notes = debrief.notes or ""
        debrief.notes = f"{notes}\n\n[Feedback by {request.user}]: {feedback_text}".strip()
        debrief.save(update_fields=["notes"])
        return Response({"saved": True, "debrief_id": str(debrief_id)}, status=status.HTTP_201_CREATED)
