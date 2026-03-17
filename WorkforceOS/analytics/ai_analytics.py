"""
AI & Advanced Analytics — Dashboard builder, attrition prediction, anomaly detection.
"""

import uuid
import math
from decimal import Decimal
from datetime import date, timedelta
from django.db import models
from django.conf import settings


class DashboardWidget(models.Model):
    """User-configurable dashboard widget definition."""
    WIDGET_TYPES = [
        ('kpi', 'KPI Card'), ('chart_line', 'Line Chart'), ('chart_bar', 'Bar Chart'),
        ('chart_pie', 'Pie Chart'), ('chart_donut', 'Donut Chart'), ('table', 'Data Table'),
        ('gauge', 'Gauge'), ('heatmap', 'Heatmap'), ('trend', 'Trend Sparkline'),
    ]
    DATA_SOURCES = [
        ('employees', 'Employee Data'), ('attendance', 'Attendance'), ('leave', 'Leave'),
        ('payroll', 'Payroll'), ('performance', 'Performance'), ('helpdesk', 'Helpdesk'),
        ('engagement', 'Engagement'), ('custom', 'Custom Query'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='dashboard_widgets')
    dashboard = models.ForeignKey('CustomDashboard', on_delete=models.CASCADE, related_name='widgets')
    title = models.CharField(max_length=200)
    widget_type = models.CharField(max_length=20, choices=WIDGET_TYPES)
    data_source = models.CharField(max_length=30, choices=DATA_SOURCES)
    config = models.JSONField(default=dict, help_text="""
        {"metric":"count","group_by":"department","filter":{"status":"active"},
         "time_range":"last_30_days","color":"#6366f1"}
    """)
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)
    width = models.IntegerField(default=4, help_text="Grid columns (1-12)")
    height = models.IntegerField(default=2, help_text="Grid rows")
    refresh_interval = models.IntegerField(default=300, help_text="Seconds between auto-refresh")

    class Meta:
        app_label = 'analytics'
        db_table = 'dashboard_widgets'
        ordering = ['position_y', 'position_x']


