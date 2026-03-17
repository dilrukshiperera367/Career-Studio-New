"""
Migration 0006: Structured AuditLog table with monthly range partitioning.

Creates a PostgreSQL RANGE-partitioned audit_log table (partitioned on
created_at). Partitions are created for the current month + 2 future months.
A pg_cron job (or a Celery beat task) is responsible for creating future
partition slices on a monthly schedule.

The table is NOT managed by Django ORM (managed=False raw SQL only).
It co-exists with the json-based AuditLogMiddleware which logs to stderr;
write operations from the middleware are also persisted here via a signal
or explicit call in production.

NOTE: PostgreSQL < 10 does not support declarative partitioning.
This migration is idempotent — safe to re-run.
"""

from django.db import migrations


_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS ats_audit_log (
    id          uuid                     NOT NULL DEFAULT gen_random_uuid(),
    tenant_id   uuid,
    user_id     uuid,
    method      varchar(10)              NOT NULL,
    path        varchar(1000)            NOT NULL,
    status_code smallint,
    ip_address  inet,
    user_agent  varchar(500),
    body_summary text,
    metadata    jsonb,
    duration_ms numeric(10, 2),
    created_at  timestamptz              NOT NULL DEFAULT now()
) PARTITION BY RANGE (created_at);
"""

_CREATE_INDEX = """
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ats_audit_log_tenant_created
    ON ats_audit_log (tenant_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ats_audit_log_user_created
    ON ats_audit_log (user_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ats_audit_log_status
    ON ats_audit_log (status_code, created_at DESC);
"""

_CREATE_PARTITIONS = """
DO $$
DECLARE
    start_date  date := date_trunc('month', now())::date;
    months      int  := 3;  -- current + 2 ahead
    d           date;
    tname       text;
    end_date    date;
BEGIN
    FOR i IN 0..months - 1 LOOP
        d        := start_date + (i || ' months')::interval;
        end_date := d + '1 month'::interval;
        tname    := 'ats_audit_log_' || to_char(d, 'YYYY_MM');

        IF NOT EXISTS (
            SELECT 1 FROM pg_tables WHERE tablename = tname
        ) THEN
            EXECUTE format(
                'CREATE TABLE %I PARTITION OF ats_audit_log
                    FOR VALUES FROM (%L) TO (%L)',
                tname, d, end_date
            );
            RAISE NOTICE 'Created partition: %', tname;
        END IF;
    END LOOP;
END $$;
"""

_CREATE_IMMUTABILITY_TRIGGER = """
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
        SELECT 1 FROM pg_trigger WHERE tgname = 'immutable_ats_audit_log'
    ) THEN
        -- Triggers on partitioned tables automatically propagate to children
        EXECUTE 'CREATE TRIGGER immutable_ats_audit_log
            BEFORE UPDATE OR DELETE ON ats_audit_log
            FOR EACH ROW EXECUTE FUNCTION prevent_row_update()';
    END IF;
END $$;
"""

_DROP_TABLE = """
DROP TABLE IF EXISTS ats_audit_log CASCADE;
"""


def run_pg_sql(apps, schema_editor):
    """Execute PostgreSQL-specific partition DDL only when running on PostgreSQL."""
    db_engine = schema_editor.connection.settings_dict.get("ENGINE", "")
    if "postgresql" not in db_engine:
        return  # Skip on SQLite and other non-PG backends

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(_CREATE_TABLE)
        cursor.execute(_CREATE_PARTITIONS)

    # Indexes with CONCURRENTLY must be outside a transaction
    with schema_editor.connection.cursor() as cursor:
        for stmt in _CREATE_INDEX.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                cursor.execute(stmt)

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(_CREATE_IMMUTABILITY_TRIGGER)


def reverse_pg_sql(apps, schema_editor):
    """Drop the partitioned audit log table (PostgreSQL only)."""
    db_engine = schema_editor.connection.settings_dict.get("ENGINE", "")
    if "postgresql" not in db_engine:
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(_DROP_TABLE)


class Migration(migrations.Migration):

    atomic = False  # CONCURRENTLY requires non-transactional DDL

    dependencies = [
        ("accounts", "0005_user_mfa_fields"),
    ]

    operations = [
        migrations.RunPython(run_pg_sql, reverse_pg_sql),
    ]
