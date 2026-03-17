from rest_framework import serializers
from .models import Payment, Payout, PayoutLineItem, PromoCode, Wallet, WalletTransaction, Invoice, RefundRequest


class PaymentSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    payment_type_label = serializers.CharField(source="get_payment_type_display", read_only=True)

    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = [
            "id", "reference", "status", "completed_at", "failed_at",
            "platform_commission_lkr", "provider_earnings_lkr",
            "risk_score", "is_flagged", "created_at", "updated_at",
        ]


class PayoutLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayoutLineItem
        fields = "__all__"
        read_only_fields = ["id"]


class PayoutSerializer(serializers.ModelSerializer):
    line_items = PayoutLineItemSerializer(many=True, read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Payout
        fields = "__all__"
        read_only_fields = ["id", "reference", "created_at"]


class PromoCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoCode
        fields = "__all__"
        read_only_fields = ["id", "total_used", "created_at"]


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = "__all__"
        read_only_fields = ["id", "balance_lkr", "created_at", "updated_at"]


class WalletTransactionSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source="get_transaction_type_display", read_only=True)

    class Meta:
        model = WalletTransaction
        fields = "__all__"
        read_only_fields = ["id", "balance_after_lkr", "created_at"]


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = "__all__"
        read_only_fields = ["id", "invoice_number", "issued_at"]


class RefundRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefundRequest
        fields = "__all__"
        read_only_fields = [
            "id", "status", "approved_amount_lkr", "admin_notes",
            "reviewed_by", "reviewed_at", "processed_at", "created_at",
        ]
