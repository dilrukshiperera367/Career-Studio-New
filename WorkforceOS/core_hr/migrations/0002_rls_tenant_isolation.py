"""
Data migration: Enable PostgreSQL Row-Level Security (RLS) on all HRM tenant-scoped tables.

This migration:
1. Creates the current_workspace_id() helper function.
2. Enables RLS on each tenant-scoped table.
3. Creates a USING policy for transparent tenant isolation.
4. Creates immutability trigger on audit tables (payroll_audit_logs, job_history).

Apply ONLY against PostgreSQL. Silently skipped on SQLite (dev/test).
"""

from django.db import migrations


def _is_pg(schema_editor):
    return 'postgresql' in schema_editor.connection.settings_dict.get('ENGINE', '')


def _apply_pg_sql(schema_editor, *sql_statements):
    if _is_pg(schema_editor):
        for sql in sql_statements:
            schema_editor.execute(sql)


# All tenant-scoped HRM tables
TENANT_TABLES = [
    # core_hr
    "employees",
    "companies",
    "branches",
    "departments",
    "positions",
    "job_history",
    "employee_documents",
    "announcements",
    # payroll
    "salary_structures",
    "employee_compensations",
    "payroll_runs",
    "payroll_entries",
    "statutory_rules",
    "loan_records",
    # leave_attendance
    "leave_types",
    "leave_balances",
    "leave_requests",
    "holiday_calendars",
    "holidays",
    "shift_templates",
    "shift_assignments",
    "attendance_records",
    "overtime_records",
]

# Append-only audit tables — rows must never be mutated after insert
IMMUTABLE_TABLES = [
    "payroll_audit_logs",
    "job_history",
]


def _enable_rls(table: str) -> str:
    return f"""
ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON "{table}";
CREATE POLICY tenant_isolation ON "{table}"
    USING (tenant_id = current_setting('app.current_workspace_id', TRUE)::uuid)
    WITH CHECK (tenant_id = current_setting('app.current_workspace_id', TRUE)::uuid);
"""


def _disable_rls(table: str) -> str:
    return f"""
DROP POLICY IF EXISTS tenant_isolation ON "{table}";
ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY;
"""


def _immutability_trigger(table: str) -> str:
    return f"""
DROP TRIGGER IF EXISTS immutable_{table} ON "{table}";
CREATE TRIGGER immutable_{table}
    BEFORE UPDATE OR DELETE ON "{table}"
    FOR EACH ROW EXECUTE FUNCTION prevent_row_update();
"""


def _drop_immutability_trigger(table: str) -> str:
    return f'DROP TRIGGER IF EXISTS immutable_{table} ON "{table}";'


FORWARD_SQL = """
-- Workspace helper function
CREATE OR REPLACE FUNCTION current_workspace_id() RETURNS uuid AS $$
    SELECT current_setting('app.current_workspace_id', TRUE)::uuid;
$$ LANGUAGE SQL STABLE SECURITY DEFINER;

-- Immutability guard
CREATE OR REPLACE FUNCTION prevent_row_update() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'Audit table % is append-only', TG_TABLE_NAME;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
""" + "".join(_enable_rls(t) for t in TENANT_TABLES) + "".join(_immutability_trigger(t) for t in IMMUTABLE_TABLES)


REVERSE_SQL = (
    "".join(_drop_immutability_trigger(t) for t in IMMUTABLE_TABLES)
    + "".join(_disable_rls(t) for t in TENANT_TABLES)
    + """
DROP FUNCTION IF EXISTS prevent_row_update();
DROP FUNCTION IF EXISTS current_workspace_id();
"""
)


class Migration(migrations.Migration):
    """HRM Row-Level Security migration. Apply after all initial schema migrations."""

    dependencies = [
        ("core_hr", "0001_initial"),
        ("payroll", "0001_initial"),
        ("leave_attendance", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            lambda apps, schema_editor: _apply_pg_sql(schema_editor, FORWARD_SQL),
            migrations.RunPython.noop,
        ),
    ]
