"""Content admin registrations."""
from django.contrib import admin
from .models import BlogPost, FAQ, StaticPage


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "author", "status", "published_at", "view_count")
    list_filter = ("status", "category")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "published_at"
    raw_id_fields = ("author",)


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "category", "sort_order", "is_published")
    list_filter = ("category", "is_published")


@admin.register(StaticPage)
class StaticPageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_published", "updated_at")
    list_filter = ("is_published",)
    prepopulated_fields = {"slug": ("title",)}
