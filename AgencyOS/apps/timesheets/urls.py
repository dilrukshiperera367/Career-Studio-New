from rest_framework.routers import DefaultRouter
from .views import TimesheetPeriodViewSet, TimesheetViewSet, ExpenseReportViewSet

router = DefaultRouter()
router.register("periods", TimesheetPeriodViewSet, basename="ts-period")
router.register("timesheets", TimesheetViewSet, basename="timesheet")
router.register("expenses", ExpenseReportViewSet, basename="expense")

urlpatterns = router.urls
