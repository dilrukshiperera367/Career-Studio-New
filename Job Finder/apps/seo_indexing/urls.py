"""SEO Indexing — URLs."""
from django.urls import path
from . import views

urlpatterns = [
    path("structured-data/job/<slug:slug>/", views.JobStructuredDataView.as_view(), name="seo-job-ld"),
    path("structured-data/company/<slug:slug>/", views.CompanyStructuredDataView.as_view(), name="seo-company-ld"),
    path("sitemap-health/", views.SitemapHealthView.as_view(), name="seo-sitemap-health"),
    path("indexing-logs/", views.IndexingAPILogListView.as_view(), name="seo-indexing-logs"),
    path("validate/<slug:slug>/", views.StructuredDataValidationView.as_view(), name="seo-validate"),
    path("facet/<str:facet_type>/<slug:slug>/", views.FacetedSEODataView.as_view(), name="seo-facet"),
    path("internal-links/", views.InternalLinkGraphView.as_view(), name="seo-internal-links"),
]
