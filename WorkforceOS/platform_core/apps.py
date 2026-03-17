from django.apps import AppConfig


class PlatformCoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'platform_core'

    def ready(self):
        import platform_core.workflow_signals  # noqa: F401 — registers signal handlers
