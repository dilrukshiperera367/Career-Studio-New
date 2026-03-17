"""Migration: Replace BinaryField with FileField for BatchItem and CandidateResumeVersion.

Stores CV files in S3/MinIO instead of as raw bytes in the database.
Existing file_content data is dropped as part of this migration — files
must be re-uploaded.  The parallel `file_hash` column is kept.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scoring", "0002_scorecard_db_models"),
    ]

    operations = [
        # ── BatchItem ─────────────────────────────────────────────────────────
        migrations.RemoveField(
            model_name="batchitem",
            name="file_content",
        ),
        migrations.AddField(
            model_name="batchitem",
            name="file",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="batches/%Y/%m/",
                help_text="CV file stored in S3/MinIO (replaces BinaryField)",
            ),
        ),
        # ── CandidateResumeVersion ────────────────────────────────────────────
        migrations.RemoveField(
            model_name="candidateresumeversion",
            name="file_content",
        ),
        migrations.AddField(
            model_name="candidateresumeversion",
            name="file",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="resumes/%Y/%m/",
                help_text="Resume file stored in S3/MinIO (replaces BinaryField)",
            ),
        ),
    ]
