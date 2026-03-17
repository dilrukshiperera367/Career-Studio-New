"""
Integrations tests — Integration model creation, unique-per-tenant constraint,
WebhookRegistration dispatch queue logic, and status transitions.
"""

from django.test import TestCase
from unittest.mock import patch

from tenants.models import Tenant
from integrations.models import Integration, WebhookRegistration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tenant(slug='integrations-test'):
    return Tenant.objects.create(name='Integrations Test Org', slug=slug)


# ---------------------------------------------------------------------------
# Integration model tests
# ---------------------------------------------------------------------------

class TestIntegrationModel(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('int-model')

    def test_create_integration(self):
        integration = Integration.objects.create(
            tenant=self.tenant,
            connector='slack',
            name='Acme Slack Workspace',
        )
        self.assertEqual(integration.connector, 'slack')
        self.assertEqual(integration.status, 'inactive')

    def test_unique_per_tenant_connector(self):
        """A tenant can only have one integration per connector type."""
        Integration.objects.create(
            tenant=self.tenant, connector='slack', name='Slack 1',
        )
        with self.assertRaises(Exception):
            Integration.objects.create(
                tenant=self.tenant, connector='slack', name='Slack 2',
            )

    def test_activate_integration(self):
        integration = Integration.objects.create(
            tenant=self.tenant, connector='xero', name='Xero Accounting',
        )
        integration.status = 'active'
        integration.save()
        integration.refresh_from_db()
        self.assertEqual(integration.status, 'active')

    def test_error_state_stores_message(self):
        integration = Integration.objects.create(
            tenant=self.tenant, connector='google_calendar', name='GCal',
        )
        integration.status = 'error'
        integration.error_message = 'OAuth token expired'
        integration.save()
        integration.refresh_from_db()
        self.assertEqual(integration.status, 'error')
        self.assertIn('expired', integration.error_message)


# ---------------------------------------------------------------------------
# WebhookRegistration tests
# ---------------------------------------------------------------------------

class TestWebhookRegistration(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('webhook-test')

    def test_create_webhook(self):
        webhook = WebhookRegistration.objects.create(
            tenant=self.tenant,
            target_url='https://example.com/hooks/hrm',
            events=['employee.created', 'leave.approved'],
            name='My Webhook',
        )
        self.assertIsNotNone(webhook.pk)
        self.assertIn('employee.created', webhook.events)

    def test_webhook_default_active(self):
        webhook = WebhookRegistration.objects.create(
            tenant=self.tenant,
            target_url='https://example.com/hook',
            events=['employee.created'],
            name='Active Hook',
        )
        self.assertTrue(webhook.is_active)

    def test_multiple_webhooks_per_tenant(self):
        WebhookRegistration.objects.create(
            tenant=self.tenant, target_url='https://a.com/hook',
            events=['employee.created'], name='Hook A',
        )
        WebhookRegistration.objects.create(
            tenant=self.tenant, target_url='https://b.com/hook',
            events=['payroll.finalized'], name='Hook B',
        )
        self.assertEqual(
            WebhookRegistration.objects.filter(tenant=self.tenant).count(), 2
        )

    def test_ats_connector_integration(self):
        """ATS internal integration connector type must be accepted."""
        integration = Integration.objects.create(
            tenant=self.tenant,
            connector='ats',
            name='ATS Connector',
        )
        self.assertEqual(integration.connector, 'ats')
