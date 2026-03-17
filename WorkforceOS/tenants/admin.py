"""Admin registration for the tenants app."""

from django.contrib import admin
from .models import Tenant, TenantFeature, FeatureFlag
from .enterprise import SSOConfiguration, SCIMConfiguration, SCIMSyncLog, Subscription, Invoice, BillingHistory, TranslationKey


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'plan', 'status', 'max_employees', 'trial_ends_at', 'created_at')
    list_filter = ('plan', 'status')
    search_fields = ('name', 'slug')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)


@admin.register(TenantFeature)
class TenantFeatureAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'module', 'tier', 'enabled', 'enabled_at', 'trial_ends_at')
    list_filter = ('module', 'tier', 'enabled')
    search_fields = ('tenant__name', 'tenant__slug', 'module')
    readonly_fields = ('id', 'enabled_at')


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = ('flag_key', 'tenant', 'enabled', 'rollout_pct')
    list_filter = ('enabled', 'tenant')
    search_fields = ('flag_key', 'tenant__name')
    readonly_fields = ('id',)
    ordering = ('flag_key',)


@admin.register(SSOConfiguration)
class SSOConfigurationAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'provider', 'is_enabled', 'force_sso', 'auto_provision',
                    'default_role', 'created_at')
    list_filter = ('provider', 'is_enabled', 'force_sso', 'auto_provision')
    search_fields = ('tenant__name', 'tenant__slug', 'sp_entity_id')
    readonly_fields = ('id', 'created_at', 'updated_at', 'idp_certificate')


@admin.register(SCIMConfiguration)
class SCIMConfigurationAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'is_enabled', 'sync_groups', 'sync_users', 'last_sync_at', 'sync_status')
    list_filter = ('is_enabled', 'sync_groups', 'sync_users')
    search_fields = ('tenant__name', 'tenant__slug', 'base_url')
    readonly_fields = ('id', 'last_sync_at', 'bearer_token')


@admin.register(SCIMSyncLog)
class SCIMSyncLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'tenant', 'operation', 'resource_type', 'resource_id', 'status', 'created_at')
    list_filter = ('operation', 'resource_type', 'status', 'tenant')
    search_fields = ('resource_id', 'tenant__name')
    readonly_fields = ('id', 'created_at', 'details')
    date_hierarchy = 'created_at'


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'plan', 'status', 'billing_cycle', 'price_per_user',
                    'max_users', 'current_users', 'trial_ends_at', 'current_period_end', 'created_at')
    list_filter = ('plan', 'status', 'billing_cycle')
    search_fields = ('tenant__name', 'tenant__slug', 'stripe_customer_id', 'stripe_subscription_id')
    readonly_fields = ('id', 'created_at')


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'tenant', 'subscription', 'period_start', 'period_end',
                    'amount', 'currency', 'status', 'paid_at', 'created_at')
    list_filter = ('status', 'currency', 'tenant')
    search_fields = ('invoice_number', 'tenant__name', 'stripe_invoice_id')
    readonly_fields = ('id', 'created_at', 'paid_at')
    date_hierarchy = 'created_at'


@admin.register(BillingHistory)
class BillingHistoryAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'event_type', 'amount', 'currency', 'plan_before', 'plan_after', 'created_at')
    list_filter = ('event_type', 'currency', 'tenant')
    search_fields = ('tenant__name', 'stripe_event_id', 'event_type')
    readonly_fields = ('id', 'created_at')
    date_hierarchy = 'created_at'


@admin.register(TranslationKey)
class TranslationKeyAdmin(admin.ModelAdmin):
    list_display = ('key', 'language', 'module', 'value')
    list_filter = ('language', 'module')
    search_fields = ('key', 'value', 'module')
    readonly_fields = ('id',)
    ordering = ('key', 'language')
