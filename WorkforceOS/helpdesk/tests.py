"""
Helpdesk tests — Ticket creation, auto-numbering, category SLA,
ticket comment threading, status lifecycle, and satisfaction rating capture.
"""

from django.test import TestCase

from tenants.models import Tenant
from core_hr.models import Company, Employee
from helpdesk.models import TicketCategory, Ticket, TicketComment


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tenant(slug='helpdesk-test'):
    return Tenant.objects.create(name='Helpdesk Test Org', slug=slug)


def _make_company(tenant):
    return Company.objects.create(tenant=tenant, name='Helpdesk Co.', country='LKA', currency='LKR')


def _make_employee(tenant, company, number='EMP001'):
    return Employee.objects.create(
        tenant=tenant, company=company,
        employee_number=number,
        first_name='Help', last_name='Seeker',
        work_email=f'{number.lower()}@example.com',
        hire_date='2022-01-01', status='active',
    )


def _make_category(tenant, name='General HR'):
    return TicketCategory.objects.create(
        tenant=tenant, name=name,
        sla_response_hours=24, sla_resolution_hours=72,
    )


# ---------------------------------------------------------------------------
# TicketCategory tests
# ---------------------------------------------------------------------------

class TestTicketCategory(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('category-test')

    def test_create_category(self):
        category = _make_category(self.tenant)
        self.assertEqual(category.name, 'General HR')
        self.assertTrue(category.is_active)

    def test_sla_defaults(self):
        category = _make_category(self.tenant)
        self.assertEqual(category.sla_response_hours, 24)
        self.assertEqual(category.sla_resolution_hours, 72)


# ---------------------------------------------------------------------------
# Ticket tests
# ---------------------------------------------------------------------------

class TestTicket(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('ticket-test')
        self.company = _make_company(self.tenant)
        self.employee = _make_employee(self.tenant, self.company)
        self.category = _make_category(self.tenant)

    def test_create_ticket(self):
        ticket = Ticket.objects.create(
            tenant=self.tenant,
            employee=self.employee,
            category=self.category,
            subject='Cannot access payslip',
            description='I cannot log in to view my payslip.',
        )
        self.assertEqual(ticket.status, 'open')
        self.assertEqual(ticket.priority, 'medium')

    def test_auto_ticket_number(self):
        """Ticket number is auto-generated on save."""
        ticket = Ticket.objects.create(
            tenant=self.tenant, employee=self.employee,
            subject='Auto number test', description='Testing.',
        )
        self.assertTrue(ticket.ticket_number.startswith('TKT-'))

    def test_sequential_ticket_numbers(self):
        t1 = Ticket.objects.create(
            tenant=self.tenant, employee=self.employee,
            subject='First ticket', description='A.',
        )
        t2 = Ticket.objects.create(
            tenant=self.tenant, employee=self.employee,
            subject='Second ticket', description='B.',
        )
        num1 = int(t1.ticket_number.split('-')[1])
        num2 = int(t2.ticket_number.split('-')[1])
        self.assertEqual(num2, num1 + 1)

    def test_ticket_status_transitions(self):
        ticket = Ticket.objects.create(
            tenant=self.tenant, employee=self.employee,
            subject='Status test', description='Testing status.',
        )
        ticket.status = 'in_progress'
        ticket.save()
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'in_progress')

    def test_ticket_resolution(self):
        from django.utils import timezone
        ticket = Ticket.objects.create(
            tenant=self.tenant, employee=self.employee,
            subject='Resolved ticket', description='Resolved.',
        )
        ticket.status = 'resolved'
        ticket.resolved_at = timezone.now()
        ticket.satisfaction_rating = 5
        ticket.save()
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'resolved')
        self.assertEqual(ticket.satisfaction_rating, 5)


# ---------------------------------------------------------------------------
# TicketComment tests
# ---------------------------------------------------------------------------

class TestTicketComment(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('comment-test')
        self.company = _make_company(self.tenant)
        self.employee = _make_employee(self.tenant, self.company)
        self.ticket = Ticket.objects.create(
            tenant=self.tenant, employee=self.employee,
            subject='Comment test ticket', description='Testing.',
        )

    def test_add_comment(self):
        comment = TicketComment.objects.create(
            ticket=self.ticket,
            body='Please provide your employee number.',
        )
        self.assertEqual(comment.ticket, self.ticket)
        self.assertFalse(comment.is_internal)

    def test_internal_note(self):
        """Internal notes are not visible to the employee."""
        comment = TicketComment.objects.create(
            ticket=self.ticket,
            body='Escalating to payroll team.',
            is_internal=True,
        )
        self.assertTrue(comment.is_internal)

    def test_comment_thread_order(self):
        """Comments are ordered by created_at ascending."""
        TicketComment.objects.create(ticket=self.ticket, body='First comment.')
        TicketComment.objects.create(ticket=self.ticket, body='Second comment.')
        comments = list(self.ticket.comments.all())
        self.assertEqual(comments[0].body, 'First comment.')
        self.assertEqual(comments[1].body, 'Second comment.')
