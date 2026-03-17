from django.apps import AppConfig


class VerificationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.trust.verification'
    label = 'verification'
    verbose_name = 'Verification & Trust'
