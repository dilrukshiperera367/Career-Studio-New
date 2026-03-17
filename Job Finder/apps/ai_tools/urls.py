"""AI Tools URL routing — Feature 15: AI & Personalization."""
from django.urls import path
from . import views
from . import views_extra

urlpatterns = [
    # Existing
    path("cover-letters/", views.CoverLetterListCreateView.as_view(), name="cover-letter-list"),
    path("cover-letters/<uuid:pk>/", views.CoverLetterDetailView.as_view(), name="cover-letter-detail"),
    path("linkedin/", views.LinkedInAnalysisListCreateView.as_view(), name="linkedin-analysis-list"),
    path("linkedin/<uuid:pk>/", views.LinkedInAnalysisDetailView.as_view(), name="linkedin-analysis-detail"),
    path("interview-prep/", views.InterviewSessionListCreateView.as_view(), name="interview-session-list"),
    path("interview-prep/<uuid:pk>/", views.InterviewSessionDetailView.as_view(), name="interview-session-detail"),
    path("interview-prep/<uuid:session_id>/answers/", views.InterviewAnswerCreateView.as_view(), name="interview-answer-create"),
    path("mentors/", views.MentorListView.as_view(), name="mentor-list"),
    path("mentors/<uuid:pk>/", views.MentorDetailView.as_view(), name="mentor-detail"),
    path("mentorship-requests/", views.MentorshipRequestCreateView.as_view(), name="mentorship-request-create"),
    path("mentorship-requests/mine/", views.MentorshipRequestListView.as_view(), name="mentorship-request-list"),
    path("networking-drafts/", views.NetworkingDraftListCreateView.as_view(), name="networking-draft-list"),
    path("networking-drafts/<uuid:pk>/", views.NetworkingDraftDetailView.as_view(), name="networking-draft-detail"),
    path("brand-score/", views.BrandScoreView.as_view(), name="brand-score"),
    path("career-roadmap/", views.CareerRoadmapListCreateView.as_view(), name="career-roadmap-list"),
    path("career-roadmap/<uuid:pk>/", views.CareerRoadmapDetailView.as_view(), name="career-roadmap-detail"),

    # Feature 15 — Title & Salary AI
    path("normalize-title/", views_extra.TitleNormalizationView.as_view(), name="ai-normalize-title"),
    path("salary-inference/", views_extra.SalaryInferenceView.as_view(), name="ai-salary-inference"),

    # Feature 15 — Personalization
    path("personalized-feed/", views_extra.PersonalizedJobRankingView.as_view(), name="ai-personalized-feed"),
    path("missing-skills/", views_extra.MissingSkillsView.as_view(), name="ai-missing-skills"),

    # Feature 15 — Job Insights
    path("job-summary/<uuid:job_id>/", views_extra.JobSummaryCardView.as_view(), name="ai-job-summary"),
    path("scam-risk/<uuid:job_id>/", views_extra.JobScamRiskFlagView.as_view(), name="ai-scam-risk"),

    # Feature 15 — Application Intelligence
    path("success-likelihood/", views_extra.ApplicationSuccessLikelihoodView.as_view(), name="ai-success-likelihood"),
    path("reactivation-prompts/", views_extra.SeekerReactivationPromptsView.as_view(), name="ai-reactivation"),

    # Feature 15 — Search Intelligence
    path("search-rewrite/", views_extra.SearchRewriteSuggestionsView.as_view(), name="ai-search-rewrite"),

    # Feature 15 — Assistants
    path("apply-assistant/", views_extra.ApplyAssistantView.as_view(), name="ai-apply-assistant"),
    path("optimize-job-post/", views_extra.JobPostOptimizerView.as_view(), name="ai-optimize-job-post"),
]
