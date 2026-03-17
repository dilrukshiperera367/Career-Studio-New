"""Search admin registrations."""
from django.contrib import admin
from .models import SearchIndex


@admin.register(SearchIndex)
class SearchIndexAdmin(admin.ModelAdmin):
    list_display = ("index_name", "last_rebuilt_at", "doc_count")
