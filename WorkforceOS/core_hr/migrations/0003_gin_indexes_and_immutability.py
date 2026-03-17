"""
Migration: GIN indexes on JSONB columns for HRM core_hr app.

Adds GIN indexes on custom_fields and other JSONB columns used in
employee profile search. Uses atomic=False to allow CONCURRENTLY.
"""

from django.db import migrations


def _is_pg(schema_editor):
    return 'postgresql' in schema_editor.connection.settings_dict.get('ENGINE', '')


def _apply_pg_sql(schema_editor, *sql_statements):
    if _is_pg(schema_editor):
        for sql in sql_statements:
            schema_editor.execute(sql)


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ("core_hr", "0002_rls_tenant_isolation"),
    ]

    operations = [
        # ── Employee: custom_fields JSONB ────────────────────────────────────
        migrations.RunPython(
            lambda apps, schema_editor: _apply_pg_sql(schema_editor, """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_employee_custom_fields_gin
                    ON core_hr_employee
                    USING GIN (custom_fields jsonb_path_ops)
                    WHERE custom_fields IS NOT NULL;
            """),
            migrations.RunPython.noop,
        ),
        # ── Employee: emergency_contacts (JSONB array) ───────────────────────
        migrations.RunPython(
            lambda apps, schema_editor: _apply_pg_sql(schema_editor, """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_employee_emergency_contacts_gin
                    ON core_hr_employee
                    USING GIN (emergency_contacts jsonb_path_ops)
                    WHERE emergency_contacts IS NOT NULL;
            """),
            migrations.RunPython.noop,
        ),
        # ── Employee: composite B-tree for department/status queries ─────────
        migrations.RunPython(
            lambda apps, schema_editor: _apply_pg_sql(schema_editor, """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_employees_workspace_dept
                    ON core_hr_employee (workspace_id, department_id, status);
            """),
            migrations.RunPython.noop,
        ),
        # ── Immutability trigger for job_history ─────────────────────────────
        # The trigger function prevent_row_update() is created in rls-init.sql.
        # We recreate it here in case this migration runs on a fresh DB before
        # the init script.
        migrations.RunPython(
            lambda apps, schema_editor: _apply_pg_sql(schema_editor, """
                CREATE OR REPLACE FUNCTION prevent_row_update()
                RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    RAISE EXCEPTION 'Rows in table % are immutable and cannot be updated or deleted.',
                        TG_TABLE_NAME;
                    RETURN NULL;
                END;
                $$;

                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_trigger WHERE tgname = 'immutable_job_history'
                    ) THEN
                        EXECUTE 'CREATE TRIGGER immutable_job_history
                            BEFORE UPDATE OR DELETE ON core_hr_jobhistory
                            FOR EACH ROW EXECUTE FUNCTION prevent_row_update()';
                    END IF;
                END $$;
            """),
            migrations.RunPython.noop,
        ),
    ]
