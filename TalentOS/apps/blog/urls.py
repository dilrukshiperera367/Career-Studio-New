"""Blog URL configuration."""

from django.urls import path
from apps.blog import views

urlpatterns = [
    # Public
    path('posts/', views.PublicPostListView.as_view(), name='blog-posts'),
    path('posts/<slug:slug>/', views.PublicPostDetailView.as_view(), name='blog-post-detail'),
    path('categories/', views.PublicCategoryListView.as_view(), name='blog-categories'),

    # Admin
    path('admin/posts/', views.AdminPostListCreateView.as_view(), name='blog-admin-posts'),
    path('admin/posts/<uuid:pk>/', views.AdminPostDetailView.as_view(), name='blog-admin-post-detail'),
    path('admin/posts/<uuid:pk>/toggle/', views.admin_toggle_publish, name='blog-admin-toggle'),
    path('admin/categories/', views.AdminCategoryListCreateView.as_view(), name='blog-admin-categories'),
    path('admin/categories/<uuid:pk>/', views.AdminCategoryDetailView.as_view(), name='blog-admin-category-detail'),
]
