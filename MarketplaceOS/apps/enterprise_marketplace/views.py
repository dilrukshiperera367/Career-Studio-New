from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone as tz
from django.utils.text import slugify
from .models import (
    EnterpriseAccount, EnterpriseTeamMember, EnterpriseBudget,
    EnterpriseApprovedProvider, EnterpriseCatalogItem,
    EnterpriseBookingApproval, InternalMentorProgram, InternalMentorMatch,
)
from .serializers import (
    EnterpriseAccountSerializer, EnterpriseTeamMemberSerializer,
    EnterpriseBudgetSerializer, EnterpriseApprovedProviderSerializer,
    EnterpriseCatalogItemSerializer, EnterpriseBookingApprovalSerializer,
    InternalMentorProgramSerializer, InternalMentorMatchSerializer,
)


def is_enterprise_admin(user, enterprise):
    return enterprise.members.filter(user=user, role__in=["admin", "manager"], is_active=True).exists() \
           or enterprise.primary_admin == user or user.role == "admin"


class EnterpriseAccountViewSet(viewsets.ModelViewSet):
    serializer_class = EnterpriseAccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return EnterpriseAccount.objects.all()
        return EnterpriseAccount.objects.filter(members__user=user, members__is_active=True)

    def perform_create(self, serializer):
        company_name = serializer.validated_data.get("company_name", "")
        slug = slugify(company_name)
        serializer.save(primary_admin=self.request.user, slug=slug)

    @action(detail=True, methods=["get"])
    def dashboard(self, request, pk=None):
        enterprise = self.get_object()
        budgets = enterprise.budgets.filter(is_active=True)
        total_budget = sum(b.total_amount_lkr for b in budgets)
        total_spent = sum(b.spent_amount_lkr for b in budgets)
        return Response({
            "company_name": enterprise.company_name,
            "tier": enterprise.tier,
            "total_members": enterprise.members.filter(is_active=True).count(),
            "total_budget_lkr": str(total_budget),
            "total_spent_lkr": str(total_spent),
            "total_available_lkr": str(total_budget - total_spent),
            "approved_providers": enterprise.approved_providers.filter(is_active=True).count(),
        })


class EnterpriseTeamMemberViewSet(viewsets.ModelViewSet):
    serializer_class = EnterpriseTeamMemberSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return EnterpriseTeamMember.objects.all()
        return EnterpriseTeamMember.objects.filter(enterprise__members__user=user)


class EnterpriseBudgetViewSet(viewsets.ModelViewSet):
    serializer_class = EnterpriseBudgetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return EnterpriseBudget.objects.all()
        return EnterpriseBudget.objects.filter(enterprise__members__user=user)


class EnterpriseApprovedProviderViewSet(viewsets.ModelViewSet):
    serializer_class = EnterpriseApprovedProviderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return EnterpriseApprovedProvider.objects.filter(is_active=True)

    def perform_create(self, serializer):
        serializer.save(approved_by=self.request.user)


class EnterpriseCatalogViewSet(viewsets.ModelViewSet):
    serializer_class = EnterpriseCatalogItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return EnterpriseCatalogItem.objects.all()
        return EnterpriseCatalogItem.objects.filter(
            enterprise__members__user=user, is_active=True,
        )


class EnterpriseBookingApprovalViewSet(viewsets.ModelViewSet):
    serializer_class = EnterpriseBookingApprovalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return EnterpriseBookingApproval.objects.filter(requested_by=user) | \
               EnterpriseBookingApproval.objects.filter(approver=user)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        approval = self.get_object()
        approval.status = EnterpriseBookingApproval.ApprovalStatus.APPROVED
        approval.approver = request.user
        approval.approver_notes = request.data.get("notes", "")
        approval.decided_at = tz.now()
        approval.save()
        return Response(EnterpriseBookingApprovalSerializer(approval).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        approval = self.get_object()
        approval.status = "rejected"
        approval.approver = request.user
        approval.approver_notes = request.data.get("notes", "")
        approval.decided_at = tz.now()
        approval.save()
        return Response(EnterpriseBookingApprovalSerializer(approval).data)


class InternalMentorProgramViewSet(viewsets.ModelViewSet):
    serializer_class = InternalMentorProgramSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return InternalMentorProgram.objects.all()
        return InternalMentorProgram.objects.filter(enterprise__members__user=user)


class InternalMentorMatchViewSet(viewsets.ModelViewSet):
    serializer_class = InternalMentorMatchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return InternalMentorMatch.objects.filter(mentor=user) | \
               InternalMentorMatch.objects.filter(mentee=user)
