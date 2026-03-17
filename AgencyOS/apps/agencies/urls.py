from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register("agencies", views.AgencyViewSet, basename="agency")
router.register("clients", views.AgencyClientViewSet, basename="agency-client")
router.register("recruiters", views.AgencyRecruiterViewSet, basename="agency-recruiter")
router.register("job-orders", views.AgencyJobOrderViewSet, basename="agency-job-order")
router.register("submissions", views.AgencySubmissionViewSet, basename="agency-submission")
router.register("placements", views.AgencyPlacementViewSet, basename="agency-placement")
router.register("contractors", views.AgencyContractorViewSet, basename="agency-contractor")
router.register("talent-pools", views.TalentPoolViewSet, basename="talent-pool")

urlpatterns = router.urls
