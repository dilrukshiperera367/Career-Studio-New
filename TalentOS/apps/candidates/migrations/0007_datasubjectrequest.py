"""Migration 0007: Add DataSubjectRequest model for GDPR right of access/erasure (#49, #50)."""

import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('candidates', '0006_alter_candidate_options'),
        ('tenants', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DataSubjectRequest',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('request_type', models.CharField(
                    max_length=20,
                    choices=[
                        ('access', 'Right of Access'),
                        ('erasure', 'Right to Erasure'),
                        ('portability', 'Data Portability'),
                        ('rectification', 'Rectification'),
                    ],
                )),
                ('requester_email', models.EmailField(help_text='Email of the data subject making the request')),
                ('status', models.CharField(
                    max_length=20,
                    default='pending',
                    choices=[
                        ('pending', 'Pending'),
                        ('in_progress', 'In Progress'),
                        ('completed', 'Completed'),
                        ('rejected', 'Rejected'),
                    ],
                )),
                ('deadline', models.DateField(
                    null=True, blank=True,
                    help_text='Statutory deadline (30 days from receipt under GDPR)',
                )),
                ('notes', models.TextField(blank=True, default='')),
                ('processed_at', models.DateTimeField(null=True, blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='data_subject_requests',
                    to='tenants.tenant',
                )),
                ('submitted_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.SET_NULL,
                    null=True, blank=True,
                    related_name='submitted_dsrs',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('processed_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.SET_NULL,
                    null=True, blank=True,
                    related_name='processed_dsrs',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'data_subject_requests',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='datasubjectrequest',
            index=models.Index(fields=['tenant', 'status'], name='dsr_tenant_status_idx'),
        ),
        migrations.AddIndex(
            model_name='datasubjectrequest',
            index=models.Index(fields=['requester_email'], name='dsr_email_idx'),
        ),
    ]
