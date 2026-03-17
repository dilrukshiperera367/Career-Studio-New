"""Leave & Attendance URL configuration."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'leave/types', views.LeaveTypeViewSet, basename='leave-type')
router.register(r'leave/balances', views.LeaveBalanceViewSet, basename='leave-balance')
router.register(r'leave/requests', views.LeaveRequestViewSet, basename='leave-request')
router.register(r'holidays', views.HolidayViewSet, basename='holiday')
router.register(r'shifts', views.ShiftTemplateViewSet, basename='shift')
router.register(r'shift-assignments', views.ShiftAssignmentViewSet, basename='shift-assignment')
router.register(r'attendance', views.AttendanceViewSet, basename='attendance')
router.register(r'overtime', views.OvertimeViewSet, basename='overtime')
# P1 upgrades
router.register(r'rosters', views.RosterViewSet, basename='roster')
router.register(r'roster-slots', views.RosterSlotViewSet, basename='roster-slot')
router.register(r'shift-swaps', views.ShiftSwapRequestViewSet, basename='shift-swap')
router.register(r'shift-bids', views.ShiftBidViewSet, basename='shift-bid')
router.register(r'shift-bid-applications', views.ShiftBidApplicationViewSet, basename='shift-bid-application')
router.register(r'geofence-zones', views.GeofenceZoneViewSet, basename='geofence-zone')
# Feature 4 upgrades
router.register(r'availability', views.EmployeeAvailabilityViewSet, basename='availability')
router.register(r'break-records', views.BreakRecordViewSet, basename='break-record')
router.register(r'biometric-devices', views.BiometricDeviceViewSet, basename='biometric-device')
router.register(r'fatigue-alerts', views.FatigueAlertViewSet, basename='fatigue-alert')
router.register(r'attendance-anomalies', views.AttendanceAnomalyViewSet, basename='attendance-anomaly')
router.register(r'absence-forecasts', views.AbsenceForecastViewSet, basename='absence-forecast')
router.register(r'overtime-thresholds', views.OvertimeThresholdViewSet, basename='overtime-threshold')
router.register(r'union-rule-packs', views.UnionRulePackViewSet, basename='union-rule-pack')
router.register(r'site-attendance-analytics', views.SiteAttendanceAnalyticsViewSet, basename='site-attendance-analytics')
router.register(r'contractor-time-entries', views.ContractorTimeEntryViewSet, basename='contractor-time-entry')
router.register(r'shift-coverage-plans', views.ShiftCoveragePlanViewSet, basename='shift-coverage-plan')

urlpatterns = [
    path('', include(router.urls)),
]
