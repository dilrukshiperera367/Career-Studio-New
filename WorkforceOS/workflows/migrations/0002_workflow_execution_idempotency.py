"""
Migration: HRM Workflow execution idempotency unique constraint.

Prevents duplicate workflow action executions for the same trigger event
under concurrent Celery workers.
"""

from django.db import migrations


def _is_pg(schema_editor):
    return 'postgresql' in schema_editor.connection.settings_dict.get('ENGINE', '')


def _apply_pg_sql(schema_editor, *sql_statements):
    if _is_pg(schema_editor):
        for sql in sql_statements:
            schema_editor.execute(sql)


class Migration(migrations.Migration):

    dependencies = [
        ("workflows", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            lambda apps, schema_editor: _apply_pg_sql(schema_editor, """
                ALTER TABLE workflows_workflowexecution
                    ADD COLUMN IF NOT EXISTS idempotency_key varchar(255);

                UPDATE workflows_workflowexecution
                SET idempotency_key =
                    COALESCE(workspace_id::text, '') || ':' ||
                    COALESCE(employee_id::text, '') || ':' ||
                    COALESCE(event_id::text, '') || ':' ||
                    COALESCE(action_type, '')
                WHERE idempotency_key IS NULL;

                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_indexes
                        WHERE indexname = 'uq_hrm_workflow_execution_idempotency'
                    ) THEN
                        EXECUTE 'CREATE UNIQUE INDEX uq_hrm_workflow_execution_idempotency
                            ON workflows_workflowexecution (workspace_id, employee_id, event_id, action_type)
                            WHERE status NOT IN (''failed'', ''cancelled'')';
                    END IF;
                END $$;
            """),
            migrations.RunPython.noop,
        ),
    ]
