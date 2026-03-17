"""Analytics serializers."""
from rest_framework import serializers
from .models import PlatformStat, EmployerAnalytics


class PlatformStatSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformStat
        fields = "__all__"


class EmployerAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployerAnalytics
        fields = "__all__"


class DateRangeSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
