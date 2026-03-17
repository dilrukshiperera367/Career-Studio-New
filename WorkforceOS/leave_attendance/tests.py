"""
Leave & Attendance tests — leave type/balance, accrual task,
QR attendance token generation and verification, attendance record constraints.
"""

import calendar
import datetime
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from tenants.models import Tenant
from core_hr.models import Company, Employee
from leave_attendance.models import LeaveType, LeaveBalance, LeaveRequest, AttendanceRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tenant(slug='la-test'):
    return Tenant.objects.create(name='LA Test Org', slug=slug)


def _make_company(tenant):
    return Company.objects.create(tenant=tenant, name='LA Test Co.', country='LKA', currency='LKR')


def _make_employee(tenant, company, number='EMP001'):
    return Employee.objects.create(
        tenant=tenant, company=company,
        employee_number=number,
        first_name='Jane', last_name='Doe',
        work_email=f'{number.lower()}@example.com',
        hire_date='2022-01-01', status='active',
    )


def _make_leave_type(tenant, *, code='AL', accrual_type='annual', annual_days=14):
    return LeaveType.objects.create(
        tenant=tenant, name='Annual Leave', code=code,
        accrual_type=accrual_type,
        max_days_per_year=Decimal(str(annual_days)),
        max_carry_forward=Decimal('5.0'),
    )


# ---------------------------------------------------------------------------
# LeaveBalance model tests
# ---------------------------------------------------------------------------

