from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone as tz
from .models import Payment, Payout, PromoCode, Wallet, WalletTransaction, Invoice, RefundRequest
from .serializers import (
    PaymentSerializer, PayoutSerializer, PromoCodeSerializer,
    WalletSerializer, WalletTransactionSerializer, InvoiceSerializer,
    RefundRequestSerializer,
)


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["status", "payment_type", "payment_method"]
    ordering_fields = ["created_at", "net_amount_lkr"]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return Payment.objects.all()
        return Payment.objects.filter(payer=user)

    @action(detail=False, methods=["post"])
    def validate_promo(self, request):
        """Validate a promo code without using it."""
        code = request.data.get("code", "").upper().strip()
        try:
            promo = PromoCode.objects.get(code=code, is_active=True)
        except PromoCode.DoesNotExist:
            return Response({"valid": False, "detail": "Promo code not found or expired."})
        now = tz.now()
        if promo.valid_to and promo.valid_to < now:
            return Response({"valid": False, "detail": "Promo code has expired."})
        if promo.max_uses and promo.total_used >= promo.max_uses:
            return Response({"valid": False, "detail": "Promo code has reached its usage limit."})
        return Response({
            "valid": True,
            "discount_type": promo.discount_type,
            "discount_value": str(promo.discount_value),
        })


class PayoutViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PayoutSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering_fields = ["created_at", "net_amount_lkr"]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return Payout.objects.all()
        return Payout.objects.filter(provider__user=user)


class PromoCodeViewSet(viewsets.ModelViewSet):
    serializer_class = PromoCodeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return PromoCode.objects.all()
        return PromoCode.objects.filter(is_active=True, provider__user=user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class WalletViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Wallet.objects.filter(user=self.request.user)

    @action(detail=False, methods=["get"])
    def my_wallet(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        return Response(WalletSerializer(wallet).data)

    @action(detail=False, methods=["get"])
    def transactions(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        txns = WalletTransaction.objects.filter(wallet=wallet).order_by("-created_at")[:50]
        return Response(WalletTransactionSerializer(txns, many=True).data)


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering_fields = ["issued_at", "total_lkr"]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return Invoice.objects.all()
        return Invoice.objects.filter(issued_to=user)


class RefundRequestViewSet(viewsets.ModelViewSet):
    serializer_class = RefundRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return RefundRequest.objects.all()
        return RefundRequest.objects.filter(requested_by=user)

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Admin approves a refund."""
        refund = self.get_object()
        approved_amount = request.data.get("approved_amount_lkr", refund.requested_amount_lkr)
        refund.status = RefundRequest.RefundStatus.APPROVED
        refund.approved_amount_lkr = approved_amount
        refund.admin_notes = request.data.get("admin_notes", "")
        refund.reviewed_by = request.user
        refund.reviewed_at = tz.now()
        refund.save()
        return Response(RefundRequestSerializer(refund).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Admin rejects a refund."""
        refund = self.get_object()
        refund.status = RefundRequest.RefundStatus.REJECTED
        refund.admin_notes = request.data.get("admin_notes", "")
        refund.reviewed_by = request.user
        refund.reviewed_at = tz.now()
        refund.save()
        return Response(RefundRequestSerializer(refund).data)
