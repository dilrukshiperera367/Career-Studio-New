"""
Migration: Workforce Planning & Job Architecture fields on Job model.

Adds:
  - requisition_type  (standard / internal_only / external_only / confidential / evergreen / pooled)
  - must_have_skills  (JSON)
  - trainable_skills  (JSON)
  - hiring_team       (JSON)
  - sla_days_to_fill  (int, nullable)
  - sla_days_to_screen (int, nullable)
  - target_start_date (date, nullable)
  - jd_quality_score  (float, nullable)
  - inclusive_language_score (float, nullable)
  - inclusive_language_flags (JSON)
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0005_job_degree_optional_note_job_degree_required_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='requisition_type',
            field=models.CharField(
                choices=[
                    ('standard', 'Standard'),
                    ('internal_only', 'Internal Only'),
                    ('external_only', 'External Only'),
                    ('confidential', 'Confidential'),
                    ('evergreen', 'Evergreen / Always-Open'),
                    ('pooled', 'Pooled / Talent Pool'),
                ],
                default='standard',
                max_length=20,
                help_text='Controls visibility and pooling behaviour',
            ),
        ),
        migrations.AddField(
            model_name='job',
            name='must_have_skills',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='[{"name": "Python", "level": "practitioner"}] — non-negotiable requirements',
            ),
        ),
        migrations.AddField(
            model_name='job',
            name='trainable_skills',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='[{"name": "Docker"}] — nice-to-have; can be learned on the job',
            ),
        ),
        migrations.AddField(
            model_name='job',
            name='hiring_team',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='[{"user_id": "...", "role": "recruiter|coordinator|interviewer"}]',
            ),
        ),
        migrations.AddField(
            model_name='job',
            name='sla_days_to_fill',
            field=models.IntegerField(
                null=True, blank=True,
                help_text='Target days from open to hire',
            ),
        ),
        migrations.AddField(
            model_name='job',
            name='sla_days_to_screen',
            field=models.IntegerField(
                null=True, blank=True,
                help_text='Target days from apply to first screen',
            ),
        ),
        migrations.AddField(
            model_name='job',
            name='target_start_date',
            field=models.DateField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='job',
            name='jd_quality_score',
            field=models.FloatField(
                null=True, blank=True,
                help_text='0–100 quality score from last JD scan',
            ),
        ),
        migrations.AddField(
            model_name='job',
            name='inclusive_language_score',
            field=models.FloatField(
                null=True, blank=True,
                help_text='0–100 inclusive language score from last scan',
            ),
        ),
        migrations.AddField(
            model_name='job',
            name='inclusive_language_flags',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='[{"term": "ninja", "suggestion": "engineer", "severity": "medium"}]',
            ),
        ),
    ]
