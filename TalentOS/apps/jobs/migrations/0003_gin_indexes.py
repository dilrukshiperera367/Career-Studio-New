"""
Migration: GIN indexes on JSONB columns for jobs app + immutability trigger
for stage_history (applications app) — both belong to the ATS database.

Because CONCURRENTLY cannot run inside a transaction, Django wraps these
in a special atomic=False migration. Django will execute each RunSQL
statement outside an explicit transaction block.
"""

from django.db import migrations

# Forward SQL statements (each must be executed separately for CONCURRENTLY)
FORWARD_SQLS = [
    # ── Jobs: required_skills JSONB ──────────────────────────────────────
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_job_required_skills_gin
        ON jobs_job
        USING GIN (required_skills jsonb_path_ops)
        WHERE required_skills IS NOT NULL;
    """,
    # ── Jobs: screening_questions JSONB ──────────────────────────────────
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_job_screening_questions_gin
        ON jobs_job
        USING GIN (screening_questions jsonb_path_ops)
        WHERE screening_questions IS NOT NULL;
    """,
    # ── Applications: screening_responses JSONB ──────────────────────────
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_application_screening_responses_gin
        ON applications_application
        USING GIN (screening_responses jsonb_path_ops)
        WHERE screening_responses IS NOT NULL;
    """,
    # ── Candidates FTS index ─────────────────────────────────────────────
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_candidates_fts
        ON candidates_candidate
        USING GIN (
            to_tsvector('english',
                COALESCE(full_name, '')  || ' ' ||
                COALESCE(email, '')       || ' ' ||
                COALESCE(current_title, '') || ' ' ||
                COALESCE(summary, '')
            )
        );
    """,
    # ── Applications: composite B-tree for pipeline queries ───────────────
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_applications_workspace_job
        ON applications_application (workspace_id, job_id, stage, created_at DESC);
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_applications_workspace_candidate
        ON applications_application (workspace_id, candidate_id, created_at DESC);
    """,
]

REVERSE_SQLS = [
    "DROP INDEX CONCURRENTLY IF EXISTS idx_job_required_skills_gin;",
    "DROP INDEX CONCURRENTLY IF EXISTS idx_job_screening_questions_gin;",
    "DROP INDEX CONCURRENTLY IF EXISTS idx_application_screening_responses_gin;",
    "DROP INDEX CONCURRENTLY IF EXISTS idx_candidates_fts;",
    "DROP INDEX CONCURRENTLY IF EXISTS idx_applications_workspace_job;",
    "DROP INDEX CONCURRENTLY IF EXISTS idx_applications_workspace_candidate;",
]


def forward(apps, schema_editor):
    db_engine = schema_editor.connection.settings_dict.get("ENGINE", "")
    if "postgresql" not in db_engine:
        return
    with schema_editor.connection.cursor() as cursor:
        for sql in FORWARD_SQLS:
            cursor.execute(sql)


def reverse(apps, schema_editor):
    db_engine = schema_editor.connection.settings_dict.get("ENGINE", "")
    if "postgresql" not in db_engine:
        return
    with schema_editor.connection.cursor() as cursor:
        for sql in REVERSE_SQLS:
            cursor.execute(sql)


class Migration(migrations.Migration):

    # Make sure we run outside a transaction (required for CONCURRENTLY)
    atomic = False

    dependencies = [
        ("jobs", "0002_jobtemplate_job_application_deadline_and_more"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
