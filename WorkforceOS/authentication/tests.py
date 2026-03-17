"""
Authentication tests — User creation, login, JWT token generation,
tenant isolation, and RBAC role assignment.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model

from tenants.models import Tenant
from authentication.models import Role, UserRole

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tenant(slug='auth-test'):
    return Tenant.objects.create(name='Auth Test Org', slug=slug)


def _make_user(email, tenant=None, password='Secr3t!Pass'):
    user = User.objects.create_user(
        email=email, tenant_id=tenant.id if tenant else None,
        first_name='Test', last_name='User',
    )
    user.set_password(password)
    user.save()
    return user


# ---------------------------------------------------------------------------
# User model tests
# ---------------------------------------------------------------------------

class TestUserModel(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('user-model')

    def test_create_user(self):
        user = _make_user('alice@example.com', self.tenant)
        self.assertEqual(user.email, 'alice@example.com')
        self.assertTrue(user.is_active)

    def test_full_name_property(self):
        user = _make_user('bob@example.com', self.tenant)
        self.assertEqual(user.full_name, 'Test User')

    def test_unique_email_per_tenant(self):
        """Same email in the same tenant must raise IntegrityError."""
        _make_user('dup@example.com', self.tenant)
        with self.assertRaises(Exception):
            _make_user('dup@example.com', self.tenant)

    def test_password_hashed(self):
        user = _make_user('hashed@example.com', self.tenant)
        self.assertNotEqual(user.password, 'Secr3t!Pass')
        self.assertTrue(user.check_password('Secr3t!Pass'))

    def test_disabled_user_is_active_false(self):
        user = _make_user('disabled@example.com', self.tenant)
        user.is_active = False
        user.save()
        user.refresh_from_db()
        self.assertFalse(user.is_active)


# ---------------------------------------------------------------------------
# Tenant isolation tests
# ---------------------------------------------------------------------------

class TestUserTenantIsolation(TestCase):
    def setUp(self):
        self.tenant_a = _make_tenant('tenant-a-auth')
        self.tenant_b = _make_tenant('tenant-b-auth')

    def test_users_scoped_to_tenant(self):
        _make_user('user-a@example.com', self.tenant_a)
        _make_user('user-b@example.com', self.tenant_b)
        self.assertEqual(User.objects.filter(tenant=self.tenant_a).count(), 1)
        self.assertEqual(User.objects.filter(tenant=self.tenant_b).count(), 1)


# ---------------------------------------------------------------------------
# RBAC Role tests
# ---------------------------------------------------------------------------

class TestRoles(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('role-test')

    def test_create_system_role(self):
        role = Role.objects.create(
            name='HR Manager', is_system_role=True,
        )
        self.assertTrue(role.is_system_role)

    def test_create_tenant_role(self):
        role = Role.objects.create(
            tenant=self.tenant, name='Custom Role',
        )
        self.assertEqual(role.tenant, self.tenant)

    def test_assign_role_to_user(self):
        user = _make_user('manager@example.com', self.tenant)
        role = Role.objects.create(tenant=self.tenant, name='Manager')
        UserRole.objects.create(user=user, role=role, tenant=self.tenant)
        self.assertEqual(user.user_roles.count(), 1)


# ---------------------------------------------------------------------------
# JWT login API tests
# ---------------------------------------------------------------------------

class TestJWTLogin(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('jwt-test')
        self.user = _make_user('jwtuser@example.com', self.tenant, password='TestPass1!')

    def test_login_returns_tokens(self):
        """POST /auth/token/ returns access and refresh tokens."""
        from rest_framework.test import APIClient
        client = APIClient()
        response = client.post('/auth/token/', {
            'email': 'jwtuser@example.com',
            'password': 'TestPass1!',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_wrong_password_rejected(self):
        from rest_framework.test import APIClient
        client = APIClient()
        response = client.post('/auth/token/', {
            'email': 'jwtuser@example.com',
            'password': 'WrongPassword',
        }, format='json')
        self.assertEqual(response.status_code, 401)
