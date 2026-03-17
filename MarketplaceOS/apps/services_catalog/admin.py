from django.contrib import admin
from .models import ServiceCategory, Service, ServicePackage, ServiceAddOn, ServiceSubscriptionPlan


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "parent", "is_active", "sort_order"]
    list_filter = ["is_active"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ["title", "provider", "service_type", "delivery_mode", "status", "visibility",
                    "base_price_lkr", "is_featured"]
    list_filter = ["status", "visibility", "service_type", "delivery_mode", "is_featured"]
    search_fields = ["title", "provider__user__email"]
    list_editable = ["status", "is_featured"]
    prepopulated_fields = {"slug": ("title",)}


@admin.register(ServicePackage)
class ServicePackageAdmin(admin.ModelAdmin):
    list_display = ["name", "service", "session_count", "price_lkr", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["service__title"]


@admin.register(ServiceAddOn)
class ServiceAddOnAdmin(admin.ModelAdmin):
    list_display = ["name", "service", "price_lkr", "is_active"]
    list_filter = ["is_active"]


@admin.register(ServiceSubscriptionPlan)
class ServiceSubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ["name", "service", "interval", "price_lkr", "is_active"]
    list_filter = ["interval", "is_active"]
