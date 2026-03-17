"""Marketplace Billing — views."""
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BillingPlan, EmployerSubscription, Invoice, AdBudget, AdBudgetTransaction
from .serializers import (
    BillingPlanSerializer, EmployerSubscriptionSerializer,
    InvoiceSerializer, AdBudgetSerializer, AdBudgetTransactionSerializer,
)


class BillingPlansView(APIView):
    """List available billing plans."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        plans = BillingPlan.objects.filter(is_active=True)
        return Response(BillingPlanSerializer(plans, many=True).data)


class EmployerSubscriptionView(APIView):
    """Get and manage the authenticated employer's subscription."""
    permission_classes = [permissions.IsAuthenticated]

    def _get_employer(self, request):
        memberships = request.user.employer_memberships.filter(role__in=["owner", "admin"]).select_related("employer")
        if not memberships.exists():
            return None
        return memberships.first().employer

    def get(self, request):
        employer = self._get_employer(request)
        if not employer:
            return Response({"detail": "No employer account found."}, status=status.HTTP_404_NOT_FOUND)
        subscription = EmployerSubscription.objects.filter(
            employer=employer, status__in=["active", "trial"]
        ).select_related("plan").first()
        if not subscription:
            return Response({"detail": "No active subscription.", "plan_tier": "free"})
        return Response(EmployerSubscriptionSerializer(subscription).data)

    def post(self, request):
        """Subscribe to a plan."""
        employer = self._get_employer(request)
        if not employer:
            return Response({"detail": "No employer account."}, status=status.HTTP_400_BAD_REQUEST)
        plan_id = request.data.get("plan_id")
        billing_cycle = request.data.get("billing_cycle", "monthly")
        try:
            plan = BillingPlan.objects.get(pk=plan_id, is_active=True)
        except BillingPlan.DoesNotExist:
            return Response({"detail": "Plan not found."}, status=status.HTTP_400_BAD_REQUEST)
        # Cancel any existing active subscription
        EmployerSubscription.objects.filter(employer=employer, status="active").update(
            status="cancelled", cancelled_at=timezone.now()
        )
        subscription = EmployerSubscription.objects.create(
            employer=employer, plan=plan, status="active",
            billing_cycle=billing_cycle, started_at=timezone.now(),
        )
        # Update employer plan
        employer.plan = plan.tier
        employer.save(update_fields=["plan"])
        return Response(EmployerSubscriptionSerializer(subscription).data, status=status.HTTP_201_CREATED)


class InvoiceListView(APIView):
    """List invoices for the authenticated employer."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        employer = request.user.employer_memberships.filter(
            role__in=["owner", "admin"]
        ).values_list("employer", flat=True).first()
        if not employer:
            return Response([])
        invoices = Invoice.objects.filter(employer_id=employer).order_by("-created_at")[:50]
        return Response(InvoiceSerializer(invoices, many=True).data)


class AdBudgetView(APIView):
    """View and manage employer ad wallet."""
    permission_classes = [permissions.IsAuthenticated]

    def _get_employer(self, request):
        m = request.user.employer_memberships.filter(role__in=["owner", "admin"]).select_related("employer").first()
        return m.employer if m else None

    def get(self, request):
        employer = self._get_employer(request)
        if not employer:
            return Response({"detail": "No employer account."}, status=status.HTTP_404_NOT_FOUND)
        budget, _ = AdBudget.objects.get_or_create(employer=employer)
        return Response(AdBudgetSerializer(budget).data)

    def post(self, request):
        """Top up ad wallet."""
        employer = self._get_employer(request)
        if not employer:
            return Response({"detail": "No employer account."}, status=status.HTTP_400_BAD_REQUEST)
        amount = request.data.get("amount_lkr", 0)
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            return Response({"detail": "Invalid amount."}, status=status.HTTP_400_BAD_REQUEST)

        budget, _ = AdBudget.objects.get_or_create(employer=employer)
        budget.balance_lkr += amount
        budget.total_deposited_lkr += amount
        budget.save()
        AdBudgetTransaction.objects.create(
            budget=budget, tx_type="deposit", amount_lkr=amount,
            balance_after_lkr=budget.balance_lkr, description="Manual top-up",
        )
        return Response(AdBudgetSerializer(budget).data)


class AdBudgetTransactionListView(APIView):
    """List ad wallet transactions for the authenticated employer."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        employer = request.user.employer_memberships.filter(
            role__in=["owner", "admin"]
        ).values_list("employer", flat=True).first()
        if not employer:
            return Response([])
        try:
            budget = AdBudget.objects.get(employer_id=employer)
        except AdBudget.DoesNotExist:
            return Response([])
        txns = budget.transactions.all()[:100]
        return Response(AdBudgetTransactionSerializer(txns, many=True).data)