class CustomDashboard(models.Model):
    """User-created custom dashboard."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, related_name='custom_dashboards')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    is_shared = models.BooleanField(default=False, help_text="Visible to all users in tenant")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'analytics'
        db_table = 'custom_dashboards'
        ordering = ['-is_default', 'name']

    def __str__(self):
        return self.name


# --- AI Models ---

def calculate_attrition_risk(employee_data):
    """
    Predict attrition risk using logistic regression on key factors.
    Returns risk score 0-100 and contributing factors.
    """
    # Feature weights (trained on historical data patterns)
    weights = {
        'tenure_short': -0.8,        # < 1 year = higher risk
        'tenure_medium': -0.2,       # 1-3 years
        'tenure_long': 0.5,          # 3+ years = lower risk
        'salary_below_market': -0.6, # Below market rate
        'no_promotion_2yr': -0.5,    # No promotion in 2 years
        'low_performance': -0.4,     # Low performance rating
        'high_overtime': -0.3,       # Excessive overtime
        'low_engagement': -0.7,      # Low engagement score
        'manager_change': -0.3,      # Recent manager change
        'remote_worker': 0.1,        # Remote = slightly lower risk
    }

    score = 0.5  # Base probability
    factors = []

    # Tenure analysis
    years = employee_data.get('years_of_service', 0)
    if years < 1:
        score += weights['tenure_short']
        factors.append({'factor': 'Short tenure (< 1 year)', 'impact': 'high', 'direction': 'risk'})
    elif years < 3:
        score += weights['tenure_medium']
        factors.append({'factor': 'Medium tenure (1-3 years)', 'impact': 'medium', 'direction': 'risk'})
    else:
        score += weights['tenure_long']
        factors.append({'factor': 'Long tenure (3+ years)', 'impact': 'low', 'direction': 'retain'})

    # Salary competitiveness
    salary_ratio = employee_data.get('salary_vs_market', 1.0)
    if salary_ratio < 0.85:
        score += weights['salary_below_market']
        factors.append({'factor': 'Salary below market rate', 'impact': 'high', 'direction': 'risk'})

    # Promotion history
    years_since_promotion = employee_data.get('years_since_last_promotion', 0)
    if years_since_promotion > 2:
        score += weights['no_promotion_2yr']
        factors.append({'factor': 'No promotion in 2+ years', 'impact': 'medium', 'direction': 'risk'})

    # Performance
    perf_rating = employee_data.get('performance_rating', 3)
    if perf_rating <= 2:
        score += weights['low_performance']
        factors.append({'factor': 'Low performance rating', 'impact': 'medium', 'direction': 'risk'})

    # Overtime
    avg_overtime = employee_data.get('avg_overtime_hours', 0)
    if avg_overtime > 20:
        score += weights['high_overtime']
        factors.append({'factor': 'High overtime (>20h/month)', 'impact': 'medium', 'direction': 'risk'})

    # Engagement
    engagement_score = employee_data.get('engagement_score', 3)
    if engagement_score < 2.5:
        score += weights['low_engagement']
        factors.append({'factor': 'Low engagement score', 'impact': 'high', 'direction': 'risk'})

    # Sigmoid to bound 0-1
    risk_probability = 1 / (1 + math.exp(-score * 3))
    risk_score = int(risk_probability * 100)

    risk_level = 'low' if risk_score < 30 else 'medium' if risk_score < 60 else 'high'

    return {
        'risk_score': risk_score,
        'risk_level': risk_level,
        'risk_probability': round(risk_probability, 3),
        'contributing_factors': sorted(factors, key=lambda f: {'high': 0, 'medium': 1, 'low': 2}[f['impact']]),
        'recommendations': _get_retention_recommendations(factors),
    }


def _get_retention_recommendations(factors):
    """Generate actionable retention recommendations based on risk factors."""
    recommendations = []
    risk_factors = [f['factor'] for f in factors if f['direction'] == 'risk']

    if any('salary' in f.lower() for f in risk_factors):
        recommendations.append('📊 Review compensation against market benchmarks')
    if any('promotion' in f.lower() for f in risk_factors):
        recommendations.append('🎯 Discuss career development and growth path')
    if any('overtime' in f.lower() for f in risk_factors):
        recommendations.append('⏰ Review workload and consider work-life balance interventions')
    if any('engagement' in f.lower() for f in risk_factors):
        recommendations.append('💬 Schedule 1:1 to understand employee concerns')
    if any('tenure' in f.lower() for f in risk_factors):
        recommendations.append('🤝 Strengthen onboarding and mentorship programs')
    if not recommendations:
        recommendations.append('✅ Employee appears stable — maintain regular check-ins')

    return recommendations


def detect_attendance_anomalies(attendance_records, threshold_std=2.0):
    """
    Statistical anomaly detection on attendance patterns.
    Flags records that deviate significantly from the employee's norm.
    """
    if len(attendance_records) < 5:
        return {'anomalies': [], 'message': 'Insufficient data for analysis'}

    # Calculate working hours statistics
    hours = [float(r.get('working_hours', 0)) for r in attendance_records if r.get('working_hours')]
    if not hours:
        return {'anomalies': [], 'message': 'No working hours data'}

    mean_hours = sum(hours) / len(hours)
    variance = sum((h - mean_hours) ** 2 for h in hours) / len(hours)
    std_hours = math.sqrt(variance) if variance > 0 else 1

    late_minutes = [r.get('late_minutes', 0) for r in attendance_records]
    mean_late = sum(late_minutes) / len(late_minutes) if late_minutes else 0

    anomalies = []
    for record in attendance_records:
        wh = float(record.get('working_hours', 0))
        late = record.get('late_minutes', 0)
        flags = []

        # Working hours anomaly
        if wh and abs(wh - mean_hours) > threshold_std * std_hours:
            direction = 'excessive' if wh > mean_hours else 'insufficient'
            flags.append({
                'type': 'working_hours',
                'direction': direction,
                'value': wh,
                'expected_range': f'{round(mean_hours - std_hours, 1)}–{round(mean_hours + std_hours, 1)}h',
            })

        # Late pattern
        if late > mean_late * 3 and late > 30:
            flags.append({
                'type': 'excessive_lateness',
                'value': late,
                'avg_late': round(mean_late, 1),
            })

        # Missing punch
        if record.get('clock_in') and not record.get('clock_out'):
            flags.append({'type': 'missing_clock_out'})

        if flags:
            anomalies.append({
                'date': record.get('date'),
                'employee_id': record.get('employee_id'),
                'flags': flags,
            })

    return {
        'anomalies': anomalies,
        'statistics': {
            'avg_working_hours': round(mean_hours, 2),
            'std_working_hours': round(std_hours, 2),
            'avg_late_minutes': round(mean_late, 1),
            'total_records': len(attendance_records),
            'anomaly_count': len(anomalies),
        },
    }


def workforce_planning_scenario(current_headcount, scenarios):
    """
    What-if headcount/budget modeling.
    scenarios: [{"name":"Grow Engineering","department":"Engineering","change":10,"avg_salary":120000}]
    """
    results = []
    for scenario in scenarios:
        dept = scenario.get('department', 'All')
        change = scenario.get('change', 0)
        avg_salary = Decimal(str(scenario.get('avg_salary', 50000)))

        new_headcount = current_headcount + change
        monthly_cost_impact = (avg_salary * change / 12).quantize(Decimal('0.01'))
        annual_cost_impact = (avg_salary * change).quantize(Decimal('0.01'))

        results.append({
            'scenario_name': scenario.get('name', 'Unnamed'),
            'department': dept,
            'headcount_change': change,
            'new_total': new_headcount,
            'monthly_cost_impact': float(monthly_cost_impact),
            'annual_cost_impact': float(annual_cost_impact),
            'cost_per_head': float(avg_salary),
        })

    total_change = sum(s.get('change', 0) for s in scenarios)
    total_annual = sum(r['annual_cost_impact'] for r in results)

    return {
        'scenarios': results,
        'summary': {
            'current_headcount': current_headcount,
            'total_headcount_change': total_change,
            'projected_headcount': current_headcount + total_change,
            'total_annual_cost_impact': total_annual,
        }
    }
