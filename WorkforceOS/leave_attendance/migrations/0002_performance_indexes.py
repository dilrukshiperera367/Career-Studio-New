"""
Migration 0002: Performance indexes for leave_attendance tables.

Adds the following indexes required by the checklist:
  • attendance_records  — composite on (employee_id, clock_in::date)
                          for fast "what did employee X do on date Y" lookups
  • leave_requests      — composite on (employee_id, status, start_date)
                          for pending/approved leave queries
  • leave_requests      — composite on (tenant_id, start_date, end_date)
                          for team-calendar range queries
  • attendance_records  — composite on (tenant_id, clock_in)
                          for payroll summary queries across a period

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
        ("leave_attendance", "0001_initial"),
    ]

    operations = [
        # ── attendance_records: daily lookup index ────────────────────────
        # Supports: "all punches for employee X on date Y"
        migrations.RunPython(
            lambda apps, schema_editor: _apply_pg_sql(schema_editor, """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    idx_attendance_employee_date
                ON attendance_records (employee_id, (clock_in::date));
            """),
            migrations.RunPython.noop,
        ),

        # ── attendance_records: tenant + period index ─────────────────────
        # Supports payroll attendance summary for a given month
        migrations.RunPython(
            lambda apps, schema_editor: _apply_pg_sql(schema_editor, """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    idx_attendance_tenant_clockin
                ON attendance_records (tenant_id, clock_in)
                WHERE clock_in IS NOT NULL;
            """),
            migrations.RunPython.noop,
        ),

        # ── leave_requests: employee + status + start_date ───────────────
        # Supports: "pending/approved leaves for employee X from date Y"
        migrations.RunPython(
            lambda apps, schema_editor: _apply_pg_sql(schema_editor, """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    idx_leave_requests_employee_status_start
                ON leave_requests (employee_id, status, start_date);
            """),
            migrations.RunPython.noop,
        ),

        # ── leave_requests: tenant + date range ──────────────────────────
        # Supports team-calendar queries: "who is on leave between date A and B?"
        migrations.RunPython(
            lambda apps, schema_editor: _apply_pg_sql(schema_editor, """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    idx_leave_requests_tenant_dates
                ON leave_requests (tenant_id, start_date, end_date)
                WHERE status IN ('approved', 'pending');
            """),
            migrations.RunPython.noop,
        ),

        # ── leave_requests: leave_type for analytics ─────────────────────
        migrations.RunPython(
            lambda apps, schema_editor: _apply_pg_sql(schema_editor, """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    idx_leave_requests_leave_type
                ON leave_requests (tenant_id, leave_type_id, status);
            """),
            migrations.RunPython.noop,
        ),

        # ── attendance_records: status for exception reports ─────────────
        migrations.RunPython(
            lambda apps, schema_editor: _apply_pg_sql(schema_editor, """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    idx_attendance_tenant_status
                ON attendance_records (tenant_id, status)
                WHERE status IN ('late', 'absent', 'half_day', 'missing_punch');
            """),
            migrations.RunPython.noop,
        ),
    ]
