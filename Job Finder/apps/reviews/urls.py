"""Reviews URL routing — Feature 12 routes."""
from django.urls import path
from . import views
from . import views_extra

urlpatterns = [
    # Existing
    path("employer/<uuid:employer_id>/", views.CompanyReviewListView.as_view(), name="review-list"),
    path("employer/<uuid:employer_id>/stats/", views.CompanyReviewStatsView.as_view(), name="review-stats"),
    path("create/", views.CompanyReviewCreateView.as_view(), name="review-create"),
    path("<uuid:pk>/helpful/", views.ReviewHelpfulToggleView.as_view(), name="review-helpful"),
    path("<uuid:pk>/respond/", views.EmployerReviewResponseView.as_view(), name="review-respond"),
    path("my/", views.MyReviewView.as_view(), name="my-review"),

    # Feature 12 — Review Hub
    path("hub/<slug:slug>/", views_extra.CompanyReviewHubView.as_view(), name="review-hub"),

    # Feature 12 — Review Types
    path("interview/<slug:slug>/", views_extra.InterviewReviewListCreateView.as_view(), name="review-interview"),
    path("benefits/<slug:slug>/", views_extra.BenefitsReviewListCreateView.as_view(), name="review-benefits"),
    path("salary/<slug:slug>/", views_extra.SalaryReviewListCreateView.as_view(), name="review-salary"),

    # Feature 12 — Q&A, Moderation, Verification
    path("qna/<slug:slug>/", views_extra.CompanyQnAReviewView.as_view(), name="review-qna"),
    path("moderation-stats/", views_extra.ModerationTransparencyView.as_view(), name="review-moderation-stats"),
    path("<uuid:review_id>/authenticity/", views_extra.ReviewerVerificationLevelView.as_view(), name="review-authenticity"),

    # Feature 12 — Employer Response Analytics
    path("response-analytics/", views_extra.EmployerResponseAnalyticsView.as_view(), name="review-response-analytics"),
]
