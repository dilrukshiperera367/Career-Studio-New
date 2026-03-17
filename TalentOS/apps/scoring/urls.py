from django.urls import path
from apps.scoring.views import (
    BatchListCreateView, BatchDetailView, BatchResultsView, batch_export_csv,
    CandidateScoreView, CandidateScoreListView, CandidateScoreDetailView,
    CandidateResumeListCreateView,
)
from apps.scoring.scorecard_views import TeamScorecardView

urlpatterns = [
    # Team scorecard aggregation
    path('scoring/team-scorecard/', TeamScorecardView.as_view(), name='team-scorecard'),

    # Company — Batch scoring
    path("batches/", BatchListCreateView.as_view(), name="batch-list-create"),
    path("batches/<uuid:pk>/", BatchDetailView.as_view(), name="batch-detail"),
    path("batches/<uuid:pk>/results/", BatchResultsView.as_view(), name="batch-results"),
    path("batches/<uuid:pk>/export/", batch_export_csv, name="batch-export"),

    # Candidate — Personal scoring
    path("my/score/", CandidateScoreView.as_view(), name="candidate-score"),
    path("my/scores/", CandidateScoreListView.as_view(), name="candidate-score-list"),
    path("my/scores/<uuid:pk>/", CandidateScoreDetailView.as_view(), name="candidate-score-detail"),
    path("my/resumes/", CandidateResumeListCreateView.as_view(), name="candidate-resume-list"),
]
