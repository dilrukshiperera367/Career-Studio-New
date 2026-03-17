"""
Shared pytest fixtures for HRM integration tests.
All fixtures create isolated tenant contexts to prevent cross-test pollution.
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta

from tenants.models import Tenant, TenantFeature
from authentication.models import User, Role, Permission, UserRole
from core_hr.models import Company, Department, Position, Employee


# ---------------------------------------------------------------------------
# Tenant / company helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def tenant_a(db):
    """Primary test tenant."""
    t = Tenant.objects.create(name="Alpha Corp", slug="alpha-corp")
    # Enable all modules for testing
    for module in [
        "core_hr", "leave", "attendance", "payroll",
        "onboarding", "performance", "engagement", "helpdesk",
    ]:
        TenantFeature.objects.get_or_create(tenant=t, feature=module, defaults={"is_enabled": True})
    return t


@pytest.fixture
def tenant_b(db):
    """Second tenant — used for RLS isolation tests."""
    t = Tenant.objects.create(name="Beta Ltd", slug="beta-ltd")
    for module in ["core_hr", "leave", "attendance", "payroll"]:
        TenantFeature.objects.get_or_create(tenant=t, feature=module, defaults={"is_enabled": True})
    return t


@pytest.fixture
def company_a(db, tenant_a):
    return Company.objects.create(
        tenant=tenant_a, name="Alpha Corp Pvt Ltd",
        country="LKA", currency="LKR",
    )


@pytest.fixture
def company_b(db, tenant_b):
    return Company.objects.create(
        tenant=tenant_b, name="Beta Ltd",
        country="LKA", currency="LKR",
    )


@pytest.fixture
def department_a(db, tenant_a, company_a):
    return Department.objects.create(
        tenant=tenant_a, company=company_a, name="Engineering",
    )


@pytest.fixture
def position_a(db, tenant_a, company_a, department_a):
    return Position.objects.create(
        tenant=tenant_a, company=company_a, department=department_a,
        title="Software Engineer", headcount=5,
    )


# ---------------------------------------------------------------------------
# Employee helpers
# ---------------------------------------------------------------------------

def make_employee(tenant, company, department=None, position=None, *,
                  number="EMP001", hire_date="2023-01-01", status="active"):
    return Employee.objects.create(
        tenant=tenant,
        company=company,
        department=department,
        position=position,
        employee_number=number,
        first_name="Test",
        last_name="Employee",
        work_email=f"{number.lower()}@example.com",
        hire_date=hire_date,
        status=status,
    )


@pytest.fixture
def employee_a(db, tenant_a, company_a, department_a, position_a):
    return make_employee(tenant_a, company_a, department_a, position_a,
                         number="EMP001-A")


@pytest.fixture
def employee_b_tenant_b(db, tenant_b, company_b):
    """Employee in Tenant B — must not be visible from Tenant A."""
    return make_employee(tenant_b, company_b, number="EMP001-B")


# ---------------------------------------------------------------------------
# User / role helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def hr_admin_user(db, tenant_a):
    user = User.objects.create_user(
        email="hradmin@alpha.com",
        tenant_id=str(tenant_a.id),
        password="Test@1234",
        first_name="HR",
        last_name="Admin",
    )
    role, _ = Role.objects.get_or_create(
        name="HR Admin", defaults={"is_system_role": True}
    )
    UserRole.objects.create(user=user, role=role, tenant=tenant_a)
    return user


@pytest.fixture
def manager_user(db, tenant_a):
    user = User.objects.create_user(
        email="manager@alpha.com",
        tenant_id=str(tenant_a.id),
        password="Test@1234",
        first_name="Team",
        last_name="Manager",
    )
    role, _ = Role.objects.get_or_create(
        name="Manager", defaults={"is_system_role": True}
    )
    UserRole.objects.create(user=user, role=role, tenant=tenant_a)
    return user


@pytest.fixture
def employee_user(db, tenant_a):
    user = User.objects.create_user(
        email="emp@alpha.com",
        tenant_id=str(tenant_a.id),
        password="Test@1234",
        first_name="Emp",
        last_name="User",
    )
    role, _ = Role.objects.get_or_create(
        name="Employee", defaults={"is_system_role": True}
    )
    UserRole.objects.create(user=user, role=role, tenant=tenant_a)
    return user
