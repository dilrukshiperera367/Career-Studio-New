"""Company Intelligence URL routing — Feature 7 routes."""
from django.urls import path
from . import views_extra

urlpatterns = [
    # Full company page (public)
    path("<slug:slug>/", views_extra.CompanyPageView.as_view(), name="ci-company-page"),
    path("<slug:slug>/offices/", views_extra.CompanyOfficeListCreateView.as_view(), name="ci-offices"),
    path("<slug:slug>/benefits/", views_extra.CompanyBenefitsView.as_view(), name="ci-benefits"),
    path("<slug:slug>/qna/", views_extra.CompanyQnAListCreateView.as_view(), name="ci-qna"),
    path("<slug:slug>/qna/<uuid:pk>/helpful/", views_extra.CompanyQnAHelpfulView.as_view(), name="ci-qna-helpful"),
    path("<slug:slug>/hiring-activity/", views_extra.HiringActivityView.as_view(), name="ci-hiring-activity"),
    path("<slug:slug>/scorecard/", views_extra.WorkplaceScorecardView.as_view(), name="ci-scorecard"),
    path("<slug:slug>/follow/", views_extra.CompanyFollowView.as_view(), name="ci-follow"),
    path("<slug:slug>/similar/", views_extra.SimilarCompaniesView.as_view(), name="ci-similar"),
    path("compare/", views_extra.CompanyCompareView.as_view(), name="ci-compare"),
]
