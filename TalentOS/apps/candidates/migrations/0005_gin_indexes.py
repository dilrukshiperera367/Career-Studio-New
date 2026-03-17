"""
Migration: GIN indexes on JSONB columns for candidates app.

Adds partial GIN indexes on high-cardinality JSONB fields to speed up
containment queries (e.g., @> operator on parsed_data, skills, tags).
Uses SeparateDatabaseAndState so Django's migration state is not affected
(the fields already exist; we're only adding PostgreSQL-side indexes).
"""

from django.db import migrations

# Forward SQL statements (each must be executed separately for CONCURRENTLY)
FORWARD_SQLS = [
    # Index parsed_data JSONB for fast skill / keyword containment queries
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_candidate_parsed_data_gin
        ON candidates_candidate
        USING GIN (parsed_data jsonb_path_ops)
        WHERE parsed_data IS NOT NULL;
    """,
    # Index skills JSONB array for tag-based filtering
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_candidate_skills_gin
        ON candidates_candidate
        USING GIN (skills jsonb_path_ops)
        WHERE skills IS NOT NULL;
    """,
    # Index tags array
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_candidate_tags_gin
        ON candidates_candidate
        USING GIN (tags)
        WHERE tags IS NOT NULL;
    """,
]

REVERSE_SQLS = [
    "DROP INDEX IF EXISTS idx_candidate_parsed_data_gin;",
    "DROP INDEX IF EXISTS idx_candidate_skills_gin;",
    "DROP INDEX IF EXISTS idx_candidate_tags_gin;",
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

    atomic = False  # Required for CREATE INDEX CONCURRENTLY

    dependencies = [
        ("candidates", "0004_rls_tenant_isolation"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
