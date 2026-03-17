# Generated migration for apps.internal_bridge

import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("jobs", "0001_initial"),
        ("tenants", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [

        # 1. InternalRequisition
        migrations.CreateModel(
            name="InternalRequisition",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=255)),
                ("department", models.CharField(blank=True, default="", max_length=150)),
                ("visibility", models.CharField(choices=[("internal_only","Internal Only"),("internal_first","Internal First"),("public","Public")], default="internal_only", max_length=20)),
                ("internal_posting_opens_at", models.DateTimeField(blank=True, null=True)),
                ("public_posting_opens_at", models.DateTimeField(blank=True, null=True)),
                ("is_gig", models.BooleanField(default=False)),
                ("gig_duration_weeks", models.IntegerField(default=0)),
                ("requires_manager_approval", models.BooleanField(default=True)),
                ("description", models.TextField(blank=True, default="")),
                ("skills_required", models.JSONField(default=list)),
                ("status", models.CharField(default="draft", max_length=30)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="internal_requisitions", to="tenants.tenant")),
                ("job", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="internal_requisitions", to="jobs.job")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_internal_reqs", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "ib_internal_requisitions", "ordering": ["-created_at"]},
        ),

        # 2. InternalPostingWindow
        migrations.CreateModel(
            name="InternalPostingWindow",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("opens_at", models.DateTimeField()),
                ("closes_at", models.DateTimeField()),
                ("notified_employees", models.BooleanField(default=False)),
                ("notification_sent_at", models.DateTimeField(blank=True, null=True)),
                ("notification_channels", models.JSONField(default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="internal_posting_windows", to="tenants.tenant")),
                ("internal_req", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="posting_windows", to="internal_bridge.internalrequisition")),
            ],
            options={"db_table": "ib_internal_posting_windows", "ordering": ["-opens_at"]},
        ),

        # 3. InternalCandidate
        migrations.CreateModel(
            name="InternalCandidate",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("employee_id", models.CharField(blank=True, default="", max_length=100)),
                ("candidate_id", models.UUIDField(blank=True, null=True)),
                ("application_id", models.UUIDField(blank=True, null=True)),
                ("source_type", models.CharField(choices=[("internal_apply","Internal Apply"),("manager_referred","Manager Referred"),("talent_marketplace","Talent Marketplace"),("internal_referral","Internal Referral"),("rehire","Rehire"),("alumni","Alumni Fast-Track")], default="internal_apply", max_length=30)),
                ("current_role", models.CharField(blank=True, default="", max_length=255)),
                ("current_department", models.CharField(blank=True, default="", max_length=150)),
                ("current_manager_id", models.CharField(blank=True, default="", max_length=100)),
                ("years_at_company", models.DecimalField(decimal_places=1, default=0, max_digits=4)),
                ("confidentiality_level", models.CharField(choices=[("standard","Standard"),("confidential","Confidential"),("highly_confidential","Highly Confidential")], default="standard", max_length=25)),
                ("manager_notified", models.BooleanField(default=False)),
                ("manager_approved", models.BooleanField(default=False)),
                ("manager_approval_at", models.DateTimeField(blank=True, null=True)),
                ("status", models.CharField(default="applied", max_length=30)),
                ("is_rehire", models.BooleanField(default=False)),
                ("is_alumni", models.BooleanField(default=False)),
                ("fast_tracked", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="internal_candidates", to="tenants.tenant")),
                ("employee_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="internal_candidacies", to=settings.AUTH_USER_MODEL)),
                ("internal_req", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="internal_candidates", to="internal_bridge.internalrequisition")),
            ],
            options={"db_table": "ib_internal_candidates", "ordering": ["-created_at"]},
        ),

        # 4. InternalTransferWorkflow
        migrations.CreateModel(
            name="InternalTransferWorkflow",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("from_department", models.CharField(blank=True, default="", max_length=150)),
                ("from_role", models.CharField(blank=True, default="", max_length=255)),
                ("to_department", models.CharField(blank=True, default="", max_length=150)),
                ("to_role", models.CharField(blank=True, default="", max_length=255)),
                ("from_manager_approval", models.CharField(default="pending", max_length=20)),
                ("from_manager_approved_at", models.DateTimeField(blank=True, null=True)),
                ("to_manager_approval", models.CharField(default="pending", max_length=20)),
                ("to_manager_approved_at", models.DateTimeField(blank=True, null=True)),
                ("hr_approval", models.CharField(default="pending", max_length=20)),
                ("hr_approved_at", models.DateTimeField(blank=True, null=True)),
                ("effective_date", models.DateField(blank=True, null=True)),
                ("transition_plan", models.TextField(blank=True, default="")),
                ("status", models.CharField(default="initiated", max_length=30)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="internal_transfer_workflows", to="tenants.tenant")),
                ("internal_candidate", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="transfer_workflows", to="internal_bridge.internalcandidate")),
            ],
            options={"db_table": "ib_internal_transfer_workflows", "ordering": ["-created_at"]},
        ),

        # 5. EmployeeSkillProfileBridge
        migrations.CreateModel(
            name="EmployeeSkillProfileBridge",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("employee_id", models.CharField(blank=True, default="", max_length=100)),
                ("skills", models.JSONField(default=list)),
                ("certifications", models.JSONField(default=list)),
                ("interests", models.JSONField(default=list)),
                ("career_goals", models.TextField(blank=True, default="")),
                ("open_to_gig", models.BooleanField(default=False)),
                ("open_to_transfer", models.BooleanField(default=False)),
                ("last_synced_from_hrm_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="employee_skill_bridges", to="tenants.tenant")),
                ("employee_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="skill_bridge_profiles", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "ib_employee_skill_bridges", "ordering": ["-updated_at"]},
        ),

        # 6. InternalReferral
        migrations.CreateModel(
            name="InternalReferral",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("referred_employee_id", models.CharField(blank=True, default="", max_length=100)),
                ("referred_employee_name", models.CharField(blank=True, default="", max_length=255)),
                ("referral_note", models.TextField(blank=True, default="")),
                ("status", models.CharField(default="submitted", max_length=30)),
                ("bonus_eligible", models.BooleanField(default=False)),
                ("bonus_paid_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="internal_referrals", to="tenants.tenant")),
                ("referrer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="made_internal_referrals", to=settings.AUTH_USER_MODEL)),
                ("internal_req", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="internal_referrals", to="internal_bridge.internalrequisition")),
            ],
            options={"db_table": "ib_internal_referrals", "ordering": ["-created_at"]},
        ),

        # 7. RehireAlumniRecord
        migrations.CreateModel(
            name="RehireAlumniRecord",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("candidate_id", models.UUIDField(blank=True, null=True)),
                ("employee_id", models.CharField(blank=True, default="", max_length=100)),
                ("name", models.CharField(max_length=255)),
                ("previous_department", models.CharField(blank=True, default="", max_length=150)),
                ("previous_role", models.CharField(blank=True, default="", max_length=255)),
                ("previous_tenure_months", models.IntegerField(default=0)),
                ("separation_date", models.DateField(blank=True, null=True)),
                ("separation_type", models.CharField(default="voluntary", max_length=30)),
                ("rehire_eligible", models.BooleanField(default=True)),
                ("rehire_notes", models.TextField(blank=True, default="")),
                ("fast_track_approved", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="rehire_alumni_records", to="tenants.tenant")),
                ("applied_to_req", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="rehire_alumni", to="internal_bridge.internalrequisition")),
            ],
            options={"db_table": "ib_rehire_alumni_records", "ordering": ["-created_at"]},
        ),

        # 8. PipelineComparison
        migrations.CreateModel(
            name="PipelineComparison",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("snapshotted_at", models.DateTimeField(auto_now_add=True)),
                ("internal_total", models.IntegerField(default=0)),
                ("external_total", models.IntegerField(default=0)),
                ("internal_advance_rate", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("external_advance_rate", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("internal_offer_rate", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("external_offer_rate", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("internal_hire_rate", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("external_hire_rate", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("internal_avg_ttf_days", models.DecimalField(decimal_places=1, default=0, max_digits=6)),
                ("external_avg_ttf_days", models.DecimalField(decimal_places=1, default=0, max_digits=6)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pipeline_comparisons", to="tenants.tenant")),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pipeline_comparisons", to="jobs.job")),
            ],
            options={"db_table": "ib_pipeline_comparisons", "ordering": ["-snapshotted_at"]},
        ),

        # 9. InternalCandidateCompare
        migrations.CreateModel(
            name="InternalCandidateCompare",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("candidate_ids", models.JSONField(default=list)),
                ("comparison_dimensions", models.JSONField(default=list)),
                ("scores", models.JSONField(default=dict)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="internal_candidate_compares", to="tenants.tenant")),
                ("internal_req", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="candidate_compares", to="internal_bridge.internalrequisition")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="internal_compares", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "ib_internal_candidate_compares", "ordering": ["-created_at"]},
        ),

        # 10. ManagerInternalApproval
        migrations.CreateModel(
            name="ManagerInternalApproval",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(default="pending", max_length=20)),
                ("decision_note", models.TextField(blank=True, default="")),
                ("conditions", models.TextField(blank=True, default="")),
                ("decided_at", models.DateTimeField(blank=True, null=True)),
                ("reminder_sent_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="manager_internal_approvals", to="tenants.tenant")),
                ("internal_candidate", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="manager_approvals", to="internal_bridge.internalcandidate")),
                ("manager", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="given_manager_approvals", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "ib_manager_internal_approvals", "ordering": ["-created_at"]},
        ),

        # 11. InternalCandidacyConfidentialityLog
        migrations.CreateModel(
            name="InternalCandidacyConfidentialityLog",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("action", models.CharField(max_length=50)),
                ("detail", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="confidentiality_logs", to="tenants.tenant")),
                ("internal_candidate", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="confidentiality_logs", to="internal_bridge.internalcandidate")),
                ("performed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="confidentiality_actions", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "ib_confidentiality_logs", "ordering": ["-created_at"]},
        ),

        # 12. TalentMarketplaceUsageStat
        migrations.CreateModel(
            name="TalentMarketplaceUsageStat",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("period_start", models.DateField()),
                ("period_end", models.DateField()),
                ("total_employees", models.IntegerField(default=0)),
                ("employees_browsed", models.IntegerField(default=0)),
                ("employees_applied", models.IntegerField(default=0)),
                ("employees_hired_internally", models.IntegerField(default=0)),
                ("gig_completions", models.IntegerField(default=0)),
                ("internal_mobility_rate", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="talent_marketplace_stats", to="tenants.tenant")),
            ],
            options={"db_table": "ib_talent_marketplace_stats", "ordering": ["-period_start"]},
        ),

        # 13. InternalJobAlert
        migrations.CreateModel(
            name="InternalJobAlert",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("channel", models.CharField(default="email", max_length=20)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("opened", models.BooleanField(default=False)),
                ("clicked", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="internal_job_alerts", to="tenants.tenant")),
                ("employee_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="internal_job_alerts", to=settings.AUTH_USER_MODEL)),
                ("internal_req", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="job_alerts", to="internal_bridge.internalrequisition")),
            ],
            options={"db_table": "ib_internal_job_alerts", "ordering": ["-created_at"]},
        ),

        # 14. InternalGigAssignment
        migrations.CreateModel(
            name="InternalGigAssignment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("hours_per_week", models.DecimalField(decimal_places=1, default=0, max_digits=5)),
                ("status", models.CharField(default="active", max_length=20)),
                ("outcome_notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="internal_gig_assignments", to="tenants.tenant")),
                ("internal_req", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="gig_assignments", to="internal_bridge.internalrequisition")),
                ("internal_candidate", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="gig_assignments", to="internal_bridge.internalcandidate")),
            ],
            options={"db_table": "ib_internal_gig_assignments", "ordering": ["-created_at"]},
        ),
    ]
