"""Migration 0007: Add Plan, Subscription, and BillingHistory models for SaaS billing."""

import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_audit_log_partition"),
        ("tenants", "0001_initial"),
    ]

    operations = [
        # Plan model
        migrations.CreateModel(
            name="Plan",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=100)),
                ("tier", models.CharField(
                    choices=[
                        ("free_trial", "Free Trial"),
                        ("starter", "Starter"),
                        ("professional", "Professional"),
                        ("enterprise", "Enterprise"),
                    ],
                    max_length=30,
                    unique=True,
                )),
                ("price_monthly", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("price_annually", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("max_jobs", models.IntegerField(default=5)),
                ("max_candidates", models.IntegerField(default=100)),
                ("max_users", models.IntegerField(default=3)),
                ("features", models.JSONField(default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "plans", "ordering": ["price_monthly"]},
        ),
        # Subscription model
        migrations.CreateModel(
            name="Subscription",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("tenant", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="subscription",
                    to="tenants.tenant",
                )),
                ("plan", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    to="accounts.plan",
                )),
                ("status", models.CharField(
                    choices=[
                        ("trialing", "Trialing"),
                        ("active", "Active"),
                        ("past_due", "Past Due"),
                        ("canceled", "Canceled"),
                        ("expired", "Expired"),
                        ("grace_period", "Grace Period"),
                    ],
                    default="trialing",
                    max_length=20,
                )),
                ("billing_cycle", models.CharField(
                    choices=[("monthly", "Monthly"), ("annually", "Annually")],
                    default="monthly",
                    max_length=10,
                )),
                ("trial_start", models.DateTimeField(blank=True, null=True)),
                ("trial_end", models.DateTimeField(blank=True, null=True)),
                ("trial_days", models.IntegerField(default=14)),
                ("stripe_customer_id", models.CharField(blank=True, max_length=100)),
                ("stripe_subscription_id", models.CharField(blank=True, max_length=100)),
                ("current_period_start", models.DateTimeField(blank=True, null=True)),
                ("current_period_end", models.DateTimeField(blank=True, null=True)),
                ("canceled_at", models.DateTimeField(blank=True, null=True)),
                ("grace_period_end", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "subscriptions", "ordering": ["-created_at"]},
        ),
        # BillingHistory model
        migrations.CreateModel(
            name="BillingHistory",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("subscription", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="billing_history",
                    to="accounts.subscription",
                )),
                ("record_type", models.CharField(
                    choices=[
                        ("invoice", "Invoice"),
                        ("payment", "Payment"),
                        ("refund", "Refund"),
                        ("credit", "Credit"),
                    ],
                    default="invoice",
                    max_length=20,
                )),
                ("status", models.CharField(
                    choices=[
                        ("paid", "Paid"),
                        ("unpaid", "Unpaid"),
                        ("void", "Void"),
                        ("refunded", "Refunded"),
                    ],
                    default="unpaid",
                    max_length=20,
                )),
                ("amount", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("currency", models.CharField(default="USD", max_length=3)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("stripe_invoice_id", models.CharField(blank=True, max_length=100)),
                ("period_start", models.DateTimeField(blank=True, null=True)),
                ("period_end", models.DateTimeField(blank=True, null=True)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("invoice_pdf_url", models.URLField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "billing_history", "ordering": ["-created_at"]},
        ),
    ]
