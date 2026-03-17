"""URL patterns for the taxonomy app."""

from django.urls import path
from . import views

urlpatterns = [
    path("skills/", views.SkillTaxonomyListView.as_view(), name="skill-list"),
    path("skills/resolve/", views.SkillAliasResolveView.as_view(), name="skill-resolve"),
    path("skills/categories/", views.SkillCategoryListView.as_view(), name="skill-categories"),
    path("titles/normalize/", views.TitleNormalizeView.as_view(), name="title-normalize"),
    path("locations/normalize/", views.LocationNormalizeView.as_view(), name="location-normalize"),
]
