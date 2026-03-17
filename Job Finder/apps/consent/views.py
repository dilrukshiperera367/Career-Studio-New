from rest_framework import viewsets, permissions
from .models import ConsentRecord, DataExportRequest, DataDeletionRequest, PrivacySetting
from .serializers import (
    ConsentRecordSerializer, DataExportRequestSerializer,
    DataDeletionRequestSerializer, PrivacySettingSerializer,
)


class ConsentRecordViewSet(viewsets.ModelViewSet):
    serializer_class = ConsentRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["consent_type", "is_granted"]

    def get_queryset(self):
        return ConsentRecord.objects.filter(user=self.request.user)


class DataExportRequestViewSet(viewsets.ModelViewSet):
    serializer_class = DataExportRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["status"]

    def get_queryset(self):
        return DataExportRequest.objects.filter(user=self.request.user)


class DataDeletionRequestViewSet(viewsets.ModelViewSet):
    serializer_class = DataDeletionRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["status", "scope"]

    def get_queryset(self):
        return DataDeletionRequest.objects.filter(user=self.request.user)


class PrivacySettingViewSet(viewsets.ModelViewSet):
    serializer_class = PrivacySettingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PrivacySetting.objects.filter(user=self.request.user)
