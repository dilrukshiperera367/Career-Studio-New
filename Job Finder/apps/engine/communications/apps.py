from django.apps import AppConfig


class CommunicationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.engine.communications'
    label = 'communications'
    verbose_name = 'Communications Engine'
