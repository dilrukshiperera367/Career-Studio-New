"""Analytics URL configuration with report endpoints."""
from django.urls import path, include
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from rest_framework.routers import DefaultRouter
from . import views
from datetime import date


class ReportsView(APIView):
    """Download various reports as CSV."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        report_type = request.query_params.get('type')
        year = int(request.query_params.get('year', date.today().year))
        month = int(request.query_params.get('month', date.today().month))

        if report_type == 'headcount':
            from payroll.reports import generate_headcount_report
            csv_content = generate_headcount_report(request.tenant_id)
            filename = f'headcount_report_{year}.csv'

        elif report_type == 'leave_utilization':
            from payroll.reports import generate_leave_utilization_report
            csv_content = generate_leave_utilization_report(request.tenant_id, year)
            filename = f'leave_utilization_{year}.csv'

        elif report_type == 'attendance':
            from payroll.reports import generate_attendance_report
            csv_content = generate_attendance_report(request.tenant_id, year, month)
            filename = f'attendance_summary_{year}_{month:02d}.csv'

        else:
            return Response({'error': {'message': 'Invalid report type. Use: headcount, leave_utilization, attendance'}}, status=400)

        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


router = DefaultRouter()
router.register(r'analytics/widgets', views.DashboardWidgetViewSet, basename='dashboard-widget')
router.register(r'analytics/custom-dashboards', views.CustomDashboardViewSet, basename='custom-dashboard')

urlpatterns = [
    path('', include(router.urls)),
    path('analytics/dashboard/', views.DashboardView.as_view(), name='analytics-dashboard'),
    path('analytics/headcount-trend/', views.HeadcountTrendView.as_view(), name='analytics-headcount-trend'),
    path('analytics/nl-search/', views.NaturalLanguageAnalyticsView.as_view(), name='analytics-nl-search'),
    path('analytics/reports/', ReportsView.as_view(), name='analytics-reports'),
    path('analytics/attrition/', views.AttritionView.as_view(), name='analytics-attrition'),
    path('analytics/payroll/', views.PayrollAnalyticsView.as_view(), name='analytics-payroll'),
    path('analytics/performance/', views.PerformanceAnalyticsView.as_view(), name='analytics-performance'),
    path('analytics/diversity/', views.DiversityView.as_view(), name='analytics-diversity'),
    path('analytics/attendance/', views.AttendanceAnalyticsView.as_view(), name='analytics-attendance'),
]
