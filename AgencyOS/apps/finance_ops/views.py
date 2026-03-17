"""Finance Ops views."""
from django.utils import timezone
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import ClientInvoice, InvoiceLineItem, CreditNote, PaymentRecord, MarginRecord
from .serializers import (
    ClientInvoiceSerializer, ClientInvoiceListSerializer,
    InvoiceLineItemSerializer, PaymentRecordSerializer,
    CreditNoteSerializer, MarginRecordSerializer,
)


def get_agency_ids(user):
    from apps.agencies.models import Agency, AgencyRecruiter
    owned = Agency.objects.filter(owner=user).values_list("id", flat=True)
    staff = AgencyRecruiter.objects.filter(user=user, is_active=True).values_list("agency_id", flat=True)
    return list(set(list(owned) + list(staff)))


def get_first_agency(user):
    from apps.agencies.models import Agency
    return Agency.objects.filter(id__in=get_agency_ids(user)).first()


class ClientInvoiceViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["invoice_number", "po_number"]
    filterset_fields = ["status", "invoice_type", "client_account"]
    ordering_fields = ["invoice_date", "due_date", "total"]

    def get_queryset(self):
        return ClientInvoice.objects.filter(
            agency_id__in=get_agency_ids(self.request.user)
        ).select_related("client_account", "created_by")

    def get_serializer_class(self):
        if self.action == "list":
            return ClientInvoiceListSerializer
        return ClientInvoiceSerializer

    def perform_create(self, serializer):
        invoice = serializer.save(
            agency=get_first_agency(self.request.user),
            created_by=self.request.user,
        )
        invoice.balance_due = invoice.total - invoice.amount_paid
        invoice.save()

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        invoice = self.get_object()
        invoice.status = ClientInvoice.Status.SENT
        invoice.sent_at = timezone.now()
        invoice.save()
        return Response({"status": "sent"})

    @action(detail=True, methods=["post"])
    def record_payment(self, request, pk=None):
        invoice = self.get_object()
        serializer = PaymentRecordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = serializer.save(invoice=invoice, recorded_by=request.user)
        invoice.amount_paid = (invoice.amount_paid or 0) + payment.amount
        invoice.balance_due = invoice.total - invoice.amount_paid
        if invoice.balance_due <= 0:
            invoice.status = ClientInvoice.Status.PAID
            invoice.paid_at = timezone.now()
        else:
            invoice.status = ClientInvoice.Status.PARTIAL
        invoice.save()
        return Response(PaymentRecordSerializer(payment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def void(self, request, pk=None):
        invoice = self.get_object()
        invoice.status = ClientInvoice.Status.VOID
        invoice.save()
        return Response({"status": "voided"})


class MarginRecordViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["record_type", "client_account", "recruiter"]
    ordering_fields = ["period_start", "gross_margin", "margin_pct"]

    def get_queryset(self):
        return MarginRecord.objects.filter(
            agency_id__in=get_agency_ids(self.request.user)
        ).select_related("client_account", "recruiter")

    def get_serializer_class(self):
        return MarginRecordSerializer

    def perform_create(self, serializer):
        serializer.save(agency=get_first_agency(self.request.user))
