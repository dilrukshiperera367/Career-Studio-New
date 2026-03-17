"""
Migration 0003: Performance indexes for platform_core tables.

Adds the following indexes required by the checklist:
  • timeline_events   — (employee_id, created_at DESC) for paginated employee timeline
  • timeline_events   — (tenant_id, category, created_at DESC) for filtered timeline
  • hrm_audit_logs    — the initial migration already creates tenant+created_at and
                        entity_type+entity_id+tenant indexes; this adds user_id index
                        for "actions by user" queries
  • notifications     — (recipient_id, is_read, created_at) for unread-count + bell
  • approval_requests — (tenant_id, status, current_approver_id) for approval queues
  • webhook_deliveries — (subscription_id, success, created_at) for delivery log

NOTE: atomic=False is required for CONCURRENTLY index builds.
"""

from django.db import migrations


def _is_pg(schema_editor):
    return 'postgresql' in schema_editor.connection.settings_dict.get('ENGINE', '')


def _apply_pg_sql(schema_editor, *sql_statements):
    if _is_pg(schema_editor):
        for sql in sql_statements:
            schema_editor.execute(sql)


class Migration(migrations.Migration):

    atomic = False  # required for CREATE INDEX CONCURRENTLY

    dependencies = [
        ("platform_core", "0002_benefitplan_grievancecase_kbcategory_kbarticle_and_more"),
    ]

    operations = [
        # ── timeline_events: primary lookup index ─────────────────────────
        # Supports GET /employees/{id}/timeline?page=N (sorted, paginated)
        migrations.RunPython(
            lambda apps, schema_editor: _apply_pg_sql(schema_editor, """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    idx_timeline_events_employee_created
                ON timeline_events (employee_id, created_at DESC);
            """),
            migrations.RunPython.noop,
        ),

        # ── timeline_events: tenant + category + date for filtered queries ─
        migrations.RunPython(
            lambda apps, schema_editor: _apply_pg_sql(schema_editor, """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    idx_timeline_events_tenant_category
                ON timeline_events (tenant_id, category, created_at DESC);
            """),
            migrations.RunPython.noop,
        ),

        # ── hrm_audit_logs: user_id index for "actions by user" report ────
        migrations.RunPython(
            lambda apps, schema_editor: _apply_pg_sql(schema_editor, """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    idx_audit_logs_user_created
                ON hrm_audit_logs (user_id, created_at DESC)
                WHERE user_id IS NOT NULL;
            """),
            migrations.RunPython.noop,
        ),

        # ── notifications: unread bell + mark-all-read ───────────────────
        migrations.RunPython(
            lambda apps, schema_editor: _apply_pg_sql(schema_editor, """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    idx_notifications_recipient_unread
                ON notifications (recipient_id, created_at DESC)
                WHERE is_read = false;
            """),
            migrations.RunPython.noop,
        ),

        # ── approval_requests: approval queue index ──────────────────────
        migrations.RunPython(
            lambda apps, schema_editor: _apply_pg_sql(schema_editor, """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    idx_approval_requests_approver_status
                ON approval_requests (current_approver_id, status, created_at DESC)
                WHERE status = 'pending';
            """),
            migrations.RunPython.noop,
        ),

        # ── approval_requests: entity lookup (e.g. leave request approvals) ─
        migrations.RunPython(
            lambda apps, schema_editor: _apply_pg_sql(schema_editor, """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    idx_approval_requests_entity
                ON approval_requests (tenant_id, entity_type, entity_id);
            """),
            migrations.RunPython.noop,
        ),

        # ── webhook_deliveries: delivery log pagination ───────────────────
        migrations.RunPython(
            lambda apps, schema_editor: _apply_pg_sql(schema_editor, """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    idx_webhook_deliveries_subscription
                ON webhook_deliveries (subscription_id, created_at DESC);
            """),
            migrations.RunPython.noop,
        ),
    ]
