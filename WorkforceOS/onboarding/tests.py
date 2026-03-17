"""
Onboarding tests — template creation, instance lifecycle, task completion,
progress recalculation, and ATS hire-event integration trigger.
"""

import datetime
from django.test import TestCase

from tenants.models import Tenant
from core_hr.models import Company, Employee
from onboarding.models import OnboardingTemplate, OnboardingInstance, OnboardingTask


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tenant(slug='onboard-test'):
    return Tenant.objects.create(name='Onboarding Test Org', slug=slug)


def _make_company(tenant):
    return Company.objects.create(tenant=tenant, name='Onboard Co.', country='LKA', currency='LKR')


def _make_employee(tenant, company, number='EMP001'):
    return Employee.objects.create(
        tenant=tenant, company=company,
        employee_number=number,
        first_name='New', last_name='Hire',
        work_email=f'{number.lower()}@example.com',
        hire_date=datetime.date.today(), status='active',
    )


def _make_template(tenant):
    return OnboardingTemplate.objects.create(
        tenant=tenant,
        name='Standard Onboarding',
        tasks=[
            {'title': 'Setup laptop', 'category': 'it', 'is_required': True, 'due_offset_days': 1},
            {'title': 'Sign contract', 'category': 'hr', 'is_required': True, 'due_offset_days': 1},
            {'title': 'Meet team', 'category': 'manager', 'is_required': False, 'due_offset_days': 3},
        ],
    )


# ---------------------------------------------------------------------------
# OnboardingTemplate tests
# ---------------------------------------------------------------------------

class TestOnboardingTemplate(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('template-test')

    def test_create_template(self):
        template = _make_template(self.tenant)
        self.assertEqual(template.name, 'Standard Onboarding')
        self.assertEqual(len(template.tasks), 3)

    def test_template_default_status_active(self):
        template = _make_template(self.tenant)
        self.assertEqual(template.status, 'active')


# ---------------------------------------------------------------------------
# OnboardingInstance tests
# ---------------------------------------------------------------------------

class TestOnboardingInstance(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('instance-test')
        self.company = _make_company(self.tenant)
        self.employee = _make_employee(self.tenant, self.company)
        self.template = _make_template(self.tenant)

    def test_create_instance(self):
        instance = OnboardingInstance.objects.create(
            tenant=self.tenant, employee=self.employee,
            template=self.template,
            start_date=datetime.date.today(),
        )
        self.assertEqual(instance.status, 'in_progress')
        self.assertEqual(instance.completion_pct, 0)

    def test_default_completion_zero(self):
        instance = OnboardingInstance.objects.create(
            tenant=self.tenant, employee=self.employee,
            template=self.template, start_date=datetime.date.today(),
        )
        self.assertEqual(instance.completion_pct, 0)


# ---------------------------------------------------------------------------
# OnboardingTask & progress recalculation tests
# ---------------------------------------------------------------------------

class TestOnboardingProgress(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('progress-test')
        self.company = _make_company(self.tenant)
        self.employee = _make_employee(self.tenant, self.company)
        self.template = _make_template(self.tenant)
        self.instance = OnboardingInstance.objects.create(
            tenant=self.tenant, employee=self.employee,
            template=self.template, start_date=datetime.date.today(),
        )

    def _add_task(self, title='Task', status='pending'):
        return OnboardingTask.objects.create(
            tenant=self.tenant, instance=self.instance,
            title=title, category='hr', status=status,
        )

    def test_progress_zero_with_no_tasks(self):
        self.instance.recalculate_progress()
        self.instance.refresh_from_db()
        self.assertEqual(self.instance.completion_pct, 0)

    def test_progress_fifty_percent(self):
        self._add_task('Task 1', 'completed')
        self._add_task('Task 2', 'pending')
        self.instance.recalculate_progress()
        self.instance.refresh_from_db()
        self.assertEqual(self.instance.completion_pct, 50)

    def test_progress_one_hundred_all_completed(self):
        self._add_task('Task A', 'completed')
        self._add_task('Task B', 'completed')
        self.instance.recalculate_progress()
        self.instance.refresh_from_db()
        self.assertEqual(self.instance.completion_pct, 100)

    def test_complete_instance_status(self):
        task = self._add_task('Only Task', 'completed')
        self.instance.recalculate_progress()
        self.instance.status = 'completed'
        self.instance.save()
        self.instance.refresh_from_db()
        self.assertEqual(self.instance.status, 'completed')
        self.assertEqual(self.instance.completion_pct, 100)

    def test_task_default_status_pending(self):
        task = self._add_task('Pending Task')
        self.assertEqual(task.status, 'pending')


# ---------------------------------------------------------------------------
# ATS integration signal test
# ---------------------------------------------------------------------------

class TestOnboardingAutoTrigger(TestCase):
    """
    When an employee is hired (created from an ATS candidate),
    the system should be able to auto-trigger an onboarding instance.
    This tests the core logic independently of signal wiring.
    """
    def setUp(self):
        self.tenant = _make_tenant('auto-trigger-test')
        self.company = _make_company(self.tenant)
        self.template = _make_template(self.tenant)

    def test_can_create_onboarding_on_hire(self):
        """Simulates what happens when an employee is hired."""
        employee = _make_employee(self.tenant, self.company, 'NEW001')
        instance = OnboardingInstance.objects.create(
            tenant=self.tenant, employee=employee,
            template=self.template,
            start_date=employee.hire_date,
        )
        self.assertIsNotNone(instance.pk)
        self.assertEqual(instance.employee, employee)
        self.assertEqual(instance.template, self.template)
