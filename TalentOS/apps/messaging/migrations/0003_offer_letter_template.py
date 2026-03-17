"""
Migration 0003: Add OfferLetterTemplate model (#45 — offer letter template CRUD).
"""
import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('messaging', '0002_activitylog_user_agent_message_clicked_at_and_more'),
        ('tenants', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='OfferLetterTemplate',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('slug', models.CharField(max_length=100)),
                ('name', models.CharField(max_length=200)),
                ('subject_line', models.CharField(default='Offer of Employment — {{company_name}}', max_length=500)),
                ('html_body', models.TextField(
                    help_text='Full HTML body with {{variable}} placeholders. Leave blank to use system default.'
                )),
                ('is_default', models.BooleanField(
                    default=False,
                    help_text='If True, this template is used when no template is explicitly selected on an offer.'
                )),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='offer_letter_templates',
                    to='tenants.tenant',
                )),
                ('created_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_offer_templates',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'offer_letter_templates',
            },
        ),
        migrations.AlterUniqueTogether(
            name='offerlettertemplate',
            unique_together={('tenant', 'slug')},
        ),
        migrations.AddIndex(
            model_name='offerlettertemplate',
            index=models.Index(fields=['tenant', 'is_default'], name='offer_tmpl_tenant_default_idx'),
        ),
        migrations.AddIndex(
            model_name='offerlettertemplate',
            index=models.Index(fields=['tenant', 'is_active'], name='offer_tmpl_tenant_active_idx'),
        ),
    ]
