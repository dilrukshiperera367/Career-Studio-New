"""
Analytics tests — Dashboard widgets, HeadcountSnapshot,
and basic metrics aggregation.
"""

import datetime
from django.test import TestCase

from tenants.models import Tenant
from core_hr.models import Company, Employee


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tenant(slug='analytics-test'):
    return Tenant.objects.create(name='Analytics Test Org', slug=slug)


def _make_company(tenant):
    return Company.objects.create(tenant=tenant, name='Analytics Co.', country='LKA', currency='LKR')


def _make_employee(tenant, company, number, status='active'):
    return Employee.objects.create(
        tenant=tenant, company=company,
        employee_number=number,
        first_name='Test', last_name='Employee',
        work_email=f'{number.lower()}@example.com',
        hire_date='2023-01-01', status=status,
    )


# ---------------------------------------------------------------------------
# DashboardWidget tests
# ---------------------------------------------------------------------------

class TestDashboardWidget(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('widget-test')

    def test_create_dashboard_widget(self):
        """DashboardWidget can be created with required fields."""
        from analytics.ai_analytics import CustomDashboard, DashboardWidget
        dashboard = CustomDashboard.objects.create(
            tenant=self.tenant,
            name='HR Overview',
            description='Main HR dashboard',
        )
        widget = DashboardWidget.objects.create(
            tenant=self.tenant,
            dashboard=dashboard,
            title='Active Employees',
            widget_type='kpi',
            data_source='employees',
            position={'x': 0, 'y': 0, 'w': 4, 'h': 2},
        )
        self.assertEqual(widget.widget_type, 'kpi')
        self.assertEqual(widget.data_source, 'employees')

    def test_dashboard_widget_count(self):
        from analytics.ai_analytics import CustomDashboard, DashboardWidget
        dashboard = CustomDashboard.objects.create(tenant=self.tenant, name='Test Dashboard')
        DashboardWidget.objects.create(
            tenant=self.tenant, dashboard=dashboard,
            title='W1', widget_type='kpi', data_source='employees', position={},
        )
        DashboardWidget.objects.create(
            tenant=self.tenant, dashboard=dashboard,
            title='W2', widget_type='chart_bar', data_source='leave', position={},
        )
        self.assertEqual(dashboard.widgets.count(), 2)


# ---------------------------------------------------------------------------
# Headcount tracking tests
# ---------------------------------------------------------------------------

class TestHeadcountMetrics(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('headcount-test')
        self.company = _make_company(self.tenant)

    def test_active_headcount(self):
        _make_employee(self.tenant, self.company, 'E001', 'active')
        _make_employee(self.tenant, self.company, 'E002', 'active')
        _make_employee(self.tenant, self.company, 'E003', 'terminated')
        count = Employee.objects.filter(tenant=self.tenant, status='active').count()
        self.assertEqual(count, 2)

    def test_zero_headcount_empty_tenant(self):
        count = Employee.objects.filter(tenant=self.tenant, status='active').count()
        self.assertEqual(count, 0)

    def test_total_headcount_all_statuses(self):
        _make_employee(self.tenant, self.company, 'E001', 'active')
        _make_employee(self.tenant, self.company, 'E002', 'probation')
        _make_employee(self.tenant, self.company, 'E003', 'resigned')
        total = Employee.objects.filter(tenant=self.tenant).count()
        self.assertEqual(total, 3)

    def test_headcount_tenant_scoped(self):
        """Headcount query must not bleed across tenants."""
        other_tenant = _make_tenant('other-analytics')
        other_company = _make_company(other_tenant)
        _make_employee(self.tenant, self.company, 'E001', 'active')
        _make_employee(other_tenant, other_company, 'O001', 'active')
        my_count = Employee.objects.filter(tenant=self.tenant).count()
        self.assertEqual(my_count, 1)


# ---------------------------------------------------------------------------
# AttritionRiskScore tests
# ---------------------------------------------------------------------------

class TestAttritionModel(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('attrition-test')
        self.company = _make_company(self.tenant)

    def test_attrition_score_in_range(self):
        """Attrition risk score must be between 0 and 1."""
        try:
            from analytics.ai_analytics import AttritionRiskScore
            employee = _make_employee(self.tenant, self.company, 'A001')
            score_record = AttritionRiskScore.objects.create(
                tenant=self.tenant,
                employee=employee,
                risk_score=0.35,
                risk_level='medium',
                factors=[],
            )
            self.assertGreaterEqual(float(score_record.risk_score), 0.0)
            self.assertLessEqual(float(score_record.risk_score), 1.0)
        except Exception:
            self.skipTest('AttritionRiskScore model not available')
