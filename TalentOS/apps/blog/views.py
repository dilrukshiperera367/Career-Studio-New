"""Blog views — public read-only + admin CRUD."""

from django.utils import timezone
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from apps.blog.models import BlogCategory, BlogPost
from apps.blog.serializers import (
    BlogCategorySerializer,
    BlogPostListSerializer,
    BlogPostDetailSerializer,
    BlogPostAdminSerializer,
)


class IsAdminUser(permissions.BasePermission):
    """Only staff / company_admin users."""
    def has_permission(self, request, view):
        return request.user.is_staff or getattr(request.user, 'user_type', '') == 'company_admin'


# ===========================================================================
# Public API (no auth required)
# ===========================================================================

class PublicPostListView(generics.ListAPIView):
    """Published blog posts — public, paginated."""
    permission_classes = [AllowAny]
    serializer_class = BlogPostListSerializer

    def get_queryset(self):
        qs = BlogPost.objects.filter(status='published').select_related('category', 'author')
        cat = self.request.query_params.get('category')
        if cat:
            qs = qs.filter(category__slug=cat)
        tag = self.request.query_params.get('tag')
        if tag:
            qs = qs.filter(tags__contains=[tag])
        featured = self.request.query_params.get('featured')
        if featured == 'true':
            qs = qs.filter(featured=True)
        return qs


class PublicPostDetailView(generics.RetrieveAPIView):
    """Single published blog post by slug — public."""
    permission_classes = [AllowAny]
    serializer_class = BlogPostDetailSerializer
    lookup_field = 'slug'

    def get_queryset(self):
        return BlogPost.objects.filter(status='published').select_related('category', 'author')

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Increment view count
        BlogPost.objects.filter(pk=instance.pk).update(view_count=instance.view_count + 1)
        instance.view_count += 1
        return Response(self.get_serializer(instance).data)


class PublicCategoryListView(generics.ListAPIView):
    """Blog categories — public."""
    permission_classes = [AllowAny]
    serializer_class = BlogCategorySerializer
    queryset = BlogCategory.objects.all()


# ===========================================================================
# Admin API (auth required)
# ===========================================================================

class AdminPostListCreateView(generics.ListCreateAPIView):
    """Admin: list all posts (any status) + create new."""
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = BlogPostAdminSerializer

    def get_queryset(self):
        qs = BlogPost.objects.select_related('category', 'author')
        st = self.request.query_params.get('status')
        if st:
            qs = qs.filter(status=st)
        return qs


class AdminPostDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin: get / update / delete a post."""
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = BlogPostAdminSerializer
    queryset = BlogPost.objects.all()


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_toggle_publish(request, pk):
    """Toggle a post between draft and published."""
    try:
        post = BlogPost.objects.get(pk=pk)
    except BlogPost.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    if post.status == 'published':
        post.status = 'draft'
        post.published_at = None
    else:
        post.status = 'published'
        post.published_at = timezone.now()
    post.save(update_fields=['status', 'published_at'])

    return Response(BlogPostAdminSerializer(post).data)


class AdminCategoryListCreateView(generics.ListCreateAPIView):
    """Admin: list/create categories."""
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = BlogCategorySerializer
    queryset = BlogCategory.objects.all()


class AdminCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin: update/delete category."""
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = BlogCategorySerializer
    queryset = BlogCategory.objects.all()
