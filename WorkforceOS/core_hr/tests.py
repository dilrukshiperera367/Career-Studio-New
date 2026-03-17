"""
Core HR tests — Employee CRUD, job history, bulk import/export,
photo upload validation, department hierarchy, and tenant isolation.
"""

import csv
import io
from django.test import TestCase
from django.test.client import RequestFactory

from tenants.models import Tenant
from core_hr.models import Company, Branch, Department, Position, Employee, JobHistory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tenant(slug='core-hr-test'):
    return Tenant.objects.create(name='Core HR Test Org', slug=slug)


def _make_company(tenant):
    return Company.objects.create(tenant=tenant, name='Test Co.', country='LKA', currency='LKR')


def _make_employee(tenant, company, number='EMP001', **kwargs):
    defaults = dict(
        first_name='Alice', last_name='Smith',
        work_email=f'{number.lower()}@example.com',
        hire_date='2023-01-01', status='active',
    )
    defaults.update(kwargs)
    return Employee.objects.create(
        tenant=tenant, company=company,
        employee_number=number,
        **defaults,
    )


# ---------------------------------------------------------------------------
# Employee CRUD tests
# ---------------------------------------------------------------------------

class TestEmployeeCRUD(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('emp-crud')
        self.company = _make_company(self.tenant)

    def test_create_employee(self):
        emp = _make_employee(self.tenant, self.company)
        self.assertEqual(emp.first_name, 'Alice')
        self.assertEqual(emp.status, 'active')

    def test_full_name_property(self):
        emp = _make_employee(self.tenant, self.company)
        self.assertEqual(emp.full_name, 'Alice Smith')

    def test_employee_number_assigned(self):
        emp = _make_employee(self.tenant, self.company)
        self.assertNotEqual(emp.employee_number, '')

    def test_update_employee_status(self):
        emp = _make_employee(self.tenant, self.company)
        emp.status = 'terminated'
        emp.save()
        emp.refresh_from_db()
        self.assertEqual(emp.status, 'terminated')

    def test_soft_delete_via_status(self):
        """HRM uses status field rather than hard-deleting employees."""
        emp = _make_employee(self.tenant, self.company)
        emp.status = 'resigned'
        emp.save()
        # Row still exists in DB
        self.assertTrue(Employee.objects.filter(id=emp.id).exists())

    def test_tenant_isolation(self):
        """Employees of one tenant are not visible under another tenant query."""
        other_tenant = _make_tenant('other-org')
        other_company = _make_company(other_tenant)
        _make_employee(other_tenant, other_company, 'O001')
        _make_employee(self.tenant, self.company, 'E001')
        self.assertEqual(
            Employee.objects.filter(tenant=self.tenant).count(), 1
        )
        self.assertEqual(
            Employee.objects.filter(tenant=other_tenant).count(), 1
        )


# ---------------------------------------------------------------------------
# Job History tests
# ---------------------------------------------------------------------------

class TestJobHistory(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('jobhist-test')
        self.company = _make_company(self.tenant)
        self.employee = _make_employee(self.tenant, self.company)

    def test_create_job_history_record(self):
        history = JobHistory.objects.create(
            tenant=self.tenant, employee=self.employee,
            change_type='hire', effective_date='2023-01-01',
        )
        self.assertEqual(history.change_type, 'hire')

    def test_multiple_history_entries(self):
        """Employee can have multiple job history events."""
        JobHistory.objects.create(
            tenant=self.tenant, employee=self.employee,
            change_type='hire', effective_date='2023-01-01',
        )
        JobHistory.objects.create(
            tenant=self.tenant, employee=self.employee,
            change_type='promotion', effective_date='2024-01-01',
        )
        self.assertEqual(
            JobHistory.objects.filter(employee=self.employee).count(), 2
        )

    def test_history_ordered_by_effective_date_desc(self):
        """Newest history entry appears first."""
        JobHistory.objects.create(
            tenant=self.tenant, employee=self.employee,
            change_type='hire', effective_date='2023-01-01',
        )
        JobHistory.objects.create(
            tenant=self.tenant, employee=self.employee,
            change_type='promotion', effective_date='2024-06-01',
        )
        latest = JobHistory.objects.filter(employee=self.employee).first()
        self.assertEqual(latest.change_type, 'promotion')


# ---------------------------------------------------------------------------
# Department hierarchy tests
# ---------------------------------------------------------------------------

class TestDepartmentHierarchy(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('dept-test')
        self.company = _make_company(self.tenant)

    def test_parent_child_relationship(self):
        parent = Department.objects.create(
            tenant=self.tenant, company=self.company, name='Engineering'
        )
        child = Department.objects.create(
            tenant=self.tenant, company=self.company,
            name='Backend', parent=parent,
        )
        self.assertEqual(child.parent, parent)

    def test_get_ancestors(self):
        root = Department.objects.create(tenant=self.tenant, company=self.company, name='Root')
        mid = Department.objects.create(tenant=self.tenant, company=self.company, name='Mid', parent=root)
        leaf = Department.objects.create(tenant=self.tenant, company=self.company, name='Leaf', parent=mid)
        ancestors = leaf.get_ancestors()
        self.assertIn(root, ancestors)
        self.assertIn(mid, ancestors)

    def test_get_descendants(self):
        root = Department.objects.create(tenant=self.tenant, company=self.company, name='Root')
        child1 = Department.objects.create(tenant=self.tenant, company=self.company, name='Child1', parent=root)
        _child2 = Department.objects.create(tenant=self.tenant, company=self.company, name='Child2', parent=root)
        descendants = root.get_descendants()
        self.assertEqual(len(descendants), 2)


# ---------------------------------------------------------------------------
# Employee export CSV tests (view-level)
# ---------------------------------------------------------------------------

class TestEmployeeExportCSV(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('export-test')
        self.company = _make_company(self.tenant)
        _make_employee(self.tenant, self.company, 'E001')
        _make_employee(self.tenant, self.company, 'E002')

    def test_export_returns_csv_rows(self):
        """Export view returns one data row per employee."""
        from core_hr.views import EmployeeViewSet
        from rest_framework.test import APIRequestFactory
        factory = APIRequestFactory()
        request = factory.get('/employees/export/')
        request.tenant = self.tenant

        view = EmployeeViewSet.as_view({'get': 'export_csv'})
        response = view(request)

        self.assertEqual(response.status_code, 200)
        content = b''.join(response.streaming_content).decode()
        rows = list(csv.reader(io.StringIO(content)))
        # Header + 2 data rows
        self.assertGreaterEqual(len(rows), 3)

    def test_export_content_disposition_header(self):
        """Response must have Content-Disposition: attachment."""
        from core_hr.views import EmployeeViewSet
        from rest_framework.test import APIRequestFactory
        factory = APIRequestFactory()
        request = factory.get('/employees/export/')
        request.tenant = self.tenant

        view = EmployeeViewSet.as_view({'get': 'export_csv'})
        response = view(request)
        self.assertIn('attachment', response.get('Content-Disposition', ''))


# ---------------------------------------------------------------------------
# Photo upload validation tests
# ---------------------------------------------------------------------------

class TestPhotoUploadValidation(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('photo-test')
        self.company = _make_company(self.tenant)
        self.employee = _make_employee(self.tenant, self.company)

    def test_invalid_file_type_rejected(self):
        """PDF upload to photo endpoint must return 400."""
        from core_hr.views import EmployeeViewSet
        from rest_framework.test import APIRequestFactory
        from django.core.files.uploadedfile import SimpleUploadedFile
        factory = APIRequestFactory()
        pdf_file = SimpleUploadedFile('resume.pdf', b'%PDF content', content_type='application/pdf')
        request = factory.post(
            f'/employees/{self.employee.id}/photo/',
            {'photo': pdf_file},
            format='multipart',
        )
        request.tenant = self.tenant

        view = EmployeeViewSet.as_view({'post': 'upload_photo'})
        response = view(request, pk=str(self.employee.id))
        self.assertEqual(response.status_code, 400)

    def test_valid_jpeg_accepted(self):
        """Minimal JPEG bytes (fake) upload should pass type-check and attempt save."""
        from core_hr.views import EmployeeViewSet
        from rest_framework.test import APIRequestFactory
        from django.core.files.uploadedfile import SimpleUploadedFile
        from unittest.mock import patch

        factory = APIRequestFactory()
        # Minimal JPEG magic bytes
        jpeg_bytes = bytes([0xFF, 0xD8, 0xFF, 0xE0]) + b'\x00' * 100
        jpeg_file = SimpleUploadedFile('photo.jpg', jpeg_bytes, content_type='image/jpeg')
        request = factory.post(
            f'/employees/{self.employee.id}/photo/',
            {'photo': jpeg_file},
            format='multipart',
        )
        request.tenant = self.tenant

        with patch('django.core.files.storage.default_storage.save', return_value='employee_photos/test.jpg'):
            view = EmployeeViewSet.as_view({'post': 'upload_photo'})
            response = view(request, pk=str(self.employee.id))
        # 200 or 201 — file accepted
        self.assertIn(response.status_code, [200, 201])
