"""
Data migration: Enable PostgreSQL Row-Level Security (RLS) on all ATS tenant-scoped tables.

This migration:
1. Creates the current_workspace_id() helper function used in USING clauses.
2. Enables RLS on each tenant-scoped table.
3. Creates a USING policy so every query is transparently filtered to the
   current tenant's workspace (set via `SET app.current_workspace_id = '...'`).
4. Creates immutability triggers on append-only audit tables (stage_history).

Apply ONLY against a PostgreSQL database. Wrapped in a RunSQL with an explicit
reverse (DROP) for robust backwards migration.
"""

from django.db import migrations

# Tables scoped to a single tenant (have a tenant_id / workspace_id column)
TENANT_TABLES = [
    "candidates",
    "candidate_identities",
    "resume_documents",
    "candidate_skills",
    "candidate_experiences",
    "candidate_education",
    "candidate_notes",
    "candidate_certifications",
    "merge_audits",
    "applications",
    "evaluations",
    "interviews",
    "interview_panels",
    "interview_scorecards",
    "offers",
    "employees",
    "onboarding_tasks",
    "jobs",
    "job_templates",
    "pipeline_stages",
]

# Append-only audit/history tables — rows must never be updated or deleted
IMMUTABLE_TABLES = [
    "stage_history",
]


def _enable_rls(table: str) -> str:
    """SQL to enable RLS on a table with a tenant isolation policy."""
    return f"""
ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON "{table}";
CREATE POLICY tenant_isolation ON "{table}"
    USING (tenant_id = current_setting('app.current_workspace_id', TRUE)::uuid)
    WITH CHECK (tenant_id = current_setting('app.current_workspace_id', TRUE)::uuid);
"""


def _disable_rls(table: str) -> str:
    """Reverse: drop policy and disable RLS on a table."""
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
-- Helper function: return the current workspace UUID from connection settings
CREATE OR REPLACE FUNCTION current_workspace_id() RETURNS uuid AS $$
    SELECT current_setting('app.current_workspace_id', TRUE)::uuid;
$$ LANGUAGE SQL STABLE SECURITY DEFINER;

-- Helper function: prevent mutations on immutable audit tables
CREATE OR REPLACE FUNCTION prevent_row_update() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'Updates and deletes are not permitted on audit table %', TG_TABLE_NAME;
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


def forward(apps, schema_editor):
    db_engine = schema_editor.connection.settings_dict.get("ENGINE", "")
    if "postgresql" not in db_engine:
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(FORWARD_SQL)


def reverse(apps, schema_editor):
    db_engine = schema_editor.connection.settings_dict.get("ENGINE", "")
    if "postgresql" not in db_engine:
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(REVERSE_SQL)


class Migration(migrations.Migration):
    """
    Row-Level Security migration for the ATS system.

    IMPORTANT: This migration uses raw PostgreSQL-specific SQL.
    It will be silently skipped if run against SQLite (development).
    For production PostgreSQL, apply after all other migrations.
    """

    dependencies = [
        ("candidates", "0003_candidate_gdpr_deletion_requested_at_and_more"),
        ("applications", "0003_employee_interviewpanel_interviewscorecard_and_more"),
        ("jobs", "0002_jobtemplate_job_application_deadline_and_more"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
