from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone as tz
from .models import Booking, RecurringPlan, WaitlistEntry
from .serializers import (
    BookingSerializer, BookingListSerializer,
    RecurringPlanSerializer, WaitlistEntrySerializer,
)


class BookingViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["status", "delivery_mode", "booking_mode", "provider"]
    ordering_fields = ["created_at", "start_time", "price_lkr"]
    search_fields = ["reference", "buyer_notes"]

    def get_serializer_class(self):
        if self.action == "list":
            return BookingListSerializer
        return BookingSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Booking.objects.select_related("buyer", "provider", "service")
        if user.role == "admin":
            return qs
        # Providers see their incoming bookings; buyers see their own
        return qs.filter(buyer=user) | qs.filter(provider__user=user)

    def perform_create(self, serializer):
        serializer.save(buyer=self.request.user)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        """Provider confirms a request-to-book."""
        booking = self.get_object()
        if booking.provider.user != request.user:
            return Response({"detail": "Only the provider can confirm."}, status=403)
        booking.status = Booking.Status.CONFIRMED
        booking.status_changed_at = tz.now()
        booking.save(update_fields=["status", "status_changed_at"])
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel a booking (buyer or provider)."""
        booking = self.get_object()
        reason = request.data.get("reason", "")
        if booking.buyer == request.user:
            booking.status = Booking.Status.CANCELLED_BUYER
        elif booking.provider.user == request.user:
            booking.status = Booking.Status.CANCELLED_PROVIDER
        else:
            return Response({"detail": "Not authorised."}, status=403)
        booking.cancellation_reason = reason
        booking.status_changed_at = tz.now()
        booking.save(update_fields=["status", "cancellation_reason", "status_changed_at"])
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=["post"])
    def reschedule(self, request, pk=None):
        """Reschedule a confirmed booking to a new time."""
        booking = self.get_object()
        new_start = request.data.get("start_time")
        new_end = request.data.get("end_time")
        if not new_start:
            return Response({"detail": "start_time is required."}, status=400)
        booking.start_time = new_start
        if new_end:
            booking.end_time = new_end
        booking.save(update_fields=["start_time", "end_time", "updated_at"])
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Mark booking as completed."""
        booking = self.get_object()
        booking.status = Booking.Status.COMPLETED
        booking.status_changed_at = tz.now()
        booking.save(update_fields=["status", "status_changed_at"])
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=["post"])
    def mark_no_show(self, request, pk=None):
        """Mark no-show (provider or admin)."""
        booking = self.get_object()
        party = request.data.get("party", "buyer")  # buyer | provider
        booking.status = Booking.Status.NO_SHOW_BUYER if party == "buyer" else Booking.Status.NO_SHOW_PROVIDER
        booking.status_changed_at = tz.now()
        booking.save(update_fields=["status", "status_changed_at"])
        return Response(BookingSerializer(booking).data)

    @action(detail=False, methods=["get"])
    def upcoming(self, request):
        """Buyer/provider upcoming sessions."""
        user = request.user
        now = tz.now()
        qs = Booking.objects.filter(
            start_time__gte=now,
            status=Booking.Status.CONFIRMED,
        ).filter(buyer=user) | Booking.objects.filter(
            start_time__gte=now,
            status=Booking.Status.CONFIRMED,
            provider__user=user,
        )
        serializer = BookingListSerializer(qs.order_by("start_time")[:20], many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def history(self, request):
        """Past completed sessions for buyer or provider."""
        user = request.user
        qs = Booking.objects.filter(
            status=Booking.Status.COMPLETED,
        ).filter(buyer=user) | Booking.objects.filter(
            status=Booking.Status.COMPLETED,
            provider__user=user,
        )
        serializer = BookingListSerializer(qs.order_by("-start_time")[:50], many=True)
        return Response(serializer.data)


class RecurringPlanViewSet(viewsets.ModelViewSet):
    serializer_class = RecurringPlanSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return RecurringPlan.objects.filter(buyer=user) | RecurringPlan.objects.filter(provider__user=user)

    def perform_create(self, serializer):
        serializer.save(buyer=self.request.user)


class WaitlistViewSet(viewsets.ModelViewSet):
    serializer_class = WaitlistEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WaitlistEntry.objects.filter(buyer=self.request.user)

    def perform_create(self, serializer):
        serializer.save(buyer=self.request.user)
