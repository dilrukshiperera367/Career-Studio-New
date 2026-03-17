# Generated migration for apps.hm_workspace

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

        # 1. RoleIntakeForm
        migrations.CreateModel(
            name="RoleIntakeForm",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("role_title", models.CharField(max_length=255)),
                ("department", models.CharField(blank=True, default="", max_length=150)),
                ("team", models.CharField(blank=True, default="", max_length=150)),
                ("headcount", models.IntegerField(default=1)),
                ("budget_range_min", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("budget_range_max", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("target_start_date", models.DateField(blank=True, null=True)),
                ("location", models.CharField(blank=True, default="", max_length=255)),
                ("is_remote", models.BooleanField(default=False)),
                ("employment_type", models.CharField(default="full_time", max_length=50)),
                ("priority", models.CharField(choices=[("low","Low"),("medium","Medium"),("high","High"),("critical","Critical")], default="medium", max_length=20)),
                ("ideal_candidate_profile", models.TextField(blank=True, default="")),
                ("must_have_skills", models.JSONField(default=list)),
                ("nice_to_have_skills", models.JSONField(default=list)),
                ("deal_breakers", models.TextField(blank=True, default="")),
                ("team_context", models.TextField(blank=True, default="")),
                ("reporting_structure", models.TextField(blank=True, default="")),
                ("interview_process_notes", models.TextField(blank=True, default="")),
                ("degree_required", models.BooleanField(default=False)),
                ("years_experience_min", models.IntegerField(default=0)),
                ("status", models.CharField(default="draft", max_length=30)),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="role_intakes", to="tenants.tenant")),
                ("job", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="intake_forms", to="jobs.job")),
                ("hiring_manager", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="hm_intake_forms", to=settings.AUTH_USER_MODEL)),
                ("recruiter", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="recruiter_intake_forms", to=settings.AUTH_USER_MODEL)),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="approved_intakes", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "hm_role_intake_forms", "ordering": ["-created_at"]},
        ),

        # 2. ShortlistReview
        migrations.CreateModel(
            name="ShortlistReview",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(default="Shortlist", max_length=255)),
                ("candidates", models.JSONField(default=list)),
                ("is_locked", models.BooleanField(default=False)),
                ("notes", models.TextField(blank=True, default="")),
                ("shared_at", models.DateTimeField(blank=True, null=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="shortlist_reviews", to="tenants.tenant")),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="shortlist_reviews", to="jobs.job")),
                ("hiring_manager", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="hm_shortlist_reviews", to=settings.AUTH_USER_MODEL)),
                ("recruiter", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="recruiter_shortlist_reviews", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "hm_shortlist_reviews", "ordering": ["-created_at"]},
        ),

        # 3. CandidateComparison
        migrations.CreateModel(
            name="CandidateComparison",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(default="Comparison", max_length=255)),
                ("candidate_ids", models.JSONField(default=list)),
                ("comparison_criteria", models.JSONField(default=list)),
                ("scores", models.JSONField(default=dict)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="candidate_comparisons", to="tenants.tenant")),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="candidate_comparisons", to="jobs.job")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_comparisons", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "hm_candidate_comparisons", "ordering": ["-created_at"]},
        ),

        # 4. HMFeedbackInboxItem
        migrations.CreateModel(
            name="HMFeedbackInboxItem",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("interview_id", models.UUIDField(blank=True, null=True)),
                ("candidate_name", models.CharField(blank=True, default="", max_length=255)),
                ("job_title", models.CharField(blank=True, default="", max_length=255)),
                ("feedback_summary", models.TextField(blank=True, default="")),
                ("recommendation", models.CharField(blank=True, default="", max_length=30)),
                ("is_read", models.BooleanField(default=False)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="hm_feedback_inbox", to="tenants.tenant")),
                ("hiring_manager", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="hm_feedback_items", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "hm_feedback_inbox", "ordering": ["-created_at"]},
        ),

        # 5. HMApprovalTask
        migrations.CreateModel(
            name="HMApprovalTask",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("task_type", models.CharField(choices=[("shortlist_review","Shortlist Review"),("offer_approval","Offer Approval"),("req_approval","Req Approval"),("intake_review","Intake Review"),("candidate_advance","Candidate Advance"),("candidate_reject","Candidate Reject"),("message_approval","Message Approval"),("other","Other")], default="other", max_length=30)),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, default="")),
                ("related_object_id", models.UUIDField(blank=True, null=True)),
                ("related_object_type", models.CharField(blank=True, default="", max_length=100)),
                ("status", models.CharField(choices=[("pending","Pending"),("approved","Approved"),("rejected","Rejected"),("needs_revision","Needs Revision")], default="pending", max_length=20)),
                ("priority", models.CharField(choices=[("low","Low"),("medium","Medium"),("high","High"),("critical","Critical")], default="medium", max_length=20)),
                ("due_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("decision_note", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="hm_approval_tasks", to="tenants.tenant")),
                ("assigned_to", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_hm_tasks", to=settings.AUTH_USER_MODEL)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_hm_tasks", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "hm_approval_tasks", "ordering": ["-created_at"]},
        ),

        # 6. HMDecisionQueueItem
        migrations.CreateModel(
            name="HMDecisionQueueItem",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("candidate_name", models.CharField(blank=True, default="", max_length=255)),
                ("job_title", models.CharField(blank=True, default="", max_length=255)),
                ("job_id", models.UUIDField(blank=True, null=True)),
                ("application_id", models.UUIDField(blank=True, null=True)),
                ("decision_type", models.CharField(default="advance", max_length=30)),
                ("decision", models.CharField(blank=True, default="", max_length=30)),
                ("decision_note", models.TextField(blank=True, default="")),
                ("is_resolved", models.BooleanField(default=False)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="hm_decision_queue", to="tenants.tenant")),
                ("hiring_manager", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="hm_decision_items", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "hm_decision_queue", "ordering": ["-created_at"]},
        ),

        # 7. ReqHealthSnapshot
        migrations.CreateModel(
            name="ReqHealthSnapshot",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("snapshotted_at", models.DateTimeField(auto_now_add=True)),
                ("pipeline_total", models.IntegerField(default=0)),
                ("pipeline_by_stage", models.JSONField(default=dict)),
                ("days_open", models.IntegerField(default=0)),
                ("target_days", models.IntegerField(default=45)),
                ("interviews_scheduled", models.IntegerField(default=0)),
                ("offers_extended", models.IntegerField(default=0)),
                ("offers_accepted", models.IntegerField(default=0)),
                ("drop_rate", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("health_score", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("health_flags", models.JSONField(default=list)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="req_health_snapshots", to="tenants.tenant")),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="health_snapshots", to="jobs.job")),
            ],
            options={"db_table": "hm_req_health_snapshots", "ordering": ["-snapshotted_at"]},
        ),

        # 8. TimeToFillRisk
        migrations.CreateModel(
            name="TimeToFillRisk",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("assessed_at", models.DateTimeField(auto_now_add=True)),
                ("days_open", models.IntegerField(default=0)),
                ("target_fill_days", models.IntegerField(default=45)),
                ("predicted_fill_days", models.IntegerField(blank=True, null=True)),
                ("risk_level", models.CharField(choices=[("low","Low"),("medium","Medium"),("high","High"),("critical","Critical")], default="medium", max_length=10)),
                ("risk_factors", models.JSONField(default=list)),
                ("recommended_actions", models.JSONField(default=list)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ttf_risks", to="tenants.tenant")),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ttf_risks", to="jobs.job")),
            ],
            options={"db_table": "hm_ttf_risks", "ordering": ["-assessed_at"]},
        ),

        # 9. CandidateMessageApproval
        migrations.CreateModel(
            name="CandidateMessageApproval",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("candidate_name", models.CharField(blank=True, default="", max_length=255)),
                ("message_subject", models.CharField(blank=True, default="", max_length=255)),
                ("message_body", models.TextField(blank=True, default="")),
                ("status", models.CharField(choices=[("pending","Pending"),("approved","Approved"),("rejected","Rejected"),("needs_revision","Needs Revision")], default="pending", max_length=20)),
                ("reviewer_note", models.TextField(blank=True, default="")),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="message_approvals", to="tenants.tenant")),
                ("recruiter", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sent_message_approvals", to=settings.AUTH_USER_MODEL)),
                ("approver", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_message_approvals", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "hm_message_approvals", "ordering": ["-created_at"]},
        ),

        # 10. HMSLAReminder
        migrations.CreateModel(
            name="HMSLAReminder",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("sla_type", models.CharField(choices=[("shortlist_review","Shortlist Review"),("feedback_submission","Feedback Submission"),("offer_approval","Offer Approval"),("req_approval","Req Approval"),("decision","Decision"),("intake_completion","Intake Completion")], default="decision", max_length=30)),
                ("related_object_id", models.UUIDField(blank=True, null=True)),
                ("due_at", models.DateTimeField()),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("is_resolved", models.BooleanField(default=False)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("escalated", models.BooleanField(default=False)),
                ("escalated_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="hm_sla_reminders", to="tenants.tenant")),
                ("hiring_manager", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="hm_sla_reminders", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "hm_sla_reminders", "ordering": ["-created_at"]},
        ),

        # 11. HMCalibrationView
        migrations.CreateModel(
            name="HMCalibrationView",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("candidate_name", models.CharField(blank=True, default="", max_length=255)),
                ("application_id", models.UUIDField(blank=True, null=True)),
                ("interviewer_scores", models.JSONField(default=dict)),
                ("consensus_score", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ("hm_recommendation", models.CharField(blank=True, default="", max_length=30)),
                ("hm_notes", models.TextField(blank=True, default="")),
                ("calibration_complete", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="hm_calibration_views", to="tenants.tenant")),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="hm_calibration_views", to="jobs.job")),
                ("hiring_manager", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="hm_calibration_entries", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "hm_calibration_views", "ordering": ["-created_at"]},
        ),

        # 12. HMOfferApproval
        migrations.CreateModel(
            name="HMOfferApproval",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("candidate_name", models.CharField(blank=True, default="", max_length=255)),
                ("job_title", models.CharField(blank=True, default="", max_length=255)),
                ("offer_id", models.UUIDField(blank=True, null=True)),
                ("base_salary", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("total_comp", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("offer_details", models.JSONField(default=dict)),
                ("status", models.CharField(choices=[("pending","Pending"),("approved","Approved"),("rejected","Rejected"),("needs_revision","Needs Revision")], default="pending", max_length=20)),
                ("decision_note", models.TextField(blank=True, default="")),
                ("decided_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="hm_offer_approvals", to="tenants.tenant")),
                ("hiring_manager", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="hm_offer_approvals", to=settings.AUTH_USER_MODEL)),
                ("recruiter", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="recruiter_hm_offer_approvals", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "hm_offer_approvals", "ordering": ["-created_at"]},
        ),

        # 13. RecruiterManagerNote
        migrations.CreateModel(
            name="RecruiterManagerNote",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("note_type", models.CharField(default="general", max_length=30)),
                ("body", models.TextField()),
                ("is_pinned", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="recruiter_manager_notes", to="tenants.tenant")),
                ("job", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="recruiter_manager_notes", to="jobs.job")),
                ("author", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="authored_collab_notes", to=settings.AUTH_USER_MODEL)),
                ("tagged_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="tagged_collab_notes", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "hm_recruiter_manager_notes", "ordering": ["-created_at"]},
        ),

        # 14. ManagerTrainingPrompt
        migrations.CreateModel(
            name="ManagerTrainingPrompt",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("trigger_event", models.CharField(default="shortlist_review", max_length=50)),
                ("title", models.CharField(max_length=255)),
                ("body", models.TextField()),
                ("resource_url", models.URLField(blank=True, default="")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="manager_training_prompts", to="tenants.tenant")),
            ],
            options={"db_table": "hm_training_prompts", "ordering": ["trigger_event", "title"]},
        ),

        # 15. HMDashboardStat
        migrations.CreateModel(
            name="HMDashboardStat",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("computed_at", models.DateTimeField(auto_now=True)),
                ("open_reqs", models.IntegerField(default=0)),
                ("pending_approvals", models.IntegerField(default=0)),
                ("pending_feedback", models.IntegerField(default=0)),
                ("pending_decisions", models.IntegerField(default=0)),
                ("overdue_slas", models.IntegerField(default=0)),
                ("active_offers", models.IntegerField(default=0)),
                ("avg_ttf_days", models.DecimalField(decimal_places=1, default=0, max_digits=6)),
                ("reqs_at_risk", models.IntegerField(default=0)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="hm_dashboard_stats", to="tenants.tenant")),
                ("hiring_manager", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="hm_dashboard_stats", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "hm_dashboard_stats", "ordering": ["-computed_at"]},
        ),
    ]
