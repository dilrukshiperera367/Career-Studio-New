"""
Integration test: ATS offer.accepted webhook → Employee created → Onboarding triggered.
Tests the full bridge pipeline including HMAC validation.
"""

import hashlib
import hmac
import json
import uuid
import pytest

from django.test import TestCase, override_settings
from django.urls import reverse

from tenants.models import Tenant, TenantFeature
from core_hr.models import Company, Employee
from onboarding.models import OnboardingTemplate, OnboardingInstance, OnboardingTask


ATS_WEBHOOK_SECRET = "test-ats-webhook-secret-abc123"


def _build_hire_payload(tenant_id, *, include_onboarding=True):
    return {
        "event": "offer.accepted",
        "tenant_id": str(tenant_id),
        "data": {
            "candidate_id": str(uuid.uuid4()),
            "first_name": "Ashan",
            "last_name": "Perera",
            "email": f"ashan.perera+{uuid.uuid4().hex[:6]}@example.com",
            "phone": "+94771234567",
            "job_title": "Software Engineer",
            "department_name": "Engineering",
            "start_date": "2026-04-01",
            "offer_id": str(uuid.uuid4()),
        },
    }


def _hmac_signature(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@override_settings(ATS_WEBHOOK_SECRET=ATS_WEBHOOK_SECRET)
class TestATSHireWebhook(TestCase):
    """Full integration: POST /api/v1/integrations/ats/hire → employee + onboarding created."""

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Acme Corp", slug="acme-corp")
        TenantFeature.objects.get_or_create(
            tenant=self.tenant, feature="core_hr", defaults={"is_enabled": True}
        )
        TenantFeature.objects.get_or_create(
            tenant=self.tenant, feature="onboarding", defaults={"is_enabled": True}
        )
        self.company = Company.objects.create(
            tenant=self.tenant, name="Acme Ltd", country="LKA", currency="LKR",
        )
        # Create a default onboarding template
        self.template = OnboardingTemplate.objects.create(
            tenant=self.tenant,
            name="Standard Onboarding",
            status="active",
            tasks=[
                {"title": "Setup laptop", "category": "it", "due_offset_days": 1},
                {"title": "Complete HR paperwork", "category": "hr", "due_offset_days": 3},
                {"title": "Meet your team", "category": "manager", "due_offset_days": 7},
            ],
        )
        self.url = "/api/v1/integrations/ats/hire/"

    def _post(self, payload):
        body = json.dumps(payload).encode("utf-8")
        sig = _hmac_signature(ATS_WEBHOOK_SECRET, body)
        return self.client.post(
            self.url,
            data=body,
            content_type="application/json",
            HTTP_X_WEBHOOK_SIGNATURE=sig,
        )

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_employee_created_on_offer_accepted(self):
        """A valid offer.accepted webhook creates an Employee record."""
        payload = _build_hire_payload(self.tenant.id)
        resp = self._post(payload)

        self.assertEqual(resp.status_code, 201, resp.data)
        emp = Employee.objects.filter(
            tenant=self.tenant,
            work_email=payload["data"]["email"],
        ).first()
        self.assertIsNotNone(emp, "Employee should have been created")
        self.assertEqual(emp.first_name, "Ashan")
        self.assertEqual(emp.last_name, "Perera")
        self.assertEqual(emp.source, "ats_import")

    def test_ats_candidate_id_stored(self):
        """ATS candidate ID is persisted on the new employee."""
        payload = _build_hire_payload(self.tenant.id)
        self._post(payload)

        employee = Employee.objects.get(
            tenant=self.tenant,
            work_email=payload["data"]["email"],
        )
        self.assertEqual(str(employee.ats_candidate_id), payload["data"]["candidate_id"])

    def test_onboarding_instance_auto_triggered(self):
        """Onboarding instance + tasks are created automatically after hire."""
        payload = _build_hire_payload(self.tenant.id)
        self._post(payload)

        employee = Employee.objects.get(
            tenant=self.tenant,
            work_email=payload["data"]["email"],
        )
        instance = OnboardingInstance.objects.filter(
            tenant=self.tenant, employee=employee
        ).first()
        self.assertIsNotNone(instance, "OnboardingInstance should be auto-created")

        task_count = OnboardingTask.objects.filter(instance=instance).count()
        self.assertEqual(task_count, len(self.template.tasks),
                         "One task row per template task definition")

    def test_employee_status_is_probation(self):
        """Employee created from ATS hire starts in probation status."""
        payload = _build_hire_payload(self.tenant.id)
        self._post(payload)
        emp = Employee.objects.get(tenant=self.tenant, work_email=payload["data"]["email"])
        self.assertEqual(emp.status, "probation")

    def test_department_and_position_created_if_missing(self):
        """Department and Position are auto-created from the webhook payload if they don't exist."""
        payload = _build_hire_payload(self.tenant.id)
        from core_hr.models import Department, Position
        self.assertFalse(Department.objects.filter(tenant=self.tenant, name="Engineering").exists())
        self._post(payload)
        self.assertTrue(Department.objects.filter(tenant=self.tenant, name="Engineering").exists())
        self.assertTrue(Position.objects.filter(tenant=self.tenant, title="Software Engineer").exists())

    # ------------------------------------------------------------------
    # Security — HMAC validation
    # ------------------------------------------------------------------

    def test_invalid_signature_rejected(self):
        """Webhook with wrong signature must return 401."""
        payload = _build_hire_payload(self.tenant.id)
        body = json.dumps(payload).encode("utf-8")
        resp = self.client.post(
            self.url,
            data=body,
            content_type="application/json",
            HTTP_X_WEBHOOK_SIGNATURE="sha256=badbadbadbad",
        )
        self.assertEqual(resp.status_code, 401)

    def test_missing_signature_rejected(self):
        """Webhook without signature header must return 401."""
        payload = _build_hire_payload(self.tenant.id)
        resp = self.client.post(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 401)

    # ------------------------------------------------------------------
    # Missing / invalid data
    # ------------------------------------------------------------------

    def test_missing_tenant_id_returns_400(self):
        payload = _build_hire_payload(self.tenant.id)
        del payload["tenant_id"]
        body = json.dumps(payload).encode("utf-8")
        resp = self.client.post(
            self.url,
            data=body,
            content_type="application/json",
            HTTP_X_WEBHOOK_SIGNATURE=_hmac_signature(ATS_WEBHOOK_SECRET, body),
        )
        self.assertEqual(resp.status_code, 400)

    def test_unknown_event_type_returns_200_no_op(self):
        """Unknown event types are acknowledged but not processed."""
        payload = {"event": "candidate.viewed", "tenant_id": str(self.tenant.id), "data": {}}
        body = json.dumps(payload).encode("utf-8")
        resp = self.client.post(
            self.url,
            data=body,
            content_type="application/json",
            HTTP_X_WEBHOOK_SIGNATURE=_hmac_signature(ATS_WEBHOOK_SECRET, body),
        )
        self.assertEqual(resp.status_code, 200)
        # No employee should have been created
        self.assertEqual(Employee.objects.filter(tenant=self.tenant).count(), 0)

    def test_duplicate_webhook_does_not_create_duplicate_employee(self):
        """Sending the same offer.accepted payload twice must not create two employees."""
        payload = _build_hire_payload(self.tenant.id)
        self._post(payload)
        self._post(payload)   # replay
        count = Employee.objects.filter(
            tenant=self.tenant, work_email=payload["data"]["email"]
        ).count()
        self.assertLessEqual(count, 1, "Duplicate webhook must not create duplicate employee")
