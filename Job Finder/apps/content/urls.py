"""Content URL routing — blog, FAQ, static pages."""
from django.urls import path
from . import views

urlpatterns = [
    path("blog/", views.BlogPostListView.as_view(), name="blog-list"),
    path("blog/<slug:slug>/", views.BlogPostDetailView.as_view(), name="blog-detail"),
    path("faq/", views.FAQListView.as_view(), name="faq-list"),
    path("pages/<slug:slug>/", views.StaticPageDetailView.as_view(), name="static-page-detail"),
]
