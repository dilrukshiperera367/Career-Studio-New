"""Retention Growth — URLs."""
from django.urls import path
from . import views

urlpatterns = [
    path("new-since-last-visit/", views.NewSinceLastVisitView.as_view(), name="ret-new-since-visit"),
    path("digest-preview/", views.DigestPreviewView.as_view(), name="ret-digest-preview"),
]
