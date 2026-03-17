"""Analytics API — Dashboard endpoints."""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets, serializers, permissions, status
from rest_framework.decorators import action
from django.db import models
from django.db.models import Avg, Sum, Count
from django.core.cache import cache
from datetime import date, timedelta

from config.base_api import TenantViewSetMixin, TenantSerializerMixin
from core_hr.models import Employee
from core_hr.cache import make_cache_key, CACHE_MEDIUM
from leave_attendance.models import LeaveRequest, AttendanceRecord
from payroll.models import PayrollRun
from .models import DashboardWidget, CustomDashboard


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

class DashboardWidgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardWidget
        fields = '__all__'
        read_only_fields = ['id', 'tenant']


class CustomDashboardSerializer(serializers.ModelSerializer):
    widgets = DashboardWidgetSerializer(many=True, read_only=True)

    class Meta:
        model = CustomDashboard
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_by', 'created_at', 'updated_at']


# ---------------------------------------------------------------------------
# ViewSets
# ---------------------------------------------------------------------------

class DashboardWidgetViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    """CRUD for individual dashboard widgets."""
    queryset = DashboardWidget.objects.select_related('dashboard').all()
    serializer_class = DashboardWidgetSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['dashboard', 'widget_type', 'data_source']

    def get_queryset(self):
        qs = super().get_queryset()
        dashboard_id = self.request.query_params.get('dashboard')
        if dashboard_id:
            qs = qs.filter(dashboard_id=dashboard_id)
        return qs


class CustomDashboardViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    """CRUD for custom dashboards (dashboard builder)."""
    queryset = CustomDashboard.objects.prefetch_related('widgets').all()
    serializer_class = CustomDashboardSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['is_default', 'is_shared']
    search_fields = ['name', 'description']

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.tenant_id,
            created_by=self.request.user,
        )

    @action(detail=True, methods=['post'], url_path='set-default')
    def set_default(self, request, pk=None):
        """Mark this dashboard as the default for the tenant."""
        dashboard = self.get_object()
        CustomDashboard.objects.filter(
            tenant_id=request.tenant_id, is_default=True
        ).exclude(pk=dashboard.pk).update(is_default=False)
        dashboard.is_default = True
        dashboard.save(update_fields=['is_default'])
        return Response({'data': CustomDashboardSerializer(dashboard).data})


class DashboardView(APIView):
    """Main HR dashboard with KPIs."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant_id = request.tenant_id
        today = date.today()

        # Serve from cache — keyed by tenant + date (refreshes every 5 min or on new day)
        cache_key = make_cache_key('hrm_dashboard', tenant_id, today.isoformat())
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        # Headcount
        active_employees = Employee.objects.filter(
            tenant_id=tenant_id, status__in=['active', 'probation']
        )
        total = active_employees.count()

        # Department breakdown
        dept_counts = list(active_employees.values('department__name').annotate(
            count=models.Count('id')
        ).order_by('-count')[:10])

        # New hires this month
        new_hires = active_employees.filter(
            hire_date__year=today.year, hire_date__month=today.month
        ).count()

        # Exits this month
        exits = Employee.objects.filter(
            tenant_id=tenant_id,
            separation_date__year=today.year,
            separation_date__month=today.month,
        ).count()

        # Pending leave requests
        pending_leaves = LeaveRequest.objects.filter(
            tenant_id=tenant_id, status='pending'
        ).count()

        # Today's attendance
        clocked_in_today = AttendanceRecord.objects.filter(
            tenant_id=tenant_id, date=today, clock_in__isnull=False
        ).count()

        # Status breakdown
        status_counts = list(Employee.objects.filter(
            tenant_id=tenant_id
        ).values('status').annotate(count=models.Count('id')))

        # Gender breakdown
        gender_counts = list(active_employees.values('gender').annotate(count=models.Count('id')))

        data = {
            'data': {
                'headcount': {
                    'total': total,
                    'by_department': dept_counts,
                    'by_status': status_counts,
                    'by_gender': gender_counts,
                },
                'this_month': {
                    'new_hires': new_hires,
                    'exits': exits,
                },
                'today': {
                    'clocked_in': clocked_in_today,
                    'pending_leaves': pending_leaves,
                },
            }
        }
        cache.set(cache_key, data, CACHE_MEDIUM)
        return Response(data)


class HeadcountTrendView(APIView):
    """Headcount trend over last 12 months."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant_id = request.tenant_id
        today = date.today()
        trend = []

        for i in range(11, -1, -1):
            month_date = today.replace(day=1) - timedelta(days=i * 30)
            count = Employee.objects.filter(
                tenant_id=tenant_id,
                hire_date__lte=month_date,
            ).exclude(
                separation_date__lt=month_date,
            ).count()
            trend.append({
                'month': month_date.strftime('%Y-%m'),
                'count': count,
            })

        return Response({'data': trend})

