"""
Migration: GIN index on payslip breakdown JSONB + composite performance index
           + immutability trigger for payroll_audit_logs.
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
        ("payroll", "0001_initial"),
    ]

    operations = [
        # ── Payslip: breakdown JSONB ─────────────────────────────────────────
        migrations.RunPython(
            lambda apps, schema_editor: _apply_pg_sql(schema_editor, """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payslip_breakdown_gin
                    ON payroll_payslip
                    USING GIN (breakdown jsonb_path_ops)
                    WHERE breakdown IS NOT NULL;
            """),
            migrations.RunPython.noop,
        ),
        # ── Payslip: composite for period-based reporting ────────────────────
        migrations.RunPython(
            lambda apps, schema_editor: _apply_pg_sql(schema_editor, """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payslips_workspace_period
                    ON payroll_payslip (workspace_id, period_year, period_month, employee_id);
            """),
            migrations.RunPython.noop,
        ),
        # ── Immutability for payroll_audit_logs ──────────────────────────────
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
                        SELECT 1 FROM pg_trigger WHERE tgname = 'immutable_payroll_audit_logs'
                    ) THEN
                        EXECUTE 'CREATE TRIGGER immutable_payroll_audit_logs
                            BEFORE UPDATE OR DELETE ON payroll_payrollauditlog
                            FOR EACH ROW EXECUTE FUNCTION prevent_row_update()';
                    END IF;
                END $$;
            """),
            migrations.RunPython.noop,
        ),
    ]
