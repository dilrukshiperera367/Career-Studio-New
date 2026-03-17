"""
Add composite indexes and GIN indexes for performance.
"""
from django.db import migrations, connection


def apply_pg_indexes(apps, schema_editor):
    """Run PostgreSQL-specific index creation; silently skip on other databases."""
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'shared_auditlog' AND indexname = 'idx_auditlog_metadata_gin'
            ) THEN
                CREATE INDEX idx_auditlog_metadata_gin
                ON shared_auditlog USING gin(metadata jsonb_path_ops);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'shared_auditlog' AND indexname = 'idx_auditlog_tenant_action'
            ) THEN
                CREATE INDEX idx_auditlog_tenant_action
                ON shared_auditlog(tenant_id, action, created_at DESC);
            END IF;
        EXCEPTION WHEN OTHERS THEN
            NULL;
        END $$;
    """)


def reverse_pg_indexes(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    schema_editor.execute("DROP INDEX IF EXISTS idx_auditlog_metadata_gin;")
    schema_editor.execute("DROP INDEX IF EXISTS idx_auditlog_tenant_action;")


class Migration(migrations.Migration):

    dependencies = [
        ('shared', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(apply_pg_indexes, reverse_code=reverse_pg_indexes),
    ]
