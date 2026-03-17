"""Add email_verified fields to User and create EmailVerificationToken model. (#17)"""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_plan_subscription_billinghistory"),
    ]

    operations = [
        # Add email_verified + email_verified_at to User
        migrations.AddField(
            model_name="user",
            name="email_verified",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="user",
            name="email_verified_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
        # EmailVerificationToken model
        migrations.CreateModel(
            name="EmailVerificationToken",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="email_verification_tokens",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("token", models.CharField(db_index=True, max_length=128, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                ("used", models.BooleanField(default=False)),
            ],
            options={"db_table": "email_verification_tokens"},
        ),
    ]
