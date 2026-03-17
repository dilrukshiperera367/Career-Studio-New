"""
Migration: Workflow execution idempotency UNIQUE constraint.

Adds a unique constraint on (workspace_id, application_id, event_id, action_type)
for the WorkflowExecution model so that the same event cannot trigger duplicate
action executions even under concurrent Celery workers.
"""

from django.db import migrations, models

# Step 1: Add idempotency key column
SQL_ADD_COLUMN = """
    ALTER TABLE workflows_workflowexecution
        ADD COLUMN IF NOT EXISTS idempotency_key varchar(255);
"""

SQL_DROP_COLUMN = """
    ALTER TABLE workflows_workflowexecution
        DROP COLUMN IF EXISTS idempotency_key;
"""

# Step 2: Populate idempotency_key for existing rows
SQL_POPULATE = """
    UPDATE workflows_workflowexecution
    SET idempotency_key =
        COALESCE(workspace_id::text, '') || ':' ||
        COALESCE(application_id::text, '') || ':' ||
        COALESCE(event_id::text, '') || ':' ||
        COALESCE(action_type, '')
    WHERE idempotency_key IS NULL;
"""

# Step 3: Unique constraint for idempotency
SQL_CREATE_INDEX = """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE indexname = 'uq_workflow_execution_idempotency'
        ) THEN
            EXECUTE 'CREATE UNIQUE INDEX uq_workflow_execution_idempotency
                ON workflows_workflowexecution (workspace_id, application_id, event_id, action_type)
                WHERE status NOT IN (''failed'', ''cancelled'')';
        END IF;
    END $$;
"""

SQL_DROP_INDEX = """
    DROP INDEX IF EXISTS uq_workflow_execution_idempotency;
"""


def forward(apps, schema_editor):
    db_engine = schema_editor.connection.settings_dict.get("ENGINE", "")
    if "postgresql" not in db_engine:
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(SQL_ADD_COLUMN)
        cursor.execute(SQL_POPULATE)
        cursor.execute(SQL_CREATE_INDEX)


def reverse(apps, schema_editor):
    db_engine = schema_editor.connection.settings_dict.get("ENGINE", "")
    if "postgresql" not in db_engine:
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(SQL_DROP_INDEX)
        cursor.execute(SQL_DROP_COLUMN)


class Migration(migrations.Migration):

    dependencies = [
        ("workflows", "0002_alter_automationrule_options_and_more"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
