from django.contrib import admin
from apps.blog.models import BlogCategory, BlogPost


@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'category', 'featured', 'published_at', 'view_count']
    list_filter = ['status', 'featured', 'category']
    search_fields = ['title', 'content']
    prepopulated_fields = {'slug': ('title',)}
