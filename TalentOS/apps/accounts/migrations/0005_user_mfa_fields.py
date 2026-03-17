"""Migration: add MFA TOTP fields to User model."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_passwordresettoken_invitetoken"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="mfa_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="user",
            name="mfa_secret",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
    ]
