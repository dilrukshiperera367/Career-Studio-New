"""
Migration: Add hrm_employee_id and hrm_employee_number to the Offer model.

These fields are populated via the HRM `employee.id_assigned` webhook
callback immediately after an employee record is created in the HRM system
following an accepted ATS offer.
"""

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("applications", "0003_employee_interviewpanel_interviewscorecard_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="offer",
            name="hrm_employee_id",
            field=models.UUIDField(
                null=True,
                blank=True,
                help_text="UUID of the HRM Employee record created from this offer",
            ),
        ),
        migrations.AddField(
            model_name="offer",
            name="hrm_employee_number",
            field=models.CharField(
                max_length=50,
                blank=True,
                default="",
                help_text="Human-readable employee number assigned by HRM (e.g., EMP-001)",
            ),
        ),
    ]
