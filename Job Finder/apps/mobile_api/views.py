"""Mobile API — views."""
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.jobs.models import JobListing
from apps.jobs.serializers import JobListSerializer
from .models import PushDeviceToken, DevicePreference
from .serializers import PushDeviceTokenSerializer, DevicePreferenceSerializer


class RegisterPushTokenView(APIView):
    """Register or update a push notification token for a device."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        token = request.data.get("token")
        platform = request.data.get("platform")
        device_id = request.data.get("device_id", "")
        if not token or not platform:
            return Response({"detail": "token and platform are required."}, status=status.HTTP_400_BAD_REQUEST)
        # Deactivate old tokens for this device
        PushDeviceToken.objects.filter(device_id=device_id, user=request.user).update(
            is_active=False, deactivated_at=timezone.now()
        )
        push_token, created = PushDeviceToken.objects.update_or_create(
            token=token,
            defaults={
                "user": request.user,
                "platform": platform,
                "device_id": device_id,
                "app_version": request.data.get("app_version", ""),
                "os_version": request.data.get("os_version", ""),
                "is_active": True,
            }
        )
        return Response(
            PushDeviceTokenSerializer(push_token).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request):
        """Deregister a push token (on logout)."""
        token = request.data.get("token")
        if not token:
            return Response({"detail": "token is required."}, status=status.HTTP_400_BAD_REQUEST)
        PushDeviceToken.objects.filter(token=token, user=request.user).update(
            is_active=False, deactivated_at=timezone.now()
        )
        return Response({"deregistered": True})


class DevicePreferenceView(APIView):
    """Get and update device-level preferences."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        device_id = request.query_params.get("device_id", "")
        prefs, _ = DevicePreference.objects.get_or_create(user=request.user, device_id=device_id)
        return Response(DevicePreferenceSerializer(prefs).data)

    def patch(self, request):
        device_id = request.data.get("device_id", "")
        prefs, _ = DevicePreference.objects.get_or_create(user=request.user, device_id=device_id)
        ser = DevicePreferenceSerializer(prefs, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class MobileJobFeedView(APIView):
    """Mobile-optimized job feed (light payload, commute-aware)."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        qs = JobListing.objects.filter(status="active").select_related(
            "employer", "district", "category"
        ).order_by("-is_featured", "-is_boosted", "-published_at")

        # Commute filter if lat/lng provided
        lat = request.query_params.get("lat")
        lng = request.query_params.get("lng")
        district_id = request.query_params.get("district")
        if district_id:
            qs = qs.filter(district_id=district_id)

        qs = qs[:20]
        return Response({
            "results": JobListSerializer(qs, many=True, context={"request": request}).data,
            "commute_filtered": bool(lat and lng),
        })
