"""SEO Indexing — serializers."""
from rest_framework import serializers
from .models import SitemapEntry, IndexingAPILog, StructuredDataValidation, CrawlHealthSnapshot


class SitemapEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = SitemapEntry
        fields = ["id", "page_type", "slug", "url", "last_modified", "change_frequency", "priority",
                  "is_indexable", "is_expired"]


class IndexingAPILogSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndexingAPILog
        fields = ["id", "url", "action", "http_status", "success", "error_message", "created_at"]


class StructuredDataValidationSerializer(serializers.ModelSerializer):
    class Meta:
        model = StructuredDataValidation
        fields = ["id", "page_type", "slug", "status", "warnings", "errors", "validated_at"]


class CrawlHealthSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrawlHealthSnapshot
        fields = "__all__"
