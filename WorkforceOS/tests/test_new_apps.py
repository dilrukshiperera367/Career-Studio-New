"""
Tests for the 12 new apps and related task/email-template fixes.

Covers:
  - Model creation & __str__ for all 12 new apps
  - core_hr tasks: probation alert derived-date logic
  - onboarding tasks: correct field names (assignee, instance)
  - platform_core email_service: all 23 template keys present
  - email template render sanity (no missing format vars)
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tenant(name="Test Corp", slug=None):
    from tenants.models import Tenant
    slug = slug or name.lower().replace(" ", "-")
    return Tenant.objects.create(name=name, slug=slug)


def _make_company(tenant):
    from core_hr.models import Company
    return Company.objects.create(
        tenant=tenant, name="Test Co Ltd", country="LK", currency="LKR"
    )


def _make_department(tenant, company):
    from core_hr.models import Department
    return Department.objects.create(tenant=tenant, company=company, name="Engineering")


def _make_position(tenant, company, department):
    from core_hr.models import Position
    return Position.objects.create(
        tenant=tenant, department=department,
        title="Software Engineer", headcount=5,
    )


def _make_employee(tenant, company, department=None, position=None, number="EMP-TEST",
                   status="active", hire_date="2023-01-01", probation_months=3):
    from core_hr.models import Employee
    return Employee.objects.create(
        tenant=tenant, company=company,
        department=department, position=position,
        employee_number=number,
        first_name="Jane", last_name="Doe",
        work_email=f"{number.lower()}@example.com",
        hire_date=hire_date, status=status,
        probation_months=probation_months,
    )


# ---------------------------------------------------------------------------
# Email templates — no DB required
# ---------------------------------------------------------------------------

class TestEmailTemplates:
    """All expected template keys must be present and renderable."""

    REQUIRED_KEYS = [
        'leave_approved', 'leave_rejected', 'leave_request',
        'payslip_ready', 'onboarding_task', 'announcement',
        'password_reset', 'welcome', 'approval_needed',
        'review_assigned', 'document_expiring',
        # newly added
        'certification_expiring', 'onboarding_task_due_soon',
        'onboarding_task_overdue', 'payroll_reminder',
        'payslip_dispatch', 'performance_review_due',
        'performance_self_assessment_due', 'probation_ending',
        'visa_permit_expiry', 'merit_cycle_deadline',
        'policy_acknowledgement_reminder', 'attrition_risk_alert',
    ]

    def test_all_required_template_keys_present(self):
        from platform_core.email_service import TEMPLATES
        for key in self.REQUIRED_KEYS:
            assert key in TEMPLATES, f"Missing email template: '{key}'"

    def test_each_template_has_subject_and_body(self):
        from platform_core.email_service import TEMPLATES
        for key, tpl in TEMPLATES.items():
            assert 'subject' in tpl, f"Template '{key}' missing 'subject'"
            assert 'body' in tpl, f"Template '{key}' missing 'body'"
            assert tpl['subject'], f"Template '{key}' has empty subject"
            assert tpl['body'], f"Template '{key}' has empty body"

    def test_send_notification_email_unknown_key_returns_false(self):
        from platform_core.email_service import send_notification_email
        result = send_notification_email('nonexistent_key_xyz', 'test@example.com', {})
        assert result is False

    @patch('platform_core.email_service.send_mail')
    def test_send_notification_email_probation_ending(self, mock_send):
        mock_send.return_value = 1
        from platform_core.email_service import send_notification_email
        ctx = {
            'manager_name': 'Alice', 'employee_name': 'Bob',
            'days_remaining': 7, 'probation_end_date': '2025-07-01',
            'company_name': 'Acme',
        }
        result = send_notification_email('probation_ending', 'mgr@example.com', ctx)
        assert result is True
        mock_send.assert_called_once()

    @patch('platform_core.email_service.send_mail')
    def test_send_notification_email_attrition_risk_alert(self, mock_send):
        mock_send.return_value = 1
        from platform_core.email_service import send_notification_email
        ctx = {
            'recipient_name': 'HR Manager', 'employee_name': 'Bob',
            'risk_score': 87, 'risk_factors': 'low engagement, long tenure',
            'company_name': 'Acme',
        }
        result = send_notification_email('attrition_risk_alert', 'hr@example.com', ctx)
        assert result is True

    @patch('platform_core.email_service.send_mail')
    def test_send_notification_email_missing_context_var_returns_false(self, mock_send):
        """Template rendering with a missing variable must return False, not crash."""
        from platform_core.email_service import send_notification_email
        # probation_ending needs {manager_name} etc. — pass empty dict
        result = send_notification_email('probation_ending', 'x@y.com', {})
        assert result is False
        mock_send.assert_not_called()


# ---------------------------------------------------------------------------
# core_hr tasks — probation alert
# ---------------------------------------------------------------------------

class TestSendProbationPeriodAlerts:

    @patch('platform_core.email_service.send_notification_email', return_value=True)
    def test_alerts_sent_for_employees_with_matching_probation_end(
        self, mock_email, db
    ):
        """Employees whose hire_date + probation_months == today+30 should get an alert."""
        from core_hr.tasks import send_probation_period_alerts
        from dateutil.relativedelta import relativedelta

        tenant = _make_tenant("ProbationCorp", "probation-corp")
        company = _make_company(tenant)
        dept = _make_department(tenant, company)
        pos = _make_position(tenant, company, dept)

        today = date.today()
        target_days = 30
        probation_months = 3
        # hire_date such that hire_date + 3 months = today + 30 days
        hire_date = today + timedelta(days=target_days) - relativedelta(months=probation_months)

        # Create manager
        manager = _make_employee(
            tenant, company, dept, pos,
            number="MGR-PROB-1", hire_date="2020-01-01",
        )
        # Create probation employee
        emp = _make_employee(
            tenant, company, dept, pos,
            number="EMP-PROB-1",
            status='probation',
            hire_date=hire_date.isoformat(),
            probation_months=probation_months,
        )
        emp.manager = manager
        emp.save()

        result = send_probation_period_alerts()
        assert result['sent'] >= 1

    @patch('platform_core.email_service.send_notification_email', return_value=True)
    def test_no_alert_for_active_employee(self, mock_email, db):
        """Active (non-probation) employees must never trigger probation alerts."""
        from core_hr.tasks import send_probation_period_alerts

        tenant = _make_tenant("ActiveCorp", "active-corp")
        company = _make_company(tenant)
        _make_employee(tenant, company, number="EMP-ACT-1", status='active')

        result = send_probation_period_alerts()
        assert result['sent'] == 0

    def test_probation_end_derivation_no_db(self):
        """Pure unit: derived probation end date logic is correct."""
        from dateutil.relativedelta import relativedelta
        hire = date(2025, 1, 15)
        months = 3
        derived = hire + relativedelta(months=months)
        assert derived == date(2025, 4, 15)


# ---------------------------------------------------------------------------
# onboarding tasks — field name correctness
# ---------------------------------------------------------------------------

class TestSendOnboardingTaskReminders:

    @patch('platform_core.email_service.send_notification_email', return_value=True)
    def test_due_soon_reminder_uses_instance_and_assignee(self, mock_email, db):
        """Tasks with instance__employee and assignee FK should produce reminders."""
        from onboarding.models import OnboardingTemplate, OnboardingInstance, OnboardingTask
        from onboarding.tasks import send_onboarding_task_reminders

        tenant = _make_tenant("OnboardCorp", "onboard-corp")
        company = _make_company(tenant)
        emp = _make_employee(tenant, company, number="EMP-ONBOARD-1")

        template = OnboardingTemplate.objects.create(
            tenant=tenant,
            name="Standard Onboarding",
        )
        instance = OnboardingInstance.objects.create(
            tenant=tenant,
            employee=emp,
            template=template,
            start_date=date.today(),
        )
        due_soon = date.today() + timedelta(days=3)
        OnboardingTask.objects.create(
            tenant=tenant,
            instance=instance,
            title="Set up laptop",
            due_date=due_soon,
            status='pending',
        )

        result = send_onboarding_task_reminders()
        assert result['sent'] >= 1

    @patch('platform_core.email_service.send_notification_email', return_value=True)
    def test_overdue_reminder_uses_instance_not_plan(self, mock_email, db):
        """Overdue tasks referencing instance.employee must trigger overdue reminders."""
        from onboarding.models import OnboardingTemplate, OnboardingInstance, OnboardingTask
        from onboarding.tasks import send_onboarding_task_reminders

        tenant = _make_tenant("OverdueCorp", "overdue-corp")
        company = _make_company(tenant)
        emp = _make_employee(
            tenant, company, number="EMP-OVER-1",
        )

        template = OnboardingTemplate.objects.create(
            tenant=tenant,
            name="Overdue Template",
        )
        instance = OnboardingInstance.objects.create(
            tenant=tenant,
            employee=emp,
            template=template,
            start_date=date.today() - timedelta(days=30),
        )
        overdue_date = date.today() - timedelta(days=5)
        OnboardingTask.objects.create(
            tenant=tenant,
            instance=instance,
            title="Complete I-9",
            due_date=overdue_date,
            status='pending',
        )

        result = send_onboarding_task_reminders()
        assert result['sent'] >= 1


# ---------------------------------------------------------------------------
# manager_hub models
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestManagerHubModels:

    def test_team_alert_str(self):
        from manager_hub.models import TeamAlert
        tenant = _make_tenant("MHub", "mhub")
        company = _make_company(tenant)
        manager = _make_employee(tenant, company, number="MGR-1")
        alert = TeamAlert.objects.create(
            tenant=tenant, manager=manager,
            alert_type='probation_due', severity='warning',
            title="Probation review due for EMP-1",
        )
        assert "probation" in str(alert).lower() or "review" in str(alert).lower() or alert.title in str(alert)

    def test_manager_dashboard_config_str(self):
        from manager_hub.models import ManagerDashboardConfig
        tenant = _make_tenant("MHub2", "mhub2")
        company = _make_company(tenant)
        manager = _make_employee(tenant, company, number="MGR-2")
        cfg = ManagerDashboardConfig.objects.create(tenant=tenant, manager=manager)
        assert str(cfg)


# ---------------------------------------------------------------------------
# employee_hub models
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestEmployeeHubModels:

    def test_employee_profile_completion_str(self):
        from employee_hub.models import EmployeeProfileCompletion
        tenant = _make_tenant("EHub", "ehub")
        company = _make_company(tenant)
        emp = _make_employee(tenant, company, number="EMP-HUB-1")
        pc = EmployeeProfileCompletion.objects.create(
            tenant=tenant, employee=emp, overall_pct=75,
        )
        assert "75" in str(pc)

    def test_self_service_request_created(self):
        from employee_hub.models import SelfServiceRequest
        tenant = _make_tenant("EHub2", "ehub2")
        company = _make_company(tenant)
        emp = _make_employee(tenant, company, number="EMP-HUB-2")
        req = SelfServiceRequest.objects.create(
            tenant=tenant, employee=emp,
            request_type='employment_letter',
            subject='Need employment letter',
        )
        assert req.status == 'pending'


# ---------------------------------------------------------------------------
# internal_marketplace models
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestInternalMarketplaceModels:

    def test_internal_job_posting_str(self):
        from internal_marketplace.models import InternalJobPosting
        tenant = _make_tenant("IMP", "imp")
        posting = InternalJobPosting.objects.create(
            tenant=tenant,
            title="Senior Backend Engineer",
            posting_type='full_time',
            description="Lead backend systems",
            open_date=date.today(),
            status='open',
        )
        assert "Senior Backend Engineer" in str(posting)


# ---------------------------------------------------------------------------
# total_rewards models
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTotalRewardsModels:

    def test_compensation_band_str_and_spread(self):
        from total_rewards.models import CompensationBand
        tenant = _make_tenant("TR", "tr")
        band = CompensationBand.objects.create(
            tenant=tenant,
            name="Senior Engineer Band",
            currency="LKR",
            min_salary=Decimal("100000.00"),
            mid_salary=Decimal("130000.00"),
            max_salary=Decimal("160000.00"),
            effective_date=date.today(),
        )
        assert "Senior Engineer Band" in str(band)
        assert band.spread == 60.0  # (160000-100000)/100000*100

    def test_merit_cycle_str(self):
        from total_rewards.models import MeritCycle
        tenant = _make_tenant("TR2", "tr2")
        cycle = MeritCycle.objects.create(
            tenant=tenant,
            name="2025 Annual Merit",
            cycle_year=2025,
            status='planning',
            effective_date=date.today(),
        )
        assert "2025" in str(cycle)


# ---------------------------------------------------------------------------
# employee_relations models
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestEmployeeRelationsModels:

    def test_er_case_created(self):
        from employee_relations.models import ERCase
        tenant = _make_tenant("ER", "er")
        company = _make_company(tenant)
        emp = _make_employee(tenant, company, number="EMP-ER-1")
        case = ERCase.objects.create(
            tenant=tenant,
            case_number="ER-2025-001",
            case_type='grievance',
            severity='moderate',
            subject_employee=emp,
            title="Workplace conflict",
            description="Details of the conflict.",
        )
        assert case.status == 'intake'
        assert "ER-2025-001" in str(case)


# ---------------------------------------------------------------------------
# people_analytics models
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPeopleAnalyticsModels:

    def test_attrition_risk_score_str(self):
        from people_analytics.models import AttritionRiskScore
        tenant = _make_tenant("PA", "pa")
        company = _make_company(tenant)
        emp = _make_employee(tenant, company, number="EMP-PA-1")
        score = AttritionRiskScore.objects.create(
            tenant=tenant,
            employee=emp,
            computed_date=date.today(),
            risk_score=72,
            risk_level='high',
            model_version='v1.0',
        )
        assert "high" in str(score)

    def test_headcount_snapshot_created(self):
        from people_analytics.models import HeadcountSnapshot
        tenant = _make_tenant("PA2", "pa2")
        company = _make_company(tenant)
        snap = HeadcountSnapshot.objects.create(
            tenant=tenant,
            snapshot_date=date.today(),
            company=company,
            headcount=150,
        )
        assert snap.headcount == 150


# ---------------------------------------------------------------------------
# compliance_ai models
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestComplianceAIModels:

    def test_ai_model_str(self):
        from compliance_ai.models import AIModel
        tenant = _make_tenant("CAI", "cai")
        ai = AIModel.objects.create(
            tenant=tenant,
            name="Attrition Predictor",
            model_type='attrition_prediction',
            version='1.0',
        )
        assert "Attrition Predictor" in str(ai)
        assert "1.0" in str(ai)


# ---------------------------------------------------------------------------
# workforce_planning models
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestWorkforcePlanningModels:

    def test_headcount_plan_str(self):
        from workforce_planning.models import HeadcountPlan
        tenant = _make_tenant("WP", "wp")
        company = _make_company(tenant)
        plan = HeadcountPlan.objects.create(
            tenant=tenant,
            name="2025 Engineering HC Plan",
            plan_year=2025,
            company=company,
            planned_headcount=20,
            status='draft',
        )
        assert "2025" in str(plan)


# ---------------------------------------------------------------------------
# documents_policies models
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDocumentsPoliciesModels:

    def test_document_template_str(self):
        from documents_policies.models import DocumentTemplate
        tenant = _make_tenant("DP", "dp")
        tpl = DocumentTemplate.objects.create(
            tenant=tenant,
            name="Offer Letter v2",
            template_type='offer_letter',
            content="Dear {{employee_name}}, welcome!",
        )
        assert "Offer Letter v2" in str(tpl)

    def test_policy_document_created(self):
        from documents_policies.models import PolicyDocument
        tenant = _make_tenant("DP2", "dp2")
        policy = PolicyDocument.objects.create(
            tenant=tenant,
            title="Code of Conduct",
            category='code_of_conduct',
            content="All employees must...",
            version="1.0",
            effective_date=date.today(),
        )
        assert policy.status == 'draft'


# ---------------------------------------------------------------------------
# experience_hub models
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestExperienceHubModels:

    def test_erg_str(self):
        from experience_hub.models import ERG
        tenant = _make_tenant("EXP", "exp")
        company = _make_company(tenant)
        emp = _make_employee(tenant, company, number="EMP-EXP-1")
        erg = ERG.objects.create(
            tenant=tenant,
            name="Women in Tech",
            category='diversity',
            lead=emp,
        )
        assert "Women in Tech" in str(erg)

    def test_erg_membership_created(self):
        from experience_hub.models import ERG, ERGMembership
        tenant = _make_tenant("EXP2", "exp2")
        company = _make_company(tenant)
        emp = _make_employee(tenant, company, number="EMP-EXP-2")
        erg = ERG.objects.create(
            tenant=tenant, name="Wellness Club", category='wellness',
        )
        mem = ERGMembership.objects.create(
            tenant=tenant, erg=erg, employee=emp, role='member',
        )
        assert str(mem)


# ---------------------------------------------------------------------------
# global_workforce models
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestGlobalWorkforceModels:

    def test_country_pack_str(self):
        from global_workforce.models import CountryPack
        tenant = _make_tenant("GW", "gw")
        cp = CountryPack.objects.create(
            tenant=tenant,
            country_code="LK",
            country_name="Sri Lanka",
            currency="LKR",
            timezone="Asia/Colombo",
        )
        assert "Sri Lanka" in str(cp)
        assert "LK" in str(cp)

    def test_multi_currency_rate_created(self):
        from global_workforce.models import MultiCurrencyRate
        tenant = _make_tenant("GW2", "gw2")
        rate = MultiCurrencyRate.objects.create(
            tenant=tenant,
            from_currency="USD",
            to_currency="LKR",
            rate=Decimal("325.50"),
            effective_date=date.today(),
        )
        assert rate.rate == Decimal("325.50")


# ---------------------------------------------------------------------------
# contingent_ops models
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestContingentOpsModels:

    def test_vendor_str(self):
        from contingent_ops.models import Vendor
        tenant = _make_tenant("CO", "co")
        vendor = Vendor.objects.create(
            tenant=tenant,
            name="TechStaff Solutions",
            compliance_status='compliant',
        )
        assert "TechStaff Solutions" in str(vendor)

    def test_contingent_worker_created(self):
        from contingent_ops.models import Vendor, ContingentWorker
        tenant = _make_tenant("CO2", "co2")
        vendor = Vendor.objects.create(tenant=tenant, name="FlexForce")
        worker = ContingentWorker.objects.create(
            tenant=tenant,
            vendor=vendor,
            first_name="John",
            last_name="Contractor",
            worker_type='contractor',
            start_date=date.today(),
        )
        assert str(worker)
