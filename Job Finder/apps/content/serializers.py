"""Content serializers — Blog, FAQ, static pages."""
from rest_framework import serializers
from .models import BlogPost, FAQ, StaticPage


class BlogPostSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = BlogPost
        fields = [
            "id", "slug", "author", "author_name",
            "title", "title_si", "title_ta",
            "excerpt", "excerpt_si", "excerpt_ta",
            "body", "body_si", "body_ta",
            "cover_image", "category", "tags", "status",
            "published_at", "view_count",
            "meta_title", "meta_description",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "slug", "author", "view_count", "created_at", "updated_at"]

    def get_author_name(self, obj):
        if obj.author:
            return obj.author.email
        return ""


class BlogPostListSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogPost
        fields = [
            "id", "slug", "title", "title_si", "title_ta",
            "excerpt", "excerpt_si", "excerpt_ta",
            "cover_image", "category", "tags",
            "published_at", "view_count",
        ]


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = [
            "id", "category",
            "question", "question_si", "question_ta",
            "answer", "answer_si", "answer_ta",
            "sort_order", "is_published",
        ]


class StaticPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaticPage
        fields = [
            "slug", "title", "title_si", "title_ta",
            "body", "body_si", "body_ta", "is_published", "updated_at",
        ]
