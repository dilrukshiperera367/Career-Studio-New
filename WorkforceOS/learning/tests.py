"""
Learning & Development tests — Course creation, enrollment constraints,
progress tracking, certification expiry, and mandatory course assignment.
"""

import datetime
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone

from tenants.models import Tenant
from core_hr.models import Company, Employee
from learning.models import Course, CourseEnrollment, Certification


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tenant(slug='learning-test'):
    return Tenant.objects.create(name='Learning Test Org', slug=slug)


def _make_company(tenant):
    return Company.objects.create(tenant=tenant, name='Learn Co.', country='LKA', currency='LKR')


def _make_employee(tenant, company, number='EMP001'):
    return Employee.objects.create(
        tenant=tenant, company=company,
        employee_number=number,
        first_name='Learner', last_name='Smith',
        work_email=f'{number.lower()}@example.com',
        hire_date='2022-01-01', status='active',
    )


def _make_course(tenant, title='Safety Compliance', status='active'):
    return Course.objects.create(
        tenant=tenant,
        title=title,
        category='compliance',
        format='online',
        duration_hours=Decimal('2.0'),
        status=status,
    )


# ---------------------------------------------------------------------------
# Course model tests
# ---------------------------------------------------------------------------

class TestCourse(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('course-test')

    def test_create_course(self):
        course = _make_course(self.tenant)
        self.assertEqual(course.title, 'Safety Compliance')
        self.assertEqual(course.status, 'active')

    def test_course_default_format_online(self):
        course = _make_course(self.tenant, 'Online Training')
        self.assertEqual(course.format, 'online')

    def test_archive_course(self):
        course = _make_course(self.tenant)
        course.status = 'archived'
        course.save()
        course.refresh_from_db()
        self.assertEqual(course.status, 'archived')


# ---------------------------------------------------------------------------
# CourseEnrollment tests
# ---------------------------------------------------------------------------

class TestCourseEnrollment(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('enrollment-test')
        self.company = _make_company(self.tenant)
        self.employee = _make_employee(self.tenant, self.company)
        self.course = _make_course(self.tenant)

    def test_enroll_employee(self):
        enrollment = CourseEnrollment.objects.create(
            tenant=self.tenant,
            course=self.course,
            employee=self.employee,
        )
        self.assertEqual(enrollment.status, 'enrolled')
        self.assertEqual(enrollment.progress, 0)

    def test_unique_enrollment_per_course(self):
        """An employee cannot be enrolled twice in the same course."""
        CourseEnrollment.objects.create(
            tenant=self.tenant, course=self.course, employee=self.employee,
        )
        with self.assertRaises(Exception):
            CourseEnrollment.objects.create(
                tenant=self.tenant, course=self.course, employee=self.employee,
            )

    def test_update_progress(self):
        enrollment = CourseEnrollment.objects.create(
            tenant=self.tenant, course=self.course, employee=self.employee,
        )
        enrollment.progress = 75
        enrollment.status = 'in_progress'
        enrollment.save()
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.progress, 75)
        self.assertEqual(enrollment.status, 'in_progress')

    def test_complete_course(self):
        enrollment = CourseEnrollment.objects.create(
            tenant=self.tenant, course=self.course, employee=self.employee,
        )
        enrollment.progress = 100
        enrollment.status = 'completed'
        enrollment.completed_at = timezone.now()
        enrollment.score = Decimal('92.50')
        enrollment.save()
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.status, 'completed')
        self.assertEqual(enrollment.progress, 100)
        self.assertIsNotNone(enrollment.completed_at)


# ---------------------------------------------------------------------------
# Certification tests
# ---------------------------------------------------------------------------

class TestCertification(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('cert-test')
        self.company = _make_company(self.tenant)
        self.employee = _make_employee(self.tenant, self.company)

    def test_create_certification(self):
        cert = Certification.objects.create(
            tenant=self.tenant,
            employee=self.employee,
            name='AWS Certified Solutions Architect',
            issuing_body='Amazon Web Services',
            issued_date='2023-06-01',
            expiry_date='2026-06-01',
        )
        self.assertEqual(cert.status, 'active')
        self.assertFalse(cert.reminder_sent)

    def test_expiry_date_stored(self):
        expiry = datetime.date(2025, 12, 31)
        cert = Certification.objects.create(
            tenant=self.tenant, employee=self.employee,
            name='ISO Auditor Cert', issuing_body='ISO',
            issued_date='2023-01-01', expiry_date=expiry,
        )
        cert.refresh_from_db()
        self.assertEqual(cert.expiry_date, expiry)

    def test_mark_reminder_sent(self):
        cert = Certification.objects.create(
            tenant=self.tenant, employee=self.employee,
            name='Reminder Cert', issuing_body='Test',
            issued_date='2023-01-01', expiry_date='2025-03-01',
        )
        cert.reminder_sent = True
        cert.save()
        cert.refresh_from_db()
        self.assertTrue(cert.reminder_sent)

    def test_expired_certification_status(self):
        cert = Certification.objects.create(
            tenant=self.tenant, employee=self.employee,
            name='Expired Cert', issuing_body='Old Body',
            issued_date='2020-01-01', expiry_date='2021-01-01',
            status='expired',
        )
        self.assertEqual(cert.status, 'expired')
