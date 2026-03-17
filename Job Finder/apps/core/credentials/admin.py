from django.contrib import admin
from .models import Credential, CredentialShare


@admin.register(Credential)
class CredentialAdmin(admin.ModelAdmin):
    list_display = ['title', 'owner', 'credential_type', 'status',
                    'issuer_name', 'issued_date', 'expiry_date']
    list_filter = ['credential_type', 'status', 'source']
    search_fields = ['title', 'issuer_name', 'owner__email']
    readonly_fields = ['verified_at']


@admin.register(CredentialShare)
class CredentialShareAdmin(admin.ModelAdmin):
    list_display = ['credential', 'shared_with', 'shared_at', 'viewed_at']
    readonly_fields = ['shared_at']
