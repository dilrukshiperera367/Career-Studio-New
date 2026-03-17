"""
Migration: Add HiringTeamTemplate, SLAConfig, IntakeMeetingTemplate, HiringPlanCalendar
to the job_architecture app.
"""

import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('job_architecture', '0001_initial'),
        ('tenants', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── HiringTeamTemplate ────────────────────────────────────────────────
        migrations.CreateModel(
            name='HiringTeamTemplate',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255, help_text="e.g. 'Engineering Full-Cycle Team'")),
                ('interviewers', models.JSONField(blank=True, default=list,
                    help_text='[{"user_id": "...", "round": 1, "focus": "Technical"}]')),
                ('notes', models.TextField(blank=True, default='')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='hiring_team_templates', to='tenants.tenant')),
                ('job_family', models.ForeignKey(blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='hiring_team_templates', to='job_architecture.jobfamily')),
                ('recruiter', models.ForeignKey(blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='htt_recruiter', to=settings.AUTH_USER_MODEL)),
                ('coordinator', models.ForeignKey(blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='htt_coordinator', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'hiring_team_templates', 'ordering': ['name']},
        ),

        # ── SLAConfig ─────────────────────────────────────────────────────────
        migrations.CreateModel(
            name='SLAConfig',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('scope', models.CharField(
                    choices=[
                        ('global', 'Global (all roles)'),
                        ('job_family', 'Job Family'),
                        ('job_level', 'Job Level'),
                        ('department', 'Department'),
                    ],
                    default='global', max_length=20,
                )),
                ('department', models.CharField(blank=True, default='', max_length=150)),
                ('days_to_fill', models.IntegerField(default=45, help_text='Target days from open to hire')),
                ('days_to_screen', models.IntegerField(default=5, help_text='Target days from apply to first screen')),
                ('days_to_offer', models.IntegerField(default=30, help_text='Target days from open to offer')),
                ('days_per_stage', models.JSONField(blank=True, default=dict,
                    help_text='{"screening": 5, "interview": 14, "offer": 3}')),
                ('escalation_enabled', models.BooleanField(default=True)),
                ('escalation_recipient_role', models.CharField(blank=True, default='', max_length=100)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='sla_configs', to='tenants.tenant')),
                ('job_family', models.ForeignKey(blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='sla_configs', to='job_architecture.jobfamily')),
                ('job_level', models.ForeignKey(blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='sla_configs', to='job_architecture.joblevel')),
            ],
            options={'db_table': 'sla_configs', 'ordering': ['scope', 'name']},
        ),

        # ── IntakeMeetingTemplate ─────────────────────────────────────────────
        migrations.CreateModel(
            name='IntakeMeetingTemplate',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('agenda_items', models.JSONField(blank=True, default=list)),
                ('recruiter_questions', models.JSONField(blank=True, default=list)),
                ('must_have_prompt', models.TextField(blank=True, default='')),
                ('nice_to_have_prompt', models.TextField(blank=True, default='')),
                ('suggested_pipeline', models.JSONField(blank=True, default=list)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='intake_meeting_templates', to='tenants.tenant')),
                ('job_family', models.ForeignKey(blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='intake_templates', to='job_architecture.jobfamily')),
            ],
            options={'db_table': 'intake_meeting_templates', 'ordering': ['name']},
        ),

        # ── HiringPlanCalendar ────────────────────────────────────────────────
        migrations.CreateModel(
            name='HiringPlanCalendar',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('fiscal_year', models.IntegerField()),
                ('quarter', models.IntegerField(help_text='1–4')),
                ('month', models.IntegerField(blank=True, null=True, help_text='1–12')),
                ('department', models.CharField(blank=True, default='', max_length=150)),
                ('location', models.CharField(blank=True, default='', max_length=255)),
                ('target_start_date', models.DateField(blank=True, null=True)),
                ('headcount', models.IntegerField(default=1)),
                ('budget_allocated', models.DecimalField(blank=True, decimal_places=2, max_digits=16, null=True)),
                ('budget_currency', models.CharField(default='USD', max_length=3)),
                ('status', models.CharField(
                    choices=[
                        ('planned', 'Planned'),
                        ('approved', 'Approved'),
                        ('in_progress', 'In Progress'),
                        ('completed', 'Completed'),
                        ('deferred', 'Deferred'),
                    ],
                    default='planned', max_length=20,
                )),
                ('notes', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='hiring_plan_calendars', to='tenants.tenant')),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='calendar_entries', to='job_architecture.headcountplan')),
                ('requisition', models.ForeignKey(blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='calendar_entries', to='job_architecture.headcountrequisition')),
                ('hiring_manager', models.ForeignKey(blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='hiring_plan_entries', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'hiring_plan_calendar',
                     'ordering': ['fiscal_year', 'quarter', 'department']},
        ),
    ]
