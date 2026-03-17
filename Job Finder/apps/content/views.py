"""Content views — Blog, FAQ, static pages."""
from rest_framework import generics, permissions

from .models import BlogPost, FAQ, StaticPage
from .serializers import (
    BlogPostSerializer, BlogPostListSerializer,
    FAQSerializer, StaticPageSerializer,
)


class BlogPostListView(generics.ListAPIView):
    serializer_class = BlogPostListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = BlogPost.objects.filter(status="published").order_by("-published_at")
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        return qs


class BlogPostDetailView(generics.RetrieveAPIView):
    serializer_class = BlogPostSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"
    queryset = BlogPost.objects.filter(status="published")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.view_count += 1
        instance.save(update_fields=["view_count"])
        return super().retrieve(request, *args, **kwargs)


class FAQListView(generics.ListAPIView):
    serializer_class = FAQSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        qs = FAQ.objects.filter(is_published=True)
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        return qs.order_by("category", "sort_order")


class StaticPageDetailView(generics.RetrieveAPIView):
    serializer_class = StaticPageSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"
    queryset = StaticPage.objects.filter(is_published=True)
