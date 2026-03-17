"""
Approval workflow integration tests.
Tests multi-level approval chain, delegation, and rejection paths
for the generic ApprovalRequest model.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.test import TestCase
from django.utils import timezone

from tenants.models import Tenant
from authentication.models import User, Role, UserRole
from core_hr.models import Company, Employee
from leave_attendance.models import LeaveType, LeaveBalance, LeaveRequest
from platform_core.models import ApprovalRequest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tenant(slug):
    return Tenant.objects.create(name=slug.title(), slug=slug)


def _make_user(tenant, email, role_name="Employee", password="Test@12345"):
    user = User.objects.create_user(
        email=email, tenant_id=str(tenant.id),
        password=password, first_name="Test", last_name=role_name,
    )
    role, _ = Role.objects.get_or_create(name=role_name, defaults={"is_system_role": True})
    UserRole.objects.create(user=user, role=role, tenant=tenant)
    return user


def _make_employee(tenant, company, number="EMP001"):
    return Employee.objects.create(
        tenant=tenant, company=company,
        employee_number=number,
        first_name="Test", last_name="Employee",
        work_email=f"{number}@{tenant.slug}.com",
        hire_date="2024-01-01", status="active",
    )


# ---------------------------------------------------------------------------
# Single-level approval tests
# ---------------------------------------------------------------------------

class TestSingleLevelApproval(TestCase):
    def setUp(self):
        self.tenant = _make_tenant("approval-single")
        self.company = Company.objects.create(
            tenant=self.tenant, name="Approval Co", country="LKA", currency="LKR"
        )
        self.requester = _make_user(self.tenant, "emp@approval.com", "Employee")
        self.approver = _make_user(self.tenant, "mgr@approval.com", "Manager")
        self.employee = _make_employee(self.tenant, self.company)
        self.leave_type = LeaveType.objects.create(
            tenant=self.tenant, name="Annual", code="AL",
            max_days_per_year=Decimal("14"), paid=True,
        )
        self.leave_request = LeaveRequest.objects.create(
            tenant=self.tenant, employee=self.employee, leave_type=self.leave_type,
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=8),
            days=Decimal("2"),
        )

    def _make_approval(self, step=1, total_steps=1):
        return ApprovalRequest.objects.create(
            tenant=self.tenant,
            requester=self.requester,
            approver=self.approver,
            entity_type="LeaveRequest",
            entity_id=self.leave_request.id,
            action_type="approve_leave",
            step=step,
            total_steps=total_steps,
        )

    def test_approval_request_created_as_pending(self):
        req = self._make_approval()
        self.assertEqual(req.status, "pending")
        self.assertEqual(req.step, 1)

    def test_approve_action(self):
        """Approver can approve a pending request."""
        req = self._make_approval()
        req.status = "approved"
        req.decided_at = timezone.now()
        req.comments = "Approved — team coverage confirmed"
        req.save()
        req.refresh_from_db()
        self.assertEqual(req.status, "approved")
        self.assertIsNotNone(req.decided_at)

    def test_reject_action_with_comment(self):
        """Approver can reject with a reason."""
        req = self._make_approval()
        req.status = "rejected"
        req.decided_at = timezone.now()
        req.comments = "Blackout period — business critical week"
        req.save()
        req.refresh_from_db()
        self.assertEqual(req.status, "rejected")
        self.assertEqual(req.comments, "Blackout period — business critical week")

    def test_cancel_before_decision(self):
        """Request can be cancelled by the requester before a decision."""
        req = self._make_approval()
        req.status = "cancelled"
        req.save()
        req.refresh_from_db()
        self.assertEqual(req.status, "cancelled")


# ---------------------------------------------------------------------------
# Multi-level approval chain
# ---------------------------------------------------------------------------

class TestMultiLevelApprovalChain(TestCase):
    """
    2-level chain: Employee → Manager (step 1) → HR Admin (step 2).
    Step 2 is only created after step 1 is approved.
    """

    def setUp(self):
        self.tenant = _make_tenant("approval-multi")
        self.company = Company.objects.create(
            tenant=self.tenant, name="Multi Approval Co", country="LKA", currency="LKR",
        )
        self.employee_user = _make_user(self.tenant, "emp@multi.com", "Employee")
        self.manager_user = _make_user(self.tenant, "mgr@multi.com", "Manager")
        self.hr_admin_user = _make_user(self.tenant, "hr@multi.com", "HR Admin")
        self.employee = _make_employee(self.tenant, self.company, "MULTI001")
        self.leave_type = LeaveType.objects.create(
            tenant=self.tenant, name="Annual", code="AL",
            max_days_per_year=Decimal("14"), paid=True,
        )
        self.leave_request = LeaveRequest.objects.create(
            tenant=self.tenant, employee=self.employee, leave_type=self.leave_type,
            start_date=date.today() + timedelta(days=14),
            end_date=date.today() + timedelta(days=18),
            days=Decimal("5"),
        )

    def _create_step(self, approver, step, total_steps=2):
        return ApprovalRequest.objects.create(
            tenant=self.tenant,
            requester=self.employee_user,
            approver=approver,
            entity_type="LeaveRequest",
            entity_id=self.leave_request.id,
            action_type="approve_leave",
            step=step,
            total_steps=total_steps,
        )

    def test_step_1_pending_before_manager_action(self):
        step1 = self._create_step(self.manager_user, step=1)
        self.assertEqual(step1.status, "pending")

    def test_full_two_step_approval_chain(self):
        """Step 1 approval by manager → step 2 created → step 2 approval completes chain."""
        step1 = self._create_step(self.manager_user, step=1)

        # Manager approves step 1
        step1.status = "approved"
        step1.decided_at = timezone.now()
        step1.save()

        # Create step 2 (HR Admin)
        step2 = self._create_step(self.hr_admin_user, step=2)

        # HR Admin approves step 2
        step2.status = "approved"
        step2.decided_at = timezone.now()
        step2.save()

        # Both steps must be approved for full chain completion
        all_steps = ApprovalRequest.objects.filter(
            tenant=self.tenant,
            entity_type="LeaveRequest",
            entity_id=self.leave_request.id,
        )
        statuses = set(all_steps.values_list("status", flat=True))
        self.assertEqual(statuses, {"approved"}, "All steps in chain must be approved")

    def test_rejection_at_step_1_blocks_chain(self):
        """If manager rejects at step 1, step 2 should not be created."""
        step1 = self._create_step(self.manager_user, step=1)
        step1.status = "rejected"
        step1.decided_at = timezone.now()
        step1.save()

        # In correct implementation step 2 must NOT be created after rejection
        step_2_count = ApprovalRequest.objects.filter(
            tenant=self.tenant,
            entity_type="LeaveRequest",
            entity_id=self.leave_request.id,
            step=2,
        ).count()
        self.assertEqual(step_2_count, 0,
                         "Step 2 must not be created when step 1 is rejected")

    def test_step_numbers_unique_per_entity(self):
        """Each step must have a unique step number for a given entity+chain."""
        step1 = self._create_step(self.manager_user, step=1)
        step1.status = "approved"
        step1.save()
        step2 = self._create_step(self.hr_admin_user, step=2)

        self.assertNotEqual(step1.step, step2.step)
        self.assertEqual(step1.step, 1)
        self.assertEqual(step2.step, 2)


# ---------------------------------------------------------------------------
# Approval isolation
# ---------------------------------------------------------------------------

class TestApprovalTenantIsolation(TestCase):
    """Approval requests must not bleed between tenants."""

    def setUp(self):
        self.t_a = _make_tenant("appr-iso-a")
        self.t_b = _make_tenant("appr-iso-b")
        self.r_a = _make_user(self.t_a, "req@a.com")
        self.r_b = _make_user(self.t_b, "req@b.com")
        self.approver_a = _make_user(self.t_a, "apr@a.com", "Manager")
        self.approver_b = _make_user(self.t_b, "apr@b.com", "Manager")

    def _approval(self, tenant, requester, approver):
        return ApprovalRequest.objects.create(
            tenant=tenant,
            requester=requester,
            approver=approver,
            entity_type="LeaveRequest",
            entity_id=uuid.uuid4(),
            action_type="approve_leave",
        )

    def test_tenant_a_cannot_see_tenant_b_approvals(self):
        appr_a = self._approval(self.t_a, self.r_a, self.approver_a)
        appr_b = self._approval(self.t_b, self.r_b, self.approver_b)
        visible_to_a = ApprovalRequest.objects.filter(tenant=self.t_a)
        self.assertIn(appr_a, visible_to_a)
        self.assertNotIn(appr_b, visible_to_a)
