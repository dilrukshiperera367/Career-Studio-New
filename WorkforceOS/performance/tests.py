"""
Performance tests — ReviewCycle lifecycle, PerformanceReview creation,
rating constraints, Goal creation and progress tracking,
and unique-review-per-cycle constraint.
"""

import datetime
from decimal import Decimal
from django.test import TestCase

from tenants.models import Tenant
from core_hr.models import Company, Employee
from performance.models import ReviewCycle, PerformanceReview, Goal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tenant(slug='perf-test'):
    return Tenant.objects.create(name='Performance Test Org', slug=slug)


def _make_company(tenant):
    return Company.objects.create(tenant=tenant, name='Perf Co.', country='LKA', currency='LKR')


def _make_employee(tenant, company, number='EMP001'):
    return Employee.objects.create(
        tenant=tenant, company=company,
        employee_number=number,
        first_name='Bob', last_name='Jones',
        work_email=f'{number.lower()}@example.com',
        hire_date='2022-01-01', status='active',
    )


def _make_cycle(tenant, name='Annual Review 2024'):
    return ReviewCycle.objects.create(
        tenant=tenant, name=name, type='annual',
        start_date='2024-01-01', end_date='2024-12-31',
    )


# ---------------------------------------------------------------------------
# ReviewCycle tests
# ---------------------------------------------------------------------------

class TestReviewCycle(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('cycle-test')

    def test_create_cycle(self):
        cycle = _make_cycle(self.tenant)
        self.assertEqual(cycle.type, 'annual')
        self.assertEqual(cycle.status, 'draft')

    def test_cycle_status_transitions(self):
        cycle = _make_cycle(self.tenant)
        cycle.status = 'active'
        cycle.save()
        cycle.refresh_from_db()
        self.assertEqual(cycle.status, 'active')


# ---------------------------------------------------------------------------
# PerformanceReview tests
# ---------------------------------------------------------------------------

class TestPerformanceReview(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('review-test')
        self.company = _make_company(self.tenant)
        self.employee = _make_employee(self.tenant, self.company)
        self.cycle = _make_cycle(self.tenant)

    def test_create_review(self):
        review = PerformanceReview.objects.create(
            tenant=self.tenant, cycle=self.cycle, employee=self.employee,
        )
        self.assertEqual(review.status, 'pending')

    def test_unique_review_per_cycle(self):
        """Same employee cannot have two reviews in the same cycle."""
        PerformanceReview.objects.create(
            tenant=self.tenant, cycle=self.cycle, employee=self.employee,
        )
        with self.assertRaises(Exception):
            PerformanceReview.objects.create(
                tenant=self.tenant, cycle=self.cycle, employee=self.employee,
            )

    def test_self_rating_stored(self):
        review = PerformanceReview.objects.create(
            tenant=self.tenant, cycle=self.cycle, employee=self.employee,
            self_rating=Decimal('4.0'), status='self_submitted',
        )
        review.refresh_from_db()
        self.assertEqual(review.self_rating, Decimal('4.0'))
        self.assertEqual(review.status, 'self_submitted')

    def test_final_rating_after_calibration(self):
        review = PerformanceReview.objects.create(
            tenant=self.tenant, cycle=self.cycle, employee=self.employee,
            self_rating=Decimal('4.0'), manager_rating=Decimal('3.5'),
            final_rating=Decimal('3.8'), status='finalized',
        )
        self.assertEqual(review.status, 'finalized')
        self.assertAlmostEqual(float(review.final_rating), 3.8, places=1)


# ---------------------------------------------------------------------------
# Goal tests
# ---------------------------------------------------------------------------

class TestGoal(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('goal-test')
        self.company = _make_company(self.tenant)
        self.employee = _make_employee(self.tenant, self.company)
        self.cycle = _make_cycle(self.tenant)

    def test_create_goal(self):
        goal = Goal.objects.create(
            tenant=self.tenant, employee=self.employee,
            cycle=self.cycle,
            title='Improve test coverage to 80%',
            due_date='2024-12-31',
        )
        self.assertIsNotNone(goal.pk)

    def test_goal_default_status(self):
        goal = Goal.objects.create(
            tenant=self.tenant, employee=self.employee,
            title='New Goal', due_date='2024-06-30',
        )
        # Status should be 'active' or 'not_started' by default
        self.assertIn(goal.status, ['active', 'not_started', 'pending', 'draft'])

    def test_goal_progress_update(self):
        goal = Goal.objects.create(
            tenant=self.tenant, employee=self.employee,
            title='Progress Goal', due_date='2024-12-31',
        )
        goal.progress = 50
        goal.save()
        goal.refresh_from_db()
        self.assertEqual(goal.progress, 50)

    def test_parent_child_goals(self):
        parent = Goal.objects.create(
            tenant=self.tenant, employee=self.employee,
            title='Parent Goal', due_date='2024-12-31',
        )
        child = Goal.objects.create(
            tenant=self.tenant, employee=self.employee,
            title='Child Goal', due_date='2024-06-30',
            parent_goal=parent,
        )
        self.assertEqual(child.parent_goal, parent)
        self.assertIn(child, parent.sub_goals.all())
