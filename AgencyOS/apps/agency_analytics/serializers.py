"""Agency Analytics serializers."""
from rest_framework import serializers
from .models import DailyKPISnapshot, RecruiterPerformance, ClientAnalytics, FunnelMetrics


class DailyKPISnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyKPISnapshot
        fields = "__all__"
        read_only_fields = ["id", "agency"]


class RecruiterPerformanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecruiterPerformance
        fields = "__all__"
        read_only_fields = ["id", "agency"]


class ClientAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientAnalytics
        fields = "__all__"
        read_only_fields = ["id", "agency"]


class FunnelMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = FunnelMetrics
        fields = "__all__"
        read_only_fields = ["id", "agency"]