class NaturalLanguageAnalyticsView(APIView):
    """
    Mock LLM endpoint translating natural language (e.g. 'headcount by department')
    into Django ORM aggregations.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        query = request.data.get('query', '').lower()
        tenant_id = request.tenant_id
        
        # Base active employees query
        active_employees = Employee.objects.filter(
            tenant_id=tenant_id, status__in=['active', 'probation']
        )
        
        response_data = {}
        chart_type = 'indicator' # default
        
        # Simple heuristic parser
        if 'headcount' in query or 'how many employ' in query:
            if 'department' in query:
                data = list(active_employees.values('department__name').annotate(
                    value=models.Count('id')
                ).order_by('-value'))
                for item in data:
                    item['label'] = item.pop('department__name') or 'Unassigned'
                response_data = data
                chart_type = 'bar'
            elif 'branch' in query or 'location' in query:
                data = list(active_employees.values('branch__name').annotate(
                    value=models.Count('id')
                ).order_by('-value'))
                for item in data:
                    item['label'] = item.pop('branch__name') or 'Unassigned'
                response_data = data
                chart_type = 'bar'
            elif 'gender' in query:
                data = list(active_employees.values('gender').annotate(
                    value=models.Count('id')
                ))
                for item in data:
                    item['label'] = item.pop('gender') or 'Unspecified'
                response_data = data
                chart_type = 'pie'
            else:
                response_data = [{'label': 'Total Headcount', 'value': active_employees.count()}]
                
        elif 'salary' in query or 'compensation' in query:
            response_data = [{'label': 'Total Payroll (Mock)', 'value': '$125,000'}]
            
        elif 'leave' in query or 'absence' in query:
            leaves = LeaveRequest.objects.filter(tenant_id=tenant_id, status='approved').count()
            response_data = [{'label': 'Total Approved Leaves', 'value': leaves}]
            
        else:
            return Response({
                'error': "I'm still learning! Try asking about 'headcount by department' or 'employees by gender'."
            }, status=400)
            
        return Response({
            'query': query,
            'chart_type': chart_type,
            'data': response_data
        })


# ---------------------------------------------------------------------------
# Attrition Analytics
# ---------------------------------------------------------------------------

class AttritionView(APIView):
    """GET /api/v1/analytics/attrition/ — turnover rate, avg tenure, separations by dept/reason."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant_id = request.tenant_id
        today = date.today()

        # Parameters: rolling 12 months by default
        months = int(request.query_params.get('months', 12))
        period_start = (today.replace(day=1) - timedelta(days=months * 30)).replace(day=1)

        base_qs = Employee.objects.filter(tenant_id=tenant_id)

        # Headcount snapshot at period start
        headcount_start = base_qs.filter(
            hire_date__lt=period_start,
        ).exclude(
            separation_date__lt=period_start,
        ).count()

        # Separations in period
        exits_qs = base_qs.filter(
            separation_date__gte=period_start,
            separation_date__lte=today,
        )
        total_exits = exits_qs.count()

        # Turnover rate (simplified: exits / avg headcount)
        headcount_now = base_qs.filter(status__in=['active', 'probation']).count()
        avg_headcount = (headcount_start + headcount_now) / 2 if headcount_start + headcount_now > 0 else 1
        turnover_rate = round((total_exits / avg_headcount) * 100, 1)

        # Separations by department
        by_dept = list(exits_qs.values('department__name').annotate(
            count=models.Count('id')
        ).order_by('-count')[:10])
        for item in by_dept:
            item['department'] = item.pop('department__name') or 'Unassigned'

        # Separation reasons (non-blank)
        reasons_raw = exits_qs.values_list('separation_reason', flat=True)
        reason_counts: dict = {}
        for reason in reasons_raw:
            if reason:
                key = reason[:60]
                reason_counts[key] = reason_counts.get(key, 0) + 1
        by_reason = sorted(
            [{'reason': k, 'count': v} for k, v in reason_counts.items()],
            key=lambda x: -x['count'],
        )[:10]

        # Avg tenure of exited employees (years)
        avg_tenure = None
        tenure_sum = 0
        tenure_count = 0
        for emp in exits_qs.only('hire_date', 'separation_date'):
            if emp.hire_date and emp.separation_date:
                tenure_sum += (emp.separation_date - emp.hire_date).days
                tenure_count += 1
        if tenure_count:
            avg_tenure = round(tenure_sum / tenure_count / 365.25, 1)

        # Monthly exits trend
        monthly_exits = []
        for i in range(months - 1, -1, -1):
            m_date = (today.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
            if m_date.month == 12:
                m_end = m_date.replace(year=m_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                m_end = m_date.replace(month=m_date.month + 1, day=1) - timedelta(days=1)
            count = exits_qs.filter(
                separation_date__gte=m_date,
                separation_date__lte=m_end,
            ).count()
            monthly_exits.append({'month': m_date.strftime('%Y-%m'), 'exits': count})

        return Response({'data': {
            'period_months': months,
            'total_exits': total_exits,
            'turnover_rate_pct': turnover_rate,
            'avg_tenure_years': avg_tenure,
            'by_department': by_dept,
            'by_reason': by_reason,
            'monthly_trend': monthly_exits,
        }})


# ---------------------------------------------------------------------------
# Payroll Analytics
# ---------------------------------------------------------------------------

class PayrollAnalyticsView(APIView):
    """GET /api/v1/analytics/payroll/ — total cost by dept, month-over-month trend."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant_id = request.tenant_id
        today = date.today()
        months = int(request.query_params.get('months', 6))

        # Latest finalized run totals
        latest_runs = list(
            PayrollRun.objects.filter(
                tenant_id=tenant_id,
                status='finalized',
            ).order_by('-period_year', '-period_month').values(
                'period_year', 'period_month',
                'total_gross', 'total_net', 'total_employer_cost',
                'employee_count',
            )[:months]
        )
        # Sort ascending for chart
        latest_runs = list(reversed(latest_runs))
        for run in latest_runs:
            run['period'] = f"{run.pop('period_year')}-{run.pop('period_month'):02d}"
            run['total_gross'] = float(run['total_gross'])
            run['total_net'] = float(run['total_net'])
            run['total_employer_cost'] = float(run['total_employer_cost'])

        # Cost by department (from PayrollEntry via employee.department)
        from payroll.models import PayrollEntry
        current_run = PayrollRun.objects.filter(
            tenant_id=tenant_id,
            status='finalized',
        ).order_by('-period_year', '-period_month').first()

        by_dept = []
        if current_run:
            by_dept = list(
                PayrollEntry.objects.filter(payroll_run=current_run).values(
                    'employee__department__name'
                ).annotate(
                    total_net=models.Sum('net_salary'),
                    total_gross=models.Sum('gross_salary'),
                    headcount=models.Count('id'),
                ).order_by('-total_net')[:15]
            )
            for item in by_dept:
                item['department'] = item.pop('employee__department__name') or 'Unassigned'
                item['total_net'] = float(item['total_net'] or 0)
                item['total_gross'] = float(item['total_gross'] or 0)

        return Response({'data': {
            'monthly_trend': latest_runs,
            'by_department': by_dept,
            'current_period': f"{current_run.period_year}-{current_run.period_month:02d}" if current_run else None,
        }})


# ---------------------------------------------------------------------------
# Performance Analytics
# ---------------------------------------------------------------------------

class PerformanceAnalyticsView(APIView):
    """GET /api/v1/analytics/performance/ — rating distribution and completion rates."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from performance.models import PerformanceReview, ReviewCycle

        tenant_id = request.tenant_id
        cycle_id = request.query_params.get('cycle_id')

        reviews_qs = PerformanceReview.objects.filter(tenant_id=tenant_id)
        if cycle_id:
            reviews_qs = reviews_qs.filter(cycle_id=cycle_id)

        total = reviews_qs.count()
        completed = reviews_qs.filter(status__in=['calibrated', 'finalized']).count()
        pending = reviews_qs.filter(status='pending').count()
        in_progress = total - completed - pending

        completion_rate = round((completed / total * 100), 1) if total > 0 else 0

        # Rating distribution (bucket into 1-2, 2-3, 3-4, 4-5)
        rated = reviews_qs.exclude(final_rating__isnull=True)
        dist = [
            {'range': '1.0-2.0', 'count': rated.filter(final_rating__gte=1, final_rating__lt=2).count()},
            {'range': '2.0-3.0', 'count': rated.filter(final_rating__gte=2, final_rating__lt=3).count()},
            {'range': '3.0-4.0', 'count': rated.filter(final_rating__gte=3, final_rating__lt=4).count()},
            {'range': '4.0-5.0', 'count': rated.filter(final_rating__gte=4, final_rating__lte=5).count()},
        ]

        avg_rating = rated.aggregate(avg=models.Avg('final_rating'))['avg']
        avg_rating = round(float(avg_rating), 2) if avg_rating else None

        # By department
        by_dept = list(
            rated.values('employee__department__name').annotate(
                avg_rating=models.Avg('final_rating'),
                count=models.Count('id'),
            ).order_by('-avg_rating')[:10]
        )
        for item in by_dept:
            item['department'] = item.pop('employee__department__name') or 'Unassigned'
            item['avg_rating'] = round(float(item['avg_rating'] or 0), 2)

        # Available cycles for this tenant
        cycles = list(
            ReviewCycle.objects.filter(tenant_id=tenant_id).values('id', 'name', 'status').order_by('-created_at')[:10]
        )
        for c in cycles:
            c['id'] = str(c['id'])

        return Response({'data': {
            'total_reviews': total,
            'completed': completed,
            'pending': pending,
            'in_progress': in_progress,
            'completion_rate_pct': completion_rate,
            'avg_rating': avg_rating,
            'rating_distribution': dist,
            'by_department': by_dept,
            'cycles': cycles,
        }})


# ---------------------------------------------------------------------------
# Diversity Analytics
# ---------------------------------------------------------------------------

class DiversityView(APIView):
    """GET /api/v1/analytics/diversity/ — gender, age, tenure breakdowns."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant_id = request.tenant_id
        today = date.today()

        active = Employee.objects.filter(tenant_id=tenant_id, status__in=['active', 'probation'])
        total = active.count()

        # Gender breakdown
        by_gender = list(active.values('gender').annotate(count=models.Count('id')))
        for item in by_gender:
            item['gender'] = item['gender'] or 'Not specified'
            item['pct'] = round(item['count'] / total * 100, 1) if total else 0

        # Age brackets
        age_brackets = [
            {'label': 'Under 25', 'min_year': today.year - 24, 'max_year': today.year},
            {'label': '25–34', 'min_year': today.year - 34, 'max_year': today.year - 25},
            {'label': '35–44', 'min_year': today.year - 44, 'max_year': today.year - 35},
            {'label': '45–54', 'min_year': today.year - 54, 'max_year': today.year - 45},
            {'label': '55+', 'min_year': None, 'max_year': today.year - 55},
        ]
        age_dist = []
        for bracket in age_brackets:
            qs = active.exclude(date_of_birth__isnull=True)
            if bracket['min_year'] and bracket['max_year']:
                qs = qs.filter(
                    date_of_birth__year__gte=bracket['min_year'],
                    date_of_birth__year__lte=bracket['max_year'],
                )
            elif bracket['max_year']:
                qs = qs.filter(date_of_birth__year__lte=bracket['max_year'])
            count = qs.count()
            age_dist.append({
                'label': bracket['label'],
                'count': count,
                'pct': round(count / total * 100, 1) if total else 0,
            })

        # Tenure brackets (years of service)
        tenure_brackets = [
            ('Under 1 year', 0, 1),
            ('1–2 years', 1, 2),
            ('3–5 years', 3, 5),
            ('6–10 years', 6, 10),
            ('10+ years', 10, None),
        ]
        tenure_dist = []
        for label, min_yr, max_yr in tenure_brackets:
            cutoff_max = today.replace(year=today.year - min_yr) if min_yr else today
            cutoff_min = today.replace(year=today.year - max_yr) if max_yr else None
            qs = active
            qs = qs.filter(hire_date__lte=cutoff_max)
            if cutoff_min:
                qs = qs.filter(hire_date__gte=cutoff_min)
            count = qs.count()
            tenure_dist.append({
                'label': label,
                'count': count,
                'pct': round(count / total * 100, 1) if total else 0,
            })

        # Gender × department (top 5 depts)
        top_depts = list(
            active.values('department__name').annotate(count=models.Count('id')).order_by('-count')[:5]
        )
        dept_gender = []
        for d in top_depts:
            dept_name = d['department__name'] or 'Unassigned'
            breakdown = list(
                active.filter(department__name=dept_name).values('gender').annotate(count=models.Count('id'))
            )
            dept_gender.append({'department': dept_name, 'breakdown': breakdown})

        return Response({'data': {
            'total_active': total,
            'by_gender': by_gender,
            'by_age': age_dist,
            'by_tenure': tenure_dist,
            'dept_gender_breakdown': dept_gender,
        }})


# ---------------------------------------------------------------------------
# Attendance Analytics
# ---------------------------------------------------------------------------

class AttendanceAnalyticsView(APIView):
    """GET /api/v1/analytics/attendance/ — present/absent rates, late, overtime trend."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from leave_attendance.models import AttendanceRecord
        from django.db.models import Avg, Sum

        tenant_id = request.tenant_id
        today = date.today()
        months = int(request.query_params.get('months', 3))

        period_start = (today.replace(day=1) - timedelta(days=max(months - 1, 0) * 30)).replace(day=1)

        base_qs = AttendanceRecord.objects.filter(
            tenant_id=tenant_id,
            date__gte=period_start,
            date__lte=today,
        )

        total = base_qs.count()

        # Status breakdown
        try:
            by_status = list(
                base_qs.values('status').annotate(count=models.Count('id')).order_by('-count')
            )
        except Exception:
            by_status = []

        # Presence rate
        present_count = 0
        absent_count = 0
        for item in by_status:
            if item['status'] in ('present', 'half_day'):
                present_count += item['count']
            elif item['status'] == 'absent':
                absent_count += item['count']
        presence_rate = round(present_count / total * 100, 1) if total else 0

        # Aggregate stats
        try:
            agg = base_qs.aggregate(
                avg_hours=Avg('working_hours'),
                total_overtime=Sum('overtime_hours'),
                avg_late=Avg('late_minutes'),
            )
            avg_hours = round(float(agg['avg_hours'] or 0), 2)
            total_overtime = round(float(agg['total_overtime'] or 0), 1)
            avg_late_minutes = round(float(agg['avg_late'] or 0), 1)
        except Exception:
            avg_hours = 0
            total_overtime = 0
            avg_late_minutes = 0

        # Exception breakdown
        try:
            by_exception = list(
                base_qs.exclude(exception_type='').values('exception_type')
                .annotate(count=models.Count('id')).order_by('-count')
            )
        except Exception:
            by_exception = []

        # Monthly trend
        monthly_trend = []
        for i in range(months - 1, -1, -1):
            m_date = (today.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
            if m_date.month == 12:
                m_end = m_date.replace(year=m_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                m_end = m_date.replace(month=m_date.month + 1, day=1) - timedelta(days=1)
            try:
                m_qs = base_qs.filter(date__gte=m_date, date__lte=m_end)
                m_total = m_qs.count()
                m_present = m_qs.filter(status__in=['present', 'half_day']).count()
                m_absent = m_qs.filter(status='absent').count()
                m_late = m_qs.exclude(exception_type='').filter(exception_type='late').count()
                m_overtime = m_qs.aggregate(ot=Sum('overtime_hours'))['ot'] or 0
                daily_slots = max(m_total, 1)
                monthly_trend.append({
                    'month': m_date.strftime('%Y-%m'),
                    'total_records': m_total,
                    'present': m_present,
                    'absent': m_absent,
                    'late': m_late,
                    'overtime_hours': round(float(m_overtime), 1),
                    'presence_rate': round(m_present / daily_slots * 100, 1),
                })
            except Exception:
                monthly_trend.append({'month': m_date.strftime('%Y-%m'), 'present': 0, 'absent': 0})

        return Response({'data': {
            'period_months': months,
            'total_records': total,
            'presence_rate_pct': presence_rate,
            'avg_working_hours': avg_hours,
            'total_overtime_hours': total_overtime,
            'avg_late_minutes': avg_late_minutes,
            'by_status': by_status,
            'by_exception': by_exception,
            'monthly_trend': monthly_trend,
        }})
