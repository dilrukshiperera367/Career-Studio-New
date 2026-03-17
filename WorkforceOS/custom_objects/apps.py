from django.apps import AppConfig

class CustomObjectsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'custom_objects'
    verbose_name = 'Custom Objects'
