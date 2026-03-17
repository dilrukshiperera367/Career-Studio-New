"""Finance Ops serializers."""
from rest_framework import serializers
from .models import ClientInvoice, InvoiceLineItem, CreditNote, PaymentRecord, MarginRecord


class InvoiceLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLineItem
        fields = "__all__"
        read_only_fields = ["id", "amount"]


class PaymentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentRecord
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class CreditNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditNote
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class ClientInvoiceSerializer(serializers.ModelSerializer):
    line_items = InvoiceLineItemSerializer(many=True, read_only=True)
    payments = PaymentRecordSerializer(many=True, read_only=True)
    credit_notes = CreditNoteSerializer(many=True, read_only=True)

    class Meta:
        model = ClientInvoice
        fields = "__all__"
        read_only_fields = ["id", "agency", "balance_due", "created_at", "updated_at"]


class ClientInvoiceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientInvoice
        fields = [
            "id", "invoice_number", "invoice_type", "status", "client_account",
            "invoice_date", "due_date", "total", "amount_paid", "balance_due", "currency",
        ]


class MarginRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarginRecord
        fields = "__all__"
        read_only_fields = ["id", "gross_margin", "margin_pct", "created_at"]
