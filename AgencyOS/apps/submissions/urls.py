from rest_framework.routers import DefaultRouter
from .views import CandidateProfileViewSet, SubmissionViewSet, ShortlistViewSet

router = DefaultRouter()
router.register("candidates", CandidateProfileViewSet, basename="candidate")
router.register("submissions", SubmissionViewSet, basename="submission")
router.register("shortlists", ShortlistViewSet, basename="shortlist")

urlpatterns = router.urls
