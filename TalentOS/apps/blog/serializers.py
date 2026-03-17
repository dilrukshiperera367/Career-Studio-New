"""Blog serializers — public read-only and admin full CRUD."""

from rest_framework import serializers
from apps.blog.models import BlogCategory, BlogPost


class BlogCategorySerializer(serializers.ModelSerializer):
    post_count = serializers.SerializerMethodField()

    class Meta:
        model = BlogCategory
        fields = ['id', 'name', 'slug', 'post_count']

    def get_post_count(self, obj):
        return obj.posts.filter(status='published').count()


class BlogPostListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', default='')
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = BlogPost
        fields = [
            'id', 'title', 'slug', 'excerpt', 'cover_image_url',
            'category_name', 'author_name', 'tags', 'status',
            'featured', 'published_at', 'created_at', 'view_count',
        ]

    def get_author_name(self, obj):
        if obj.author:
            return f'{obj.author.first_name} {obj.author.last_name}'.strip() or obj.author.email
        return 'ATS Team'


class BlogPostDetailSerializer(serializers.ModelSerializer):
    category = BlogCategorySerializer(read_only=True)
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = BlogPost
        fields = [
            'id', 'title', 'slug', 'excerpt', 'content', 'cover_image_url',
            'category', 'author_name', 'tags', 'status', 'featured',
            'meta_title', 'meta_description',
            'published_at', 'created_at', 'updated_at', 'view_count',
        ]

    def get_author_name(self, obj):
        if obj.author:
            return f'{obj.author.first_name} {obj.author.last_name}'.strip() or obj.author.email
        return 'ATS Team'


class BlogPostAdminSerializer(serializers.ModelSerializer):
    """Admin serializer — allows create/update of all fields."""
    category_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = BlogPost
        fields = [
            'id', 'title', 'slug', 'excerpt', 'content', 'cover_image_url',
            'category', 'category_id', 'author', 'tags', 'status', 'featured',
            'meta_title', 'meta_description',
            'published_at', 'created_at', 'updated_at', 'view_count',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'view_count', 'author', 'category']

    def create(self, validated_data):
        cat_id = validated_data.pop('category_id', None)
        user = self.context['request'].user
        post = BlogPost.objects.create(author=user, **validated_data)
        if cat_id:
            post.category_id = cat_id
            post.save(update_fields=['category_id'])
        return post

    def update(self, instance, validated_data):
        cat_id = validated_data.pop('category_id', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if cat_id is not None:
            instance.category_id = cat_id
        instance.save()
        return instance
