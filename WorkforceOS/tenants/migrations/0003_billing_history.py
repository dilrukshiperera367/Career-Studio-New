"""Migration 0003: Add BillingHistory model (#353)."""

import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0002_scimconfiguration_scimsynclog_ssoconfiguration_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='BillingHistory',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('event_type', models.CharField(
                    max_length=40,
                    choices=[
                        ('trial_started', 'Trial Started'),
                        ('trial_expired', 'Trial Expired'),
                        ('subscription_created', 'Subscription Created'),
                        ('payment_succeeded', 'Payment Succeeded'),
                        ('payment_failed', 'Payment Failed'),
                        ('plan_upgraded', 'Plan Upgraded'),
                        ('plan_downgraded', 'Plan Downgraded'),
                        ('subscription_cancelled', 'Subscription Cancelled'),
                        ('refund_issued', 'Refund Issued'),
                        ('invoice_generated', 'Invoice Generated'),
                    ],
                )),
                ('amount', models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)),
                ('currency', models.CharField(max_length=3, default='USD')),
                ('plan_before', models.CharField(max_length=20, blank=True)),
                ('plan_after', models.CharField(max_length=20, blank=True)),
                ('stripe_event_id', models.CharField(max_length=100, blank=True)),
                ('metadata', models.JSONField(default=dict, blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('tenant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='billing_history',
                    to='tenants.tenant',
                )),
                ('subscription', models.ForeignKey(
                    on_delete=django.db.models.deletion.SET_NULL,
                    null=True,
                    blank=True,
                    related_name='billing_history',
                    to='tenants.subscription',
                )),
            ],
            options={
                'app_label': 'tenants',
                'db_table': 'billing_history',
                'ordering': ['-created_at'],
            },
        ),
    ]
