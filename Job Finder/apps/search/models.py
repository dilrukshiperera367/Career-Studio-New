"""Search app — OpenSearch index management, search utilities.
Actual indexing/search logic uses opensearch-py; models here are minimal.
"""
from django.db import models


class SearchIndex(models.Model):
    """Track OpenSearch index metadata and rebuild state."""
    index_name = models.CharField(max_length=50, primary_key=True)
    doc_count = models.IntegerField(default=0)
    last_rebuilt_at = models.DateTimeField(null=True, blank=True)
    last_updated_at = models.DateTimeField(null=True, blank=True)
    is_rebuilding = models.BooleanField(default=False)
    settings_json = models.JSONField(default=dict, blank=True)
    mapping_json = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "jf_search_indexes"

    def __str__(self):
        return self.index_name
