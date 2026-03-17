"""
Platform Core tests — AuditLog creation, TimelineEvent recording,
approval workflow, and notification queuing.
"""

import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model

from tenants.models import Tenant
from core_hr.models import Company, Employee
from platform_core.models import AuditLog, TimelineEvent

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tenant(slug='platform-core-test'):
    return Tenant.objects.create(name='Platform Core Test Org', slug=slug)


def _make_company(tenant):
    return Company.objects.create(tenant=tenant, name='Platform Co.', country='LKA', currency='LKR')


def _make_employee(tenant, company, number='EMP001'):
    return Employee.objects.create(
        tenant=tenant, company=company,
        employee_number=number,
        first_name='Core', last_name='User',
        work_email=f'{number.lower()}@example.com',
        hire_date='2023-01-01', status='active',
    )


def _make_user(tenant):
    return User.objects.create_user(
        email='admin@platform-test.com',
        tenant_id=tenant.id,
        first_name='Admin', last_name='User',
    )


# ---------------------------------------------------------------------------
# AuditLog tests
# ---------------------------------------------------------------------------

class TestAuditLog(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('audit-test')
        self.company = _make_company(self.tenant)
        self.employee = _make_employee(self.tenant, self.company)
        self.user = _make_user(self.tenant)

    def test_create_audit_log(self):
        entry = AuditLog.objects.create(
            tenant=self.tenant,
            user=self.user,
            action='employee.created',
            entity_type='Employee',
            entity_id=self.employee.id,
            changes={'status': {'old': None, 'new': 'active'}},
        )
        self.assertEqual(entry.action, 'employee.created')
        self.assertEqual(entry.entity_type, 'Employee')

    def test_audit_log_immutable_no_updated_at(self):
        """AuditLog has no updated_at field — it's immutable."""
        entry = AuditLog.objects.create(
            tenant=self.tenant,
            action='leave.approved',
            entity_type='LeaveRequest',
            entity_id=uuid.uuid4(),
        )
        self.assertTrue(hasattr(entry, 'created_at'))
        self.assertFalse(hasattr(entry, 'updated_at'))

    def test_audit_log_ordered_newest_first(self):
        """AuditLog is ordered by -created_at."""
        AuditLog.objects.create(
            tenant=self.tenant, action='event.first',
            entity_type='Employee', entity_id=self.employee.id,
        )
        AuditLog.objects.create(
            tenant=self.tenant, action='event.second',
            entity_type='Employee', entity_id=self.employee.id,
        )
        latest = AuditLog.objects.filter(tenant=self.tenant).first()
        self.assertEqual(latest.action, 'event.second')

    def test_audit_log_tenant_scoped(self):
        other_tenant = _make_tenant('other-platform')
        other_company = _make_company(other_tenant)
        other_emp = _make_employee(other_tenant, other_company, 'O001')
        AuditLog.objects.create(
            tenant=self.tenant, action='employee.created',
            entity_type='Employee', entity_id=self.employee.id,
        )
        AuditLog.objects.create(
            tenant=other_tenant, action='employee.created',
            entity_type='Employee', entity_id=other_emp.id,
        )
        self.assertEqual(AuditLog.objects.filter(tenant=self.tenant).count(), 1)
        self.assertEqual(AuditLog.objects.filter(tenant=other_tenant).count(), 1)


# ---------------------------------------------------------------------------
# TimelineEvent tests
# ---------------------------------------------------------------------------

class TestTimelineEvent(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('timeline-test')
        self.company = _make_company(self.tenant)
        self.employee = _make_employee(self.tenant, self.company)

    def test_create_timeline_event(self):
        event = TimelineEvent.objects.create(
            tenant=self.tenant,
            employee=self.employee,
            event_type='employee.created',
            category='hr',
            title='Employee hired',
        )
        self.assertEqual(event.event_type, 'employee.created')
        self.assertEqual(event.category, 'hr')

    def test_timeline_events_per_employee(self):
        TimelineEvent.objects.create(
            tenant=self.tenant, employee=self.employee,
            event_type='leave.approved', category='leave', title='Leave approved',
        )
        TimelineEvent.objects.create(
            tenant=self.tenant, employee=self.employee,
            event_type='payroll.payslip_generated', category='payroll', title='Payslip generated',
        )
        self.assertEqual(
            TimelineEvent.objects.filter(employee=self.employee).count(), 2
        )

    def test_system_actor_type(self):
        event = TimelineEvent.objects.create(
            tenant=self.tenant, employee=self.employee,
            event_type='system.auto', category='system', title='Auto action',
            actor_type='system',
        )
        self.assertEqual(event.actor_type, 'system')