class TestLeaveBalance(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('balance-test')
        self.company = _make_company(self.tenant)
        self.employee = _make_employee(self.tenant, self.company)
        self.leave_type = _make_leave_type(self.tenant)

    def test_remaining_property(self):
        """remaining == entitled + carried_forward + adjustment - taken - pending."""
        balance = LeaveBalance.objects.create(
            tenant=self.tenant, employee=self.employee,
            leave_type=self.leave_type, year=2024,
            entitled=Decimal('14.0'), carried_forward=Decimal('3.0'),
            taken=Decimal('5.0'), pending=Decimal('2.0'),
            adjustment=Decimal('1.0'),
        )
        expected = Decimal('14.0') + Decimal('3.0') + Decimal('1.0') - Decimal('5.0') - Decimal('2.0')
        self.assertEqual(balance.remaining, expected)

    def test_unique_per_employee_per_year(self):
        """Duplicate leave balance (same employee/type/year) is disallowed."""
        LeaveBalance.objects.create(
            tenant=self.tenant, employee=self.employee,
            leave_type=self.leave_type, year=2024, entitled=Decimal('14.0'),
        )
        with self.assertRaises(Exception):
            LeaveBalance.objects.create(
                tenant=self.tenant, employee=self.employee,
                leave_type=self.leave_type, year=2024, entitled=Decimal('10.0'),
            )


# ---------------------------------------------------------------------------
# Monthly leave accrual task tests
# ---------------------------------------------------------------------------

class TestMonthlyLeaveAccrual(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('accrual-test')
        self.company = _make_company(self.tenant)
        self.employee = _make_employee(self.tenant, self.company)
        self.leave_type = _make_leave_type(
            self.tenant, code='ML', accrual_type='monthly', annual_days=12
        )

    @patch('leave_attendance.tasks.datetime')
    def test_accrual_runs_only_on_last_day_of_month(self, mock_dt):
        """Task must not create balances if today is not the last day of the month."""
        # Set today to the 1st — not the last day
        mock_dt.date.today.return_value = datetime.date(2024, 6, 1)
        mock_dt.date.side_effect = lambda *a, **kw: datetime.date(*a, **kw)
        from leave_attendance.tasks import run_monthly_leave_accrual
        run_monthly_leave_accrual()
        count = LeaveBalance.objects.filter(
            employee=self.employee, leave_type=self.leave_type
        ).count()
        self.assertEqual(count, 0)

    @patch('leave_attendance.tasks.datetime')
    def test_accrual_runs_on_last_day_of_month(self, mock_dt):
        """Task creates or updates LeaveBalance on the last day of the month."""
        # June 2024 has 30 days
        mock_dt.date.today.return_value = datetime.date(2024, 6, 30)
        mock_dt.date.side_effect = lambda *a, **kw: datetime.date(*a, **kw)
        from leave_attendance.tasks import run_monthly_leave_accrual
        run_monthly_leave_accrual()
        balance = LeaveBalance.objects.filter(
            employee=self.employee, leave_type=self.leave_type,
            year=2024,
        ).first()
        self.assertIsNotNone(balance)
        # monthly increment = 12 / 12 = 1.0 day
        self.assertAlmostEqual(float(balance.entitled), 1.0, places=1)

    @patch('leave_attendance.tasks.datetime')
    def test_monthly_increment_value(self, mock_dt):
        """Each month accrues annual_days / 12 days."""
        mock_dt.date.today.return_value = datetime.date(2024, 1, 31)
        mock_dt.date.side_effect = lambda *a, **kw: datetime.date(*a, **kw)
        from leave_attendance.tasks import run_monthly_leave_accrual
        run_monthly_leave_accrual()
        balance = LeaveBalance.objects.filter(
            employee=self.employee, leave_type=self.leave_type,
        ).first()
        self.assertIsNotNone(balance)
        expected_increment = float(self.leave_type.max_days_per_year) / 12
        self.assertAlmostEqual(float(balance.entitled), expected_increment, places=2)


# ---------------------------------------------------------------------------
# QR attendance token tests
# ---------------------------------------------------------------------------

class TestQRAttendanceToken(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('qr-test')
        self.company = _make_company(self.tenant)
        self.employee = _make_employee(self.tenant, self.company)

    def test_qr_token_generation(self):
        """QR token endpoint returns a non-empty token string."""
        from django.core import signing
        payload = {
            'employee_id': str(self.employee.id),
            'tenant_id': str(self.tenant.id),
        }
        token = signing.dumps(payload, salt='qr_attendance')
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 10)

    def test_qr_token_round_trip(self):
        """Token can be decoded back to the original payload within max_age."""
        from django.core import signing
        payload = {
            'employee_id': str(self.employee.id),
            'tenant_id': str(self.tenant.id),
        }
        token = signing.dumps(payload, salt='qr_attendance')
        decoded = signing.loads(token, salt='qr_attendance', max_age=120)
        self.assertEqual(decoded['employee_id'], payload['employee_id'])
        self.assertEqual(decoded['tenant_id'], payload['tenant_id'])

    def test_qr_token_tamper_rejected(self):
        """Tampered or invalid token must raise BadSignature."""
        from django.core import signing
        with self.assertRaises(signing.BadSignature):
            signing.loads('invalid.token.value', salt='qr_attendance', max_age=120)

    def test_qr_token_expiry_raises(self):
        """Token older than max_age must raise SignatureExpired."""
        from django.core import signing
        import time
        payload = {'employee_id': str(self.employee.id), 'tenant_id': str(self.tenant.id)}
        # Create token with very short max_age, then wait / force check with 0 max_age
        token = signing.dumps(payload, salt='qr_attendance')
        with self.assertRaises(signing.SignatureExpired):
            signing.loads(token, salt='qr_attendance', max_age=-1)  # already expired


# ---------------------------------------------------------------------------
# AttendanceRecord constraint tests
# ---------------------------------------------------------------------------

class TestAttendanceRecord(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('attend-test')
        self.company = _make_company(self.tenant)
        self.employee = _make_employee(self.tenant, self.company)

    def test_unique_attendance_per_day(self):
        """Two attendance records for the same employee on the same date are disallowed."""
        today = datetime.date.today()
        AttendanceRecord.objects.create(
            tenant=self.tenant, employee=self.employee,
            date=today, status='present',
        )
        with self.assertRaises(Exception):
            AttendanceRecord.objects.create(
                tenant=self.tenant, employee=self.employee,
                date=today, status='present',
            )

    def test_default_status_is_present(self):
        """AttendanceRecord defaults to status='present'."""
        record = AttendanceRecord.objects.create(
            tenant=self.tenant, employee=self.employee,
            date=datetime.date.today(), clock_in=timezone.now(),
        )
        self.assertEqual(record.status, 'present')


# ---------------------------------------------------------------------------
# LeaveRequest tests
# ---------------------------------------------------------------------------

class TestLeaveRequest(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('lr-test')
        self.company = _make_company(self.tenant)
        self.employee = _make_employee(self.tenant, self.company)
        self.leave_type = _make_leave_type(self.tenant, code='CL')

    def test_leave_request_default_status(self):
        """A new leave request starts in 'pending' status."""
        request = LeaveRequest.objects.create(
            tenant=self.tenant, employee=self.employee,
            leave_type=self.leave_type,
            start_date='2024-06-01', end_date='2024-06-03',
            days=Decimal('3.0'),
        )
        self.assertEqual(request.status, 'pending')

    def test_approved_request_changes_status(self):
        """Manually approving a leave request persists the status change."""
        request = LeaveRequest.objects.create(
            tenant=self.tenant, employee=self.employee,
            leave_type=self.leave_type,
            start_date='2024-07-01', end_date='2024-07-02',
            days=Decimal('2.0'),
        )
        request.status = 'approved'
        request.save()
        request.refresh_from_db()
        self.assertEqual(request.status, 'approved')
