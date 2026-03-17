"""Promotions & Ads URL routing — Feature 9 & 10 routes."""
from django.urls import path
from . import views
from . import views_extra

urlpatterns = [
    # Existing
    path("campaigns/", views.PromotedJobCampaignListCreateView.as_view(), name="promo-campaigns"),
    path("campaigns/<uuid:campaign_id>/", views.PromotedJobCampaignDetailView.as_view(), name="promo-campaign-detail"),
    path("campaigns/<uuid:campaign_id>/promote-job/", views.PromoteJobView.as_view(), name="promo-promote-job"),
    path("click/", views.AdClickTrackView.as_view(), name="promo-click-track"),
    path("ad-feed/", views.PromotedJobFeedView.as_view(), name="promo-ad-feed"),

    # Feature 9 — Campaign dashboard
    path("dashboard/", views_extra.CampaignPerformanceDashboardView.as_view(), name="promo-dashboard"),

    # Feature 10 — Career site builder
    path("career-pages/", views_extra.CareerPageListCreateView.as_view(), name="career-pages-list"),
    path("career-pages/<uuid:pk>/", views_extra.CareerPageDetailView.as_view(), name="career-page-detail"),
    path("career-pages/public/<slug:slug>/", views_extra.PublicCareerPageView.as_view(), name="career-page-public"),

    # Feature 10 — Talent community
    path("talent-community/list/", views_extra.TalentCommunityListView.as_view(), name="talent-community-list"),
    path("talent-community/<slug:employer_slug>/join/", views_extra.TalentCommunitySignUpView.as_view(), name="talent-community-join"),

    # Feature 10 — Social sharing
    path("social-kit/<uuid:job_id>/", views_extra.SocialShareKitView.as_view(), name="social-kit"),

    # Feature 10 — Source attribution
    path("attribution/", views_extra.SourceAttributionAnalyticsView.as_view(), name="attribution-analytics"),
]

