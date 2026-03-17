"""
Tenants tests — Tenant creation, plan enforcement, TenantFeature gating,
slug uniqueness, and settings_json persistence.
"""

from django.test import TestCase

from tenants.models import Tenant, TenantFeature


# ---------------------------------------------------------------------------
# Tenant model tests
# ---------------------------------------------------------------------------

class TestTenantModel(TestCase):
    def test_create_tenant(self):
        tenant = Tenant.objects.create(name='Acme Corp', slug='acme-corp')
        self.assertEqual(tenant.name, 'Acme Corp')
        self.assertEqual(tenant.slug, 'acme-corp')
        self.assertEqual(tenant.status, 'active')

    def test_default_plan_is_free(self):
        tenant = Tenant.objects.create(name='Trial Org', slug='trial-org')
        self.assertEqual(tenant.plan, 'free')

    def test_slug_uniqueness(self):
        """Two tenants with the same slug must raise IntegrityError."""
        Tenant.objects.create(name='Org A', slug='shared-slug')
        with self.assertRaises(Exception):
            Tenant.objects.create(name='Org B', slug='shared-slug')

    def test_settings_json_persistence(self):
        settings_data = {'primary_color': '#ff7a59', 'timezone': 'Asia/Colombo'}
        tenant = Tenant.objects.create(
            name='Branded Org', slug='branded-org',
            settings_json=settings_data,
        )
        tenant.refresh_from_db()
        self.assertEqual(tenant.settings_json['primary_color'], '#ff7a59')

    def test_hrm_settings_json(self):
        tenant = Tenant.objects.create(
            name='HRM Org', slug='hrm-org',
            hrm_settings={'currency': 'LKR', 'working_days': 5},
        )
        tenant.refresh_from_db()
        self.assertEqual(tenant.hrm_settings['currency'], 'LKR')

    def test_plan_upgrade(self):
        tenant = Tenant.objects.create(name='Growing Org', slug='growing-org', plan='free')
        tenant.plan = 'pro'
        tenant.save()
        tenant.refresh_from_db()
        self.assertEqual(tenant.plan, 'pro')

    def test_suspend_tenant(self):
        tenant = Tenant.objects.create(name='Bad Actor', slug='bad-actor')
        tenant.status = 'suspended'
        tenant.save()
        tenant.refresh_from_db()
        self.assertEqual(tenant.status, 'suspended')


# ---------------------------------------------------------------------------
# TenantFeature tests
# ---------------------------------------------------------------------------

class TestTenantFeature(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='Feature Org', slug='feature-org', plan='pro')

    def test_enable_module(self):
        feature = TenantFeature.objects.create(
            tenant=self.tenant,
            module='payroll',
            tier='pro',
            enabled=True,
        )
        self.assertTrue(feature.enabled)
        self.assertEqual(feature.module, 'payroll')

    def test_disable_module(self):
        feature = TenantFeature.objects.create(
            tenant=self.tenant, module='learning', tier='starter', enabled=False,
        )
        self.assertFalse(feature.enabled)

    def test_multiple_modules(self):
        for module in ['core_hr', 'leave_attendance', 'payroll']:
            TenantFeature.objects.create(
                tenant=self.tenant, module=module, tier='pro', enabled=True,
            )
        enabled_count = TenantFeature.objects.filter(tenant=self.tenant, enabled=True).count()
        self.assertEqual(enabled_count, 3)

    def test_feature_unique_per_module_per_tenant(self):
        """A tenant cannot have duplicate feature entries for the same module."""
        TenantFeature.objects.create(tenant=self.tenant, module='analytics', tier='pro', enabled=True)
        with self.assertRaises(Exception):
            TenantFeature.objects.create(tenant=self.tenant, module='analytics', tier='starter', enabled=False)
