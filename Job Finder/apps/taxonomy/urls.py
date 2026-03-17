"""Taxonomy URL routing — provinces, districts, categories, skills, etc."""
from django.urls import path
from . import views

urlpatterns = [
    path("provinces/", views.ProvinceListView.as_view(), name="province-list"),
    path("districts/", views.DistrictListView.as_view(), name="district-list"),
    path("categories/", views.JobCategoryListView.as_view(), name="category-list"),
    path("categories/<slug:slug>/", views.JobCategoryDetailView.as_view(), name="category-detail"),
    path("subcategories/", views.JobSubCategoryListView.as_view(), name="subcategory-list"),
    path("industries/", views.IndustryListView.as_view(), name="industry-list"),
    path("skills/", views.SkillListView.as_view(), name="skill-list"),
    path("education-levels/", views.EducationLevelListView.as_view(), name="education-level-list"),
]
