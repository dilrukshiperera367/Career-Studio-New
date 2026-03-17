"""API for Talent CRM app — talent pools, prospects, nurture sequences, campaigns."""

from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.talent_crm.models import (
    TalentPool, TalentPoolMember, Prospect,
    NurtureSequence, NurtureStep, NurtureEnrollment,
    OutreachCampaign, DoNotContact,
)
from apps.accounts.permissions import IsRecruiter, HasTenantAccess


# ── Serializers ───────────────────────────────────────────────────────────────

class TalentPoolMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = TalentPoolMember
        fields = "__all__"
        read_only_fields = ["id", "tenant", "added_at"]


class TalentPoolSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = TalentPool
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at"]

    def get_member_count(self, obj):
        return obj.members.count()


class ProspectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prospect
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at"]


class NurtureStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = NurtureStep
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at"]


class NurtureSequenceSerializer(serializers.ModelSerializer):
    steps = NurtureStepSerializer(many=True, read_only=True)

    class Meta:
        model = NurtureSequence
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at"]


class NurtureEnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = NurtureEnrollment
        fields = "__all__"
        read_only_fields = ["id", "tenant", "enrolled_at", "updated_at"]


class OutreachCampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutreachCampaign
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at", "updated_at"]


class DoNotContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoNotContact
        fields = "__all__"
        read_only_fields = ["id", "tenant", "created_at"]


# ── ViewSets ──────────────────────────────────────────────────────────────────

class TalentPoolViewSet(viewsets.ModelViewSet):
    serializer_class = TalentPoolSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["is_active", "pool_type"]
    search_fields = ["name", "description"]

    def get_queryset(self):
        return TalentPool.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id, owner=self.request.user)

    @action(detail=True, methods=["post"])
    def add_member(self, request, pk=None):
        pool = self.get_object()
        candidate_id = request.data.get("candidate_id")
        if not candidate_id:
            return Response({"error": "candidate_id required"}, status=status.HTTP_400_BAD_REQUEST)
        member, created = TalentPoolMember.objects.get_or_create(
            tenant_id=request.tenant_id,
            pool=pool,
            candidate_id=candidate_id,
            defaults={"added_by": request.user},
        )
        return Response(TalentPoolMemberSerializer(member).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def members(self, request, pk=None):
        pool = self.get_object()
        qs = TalentPoolMember.objects.filter(tenant_id=request.tenant_id, pool=pool)
        return Response(TalentPoolMemberSerializer(qs, many=True).data)


class ProspectViewSet(viewsets.ModelViewSet):
    serializer_class = ProspectSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["status", "source"]
    search_fields = ["first_name", "last_name", "email", "headline"]

    def get_queryset(self):
        return Prospect.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id, owner=self.request.user)


class NurtureSequenceViewSet(viewsets.ModelViewSet):
    serializer_class = NurtureSequenceSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["is_active"]
    search_fields = ["name"]

    def get_queryset(self):
        return NurtureSequence.objects.filter(tenant_id=self.request.tenant_id).prefetch_related("steps")

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class NurtureEnrollmentViewSet(viewsets.ModelViewSet):
    serializer_class = NurtureEnrollmentSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["sequence", "status"]

    def get_queryset(self):
        return NurtureEnrollment.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)


class OutreachCampaignViewSet(viewsets.ModelViewSet):
    serializer_class = OutreachCampaignSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["status", "channel"]
    search_fields = ["name"]

    def get_queryset(self):
        return OutreachCampaign.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id, created_by=self.request.user)


class DoNotContactViewSet(viewsets.ModelViewSet):
    serializer_class = DoNotContactSerializer
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]
    filterset_fields = ["reason"]
    search_fields = ["email"]

    def get_queryset(self):
        return DoNotContact.objects.filter(tenant_id=self.request.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id, added_by=self.request.user)


# ── Router & URLs ─────────────────────────────────────────────────────────────

router = DefaultRouter()
router.register("pools", TalentPoolViewSet, basename="talent-pools")
router.register("prospects", ProspectViewSet, basename="prospects")
router.register("sequences", NurtureSequenceViewSet, basename="nurture-sequences")
router.register("enrollments", NurtureEnrollmentViewSet, basename="nurture-enrollments")
router.register("campaigns", OutreachCampaignViewSet, basename="outreach-campaigns")
router.register("do-not-contact", DoNotContactViewSet, basename="do-not-contact")

urlpatterns = [path("", include(router.urls))]
