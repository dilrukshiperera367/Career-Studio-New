"""SEO Indexing — apps.py"""
from django.apps import AppConfig


class SeoIndexingConfig(AppConfig):
    name = "apps.seo_indexing"
    label = "seo_indexing"
    verbose_name = "SEO Indexing"

    def ready(self):
        import apps.seo_indexing.signals  # noqa: F401 — registers post_save hooks
