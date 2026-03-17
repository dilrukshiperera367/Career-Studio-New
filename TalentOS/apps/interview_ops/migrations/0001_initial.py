# Generated migration for apps.interview_ops

import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("applications", "0001_initial"),
        ("candidates", "0001_initial"),
        ("jobs", "0001_initial"),
        ("tenants", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. InterviewPlanTemplate
        migrations.CreateModel(
            name="InterviewPlanTemplate",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("job_family", models.CharField(blank=True, default="", max_length=150)),
                ("job_level", models.CharField(choices=[("ic1","IC1 — Entry"),("ic2","IC2 — Mid"),("ic3","IC3 — Senior"),("ic4","IC4 — Staff"),("ic5","IC5 — Principal"),("m1","M1 — Manager"),("m2","M2 — Senior Manager"),("m3","M3 — Director"),("m4","M4 — VP+"),("exec","Executive"),("any","Any Level")], default="any", max_length=20)),
                ("description", models.TextField(blank=True, default="")),
                ("is_active", models.BooleanField(default=True)),
                ("total_duration_minutes", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="interview_plan_templates", to="tenants.tenant")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_interview_plans", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "interview_plan_templates", "ordering": ["job_family","job_level","name"]},
        ),
        migrations.AddIndex(
            model_name="interviewplantemplate",
            index=models.Index(fields=["tenant","job_family","job_level"], name="ipt_tenant_family_level_idx"),
        ),

        # 2. InterviewPlanStage
        migrations.CreateModel(
            name="InterviewPlanStage",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("stage_type", models.CharField(choices=[("phone_screen","Phone Screen"),("recruiter_screen","Recruiter Screen"),("hiring_manager_screen","Hiring Manager Screen"),("technical","Technical Interview"),("system_design","System Design"),("coding","Coding Assessment"),("case_study","Case Study"),("behavioral","Behavioral Interview"),("panel","Panel Interview"),("presentation","Presentation"),("culture_fit","Culture / Values"),("executive","Executive Interview"),("reference_check","Reference Check"),("take_home","Take-Home Exercise"),("onsite","Onsite Loop"),("other","Other")], default="phone_screen", max_length=30)),
                ("name", models.CharField(max_length=150)),
                ("order", models.PositiveIntegerField(default=0)),
                ("duration_minutes", models.IntegerField(default=45)),
                ("min_interviewers", models.IntegerField(default=1)),
                ("max_interviewers", models.IntegerField(default=3)),
                ("required_competencies", models.JSONField(blank=True, default=list)),
                ("notes_template_id", models.UUIDField(blank=True, null=True)),
                ("instructions", models.TextField(blank=True, default="")),
                ("scorecard_required", models.BooleanField(default=True)),
                ("feedback_deadline_hours", models.IntegerField(default=24)),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="stages", to="interview_ops.interviewplantemplate")),
            ],
            options={"db_table": "interview_plan_stages", "ordering": ["plan","order"]},
        ),
        migrations.AlterUniqueTogether(
            name="interviewplanstage",
            unique_together={("plan","order")},
        ),

        # 3. CompetencyQuestionBank
        migrations.CreateModel(
            name="CompetencyQuestionBank",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("competency", models.CharField(max_length=150)),
                ("job_family", models.CharField(blank=True, default="", max_length=150)),
                ("description", models.TextField(blank=True, default="")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="question_banks", to="tenants.tenant")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_question_banks", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "competency_question_banks", "ordering": ["competency","name"]},
        ),
        migrations.AddIndex(
            model_name="competencyquestionbank",
            index=models.Index(fields=["tenant","competency"], name="cqb_tenant_competency_idx"),
        ),

        # 4. InterviewQuestion
        migrations.CreateModel(
            name="InterviewQuestion",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("text", models.TextField()),
                ("follow_ups", models.JSONField(blank=True, default=list)),
                ("question_type", models.CharField(choices=[("behavioral","Behavioral (STAR)"),("situational","Situational"),("technical","Technical"),("hypothetical","Hypothetical"),("case","Case / Problem Solving"),("culture","Culture / Values"),("motivation","Motivation / Career")], default="behavioral", max_length=20)),
                ("difficulty", models.CharField(choices=[("easy","Easy"),("medium","Medium"),("hard","Hard"),("expert","Expert")], default="medium", max_length=10)),
                ("scoring_rubric", models.TextField(blank=True, default="")),
                ("ideal_answer_notes", models.TextField(blank=True, default="")),
                ("tags", models.JSONField(blank=True, default=list)),
                ("usage_count", models.IntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("bank", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="questions", to="interview_ops.competencyquestionbank")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_interview_questions", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "interview_questions", "ordering": ["bank","difficulty","question_type"]},
        ),
        migrations.AddIndex(
            model_name="interviewquestion",
            index=models.Index(fields=["bank","difficulty"], name="iq_bank_difficulty_idx"),
        ),

        # 5. InterviewKit
        migrations.CreateModel(
            name="InterviewKit",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("competencies_covered", models.JSONField(blank=True, default=list)),
                ("interviewer_instructions", models.TextField(blank=True, default="")),
                ("candidate_instructions", models.TextField(blank=True, default="")),
                ("time_allocation", models.JSONField(blank=True, default=dict)),
                ("is_published", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="interview_kits", to="tenants.tenant")),
                ("plan_stage", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="kits", to="interview_ops.interviewplanstage")),
                ("job", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="interview_kits", to="jobs.job")),
                ("interview", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="kits", to="applications.interview")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_kits", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "interview_kits", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="interviewkit",
            index=models.Index(fields=["tenant","job"], name="ik_tenant_job_idx"),
        ),

        # 6. InterviewKitQuestion
        migrations.CreateModel(
            name="InterviewKitQuestion",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("custom_question_text", models.TextField(blank=True, default="")),
                ("order", models.PositiveIntegerField(default=0)),
                ("weight", models.FloatField(default=1.0)),
                ("required", models.BooleanField(default=True)),
                ("time_minutes", models.IntegerField(default=5)),
                ("notes", models.TextField(blank=True, default="")),
                ("kit", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="kit_questions", to="interview_ops.interviewkit")),
                ("question", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="kit_usages", to="interview_ops.interviewquestion")),
            ],
            options={"db_table": "interview_kit_questions", "ordering": ["kit","order"]},
        ),

        # 7. InterviewerTrainingModule
        migrations.CreateModel(
            name="InterviewerTrainingModule",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("module_type", models.CharField(choices=[("bias_awareness","Bias Awareness"),("legal_compliance","Legal / Compliance"),("structured_interviewing","Structured Interviewing"),("technical_calibration","Technical Calibration"),("feedback_writing","Feedback Writing"),("dei_practices","DEI Practices"),("scorecard_usage","Scorecard Usage"),("onboarding","Interviewer Onboarding"),("refresher","Refresher"),("custom","Custom")], default="structured_interviewing", max_length=30)),
                ("description", models.TextField(blank=True, default="")),
                ("content_url", models.URLField(blank=True, default="")),
                ("duration_minutes", models.IntegerField(default=30)),
                ("passing_score", models.IntegerField(default=80)),
                ("is_mandatory", models.BooleanField(default=False)),
                ("recertification_months", models.IntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="training_modules", to="tenants.tenant")),
            ],
            options={"db_table": "interviewer_training_modules", "ordering": ["module_type","name"]},
        ),

        # 8. InterviewerCertification
        migrations.CreateModel(
            name="InterviewerCertification",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("enrolled","Enrolled"),("in_progress","In Progress"),("passed","Passed"),("failed","Failed"),("expired","Expired"),("waived","Waived")], default="enrolled", max_length=20)),
                ("score", models.IntegerField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("expires_at", models.DateField(blank=True, null=True)),
                ("certificate_url", models.URLField(blank=True, default="")),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="interviewer_certifications", to="tenants.tenant")),
                ("interviewer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="interview_certifications", to=settings.AUTH_USER_MODEL)),
                ("module", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="certifications", to="interview_ops.interviewertrainingmodule")),
            ],
            options={"db_table": "interviewer_certifications", "ordering": ["-created_at"]},
        ),
        migrations.AlterUniqueTogether(
            name="interviewercertification",
            unique_together={("interviewer","module")},
        ),
        migrations.AddIndex(
            model_name="interviewercertification",
            index=models.Index(fields=["tenant","interviewer","status"], name="ic_tenant_iv_status_idx"),
        ),

        # 9. InterviewPrepBrief
        migrations.CreateModel(
            name="InterviewPrepBrief",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("candidate_summary", models.TextField(blank=True, default="")),
                ("role_context", models.TextField(blank=True, default="")),
                ("suggested_questions", models.JSONField(blank=True, default=list)),
                ("areas_to_probe", models.JSONField(blank=True, default=list)),
                ("dos_and_donts", models.JSONField(blank=True, default=dict)),
                ("logistics_notes", models.TextField(blank=True, default="")),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("viewed_at", models.DateTimeField(blank=True, null=True)),
                ("is_sent", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="prep_briefs", to="tenants.tenant")),
                ("interview", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="prep_briefs", to="applications.interview")),
                ("interviewer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="prep_briefs", to=settings.AUTH_USER_MODEL)),
                ("kit", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="prep_briefs", to="interview_ops.interviewkit")),
            ],
            options={"db_table": "interview_prep_briefs", "ordering": ["-created_at"]},
        ),
        migrations.AlterUniqueTogether(
            name="interviewprepbrief",
            unique_together={("interview","interviewer")},
        ),

        # 10. PanelRoleAssignment
        migrations.CreateModel(
            name="PanelRoleAssignment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("role", models.CharField(choices=[("lead","Lead Interviewer"),("co_interviewer","Co-Interviewer"),("note_taker","Note-Taker"),("technical","Technical Evaluator"),("behavioral","Behavioral Evaluator"),("culture","Culture / Values Evaluator"),("observer","Observer (Shadowing)"),("hiring_manager","Hiring Manager"),("recruiter","Recruiter"),("executive","Executive Sponsor")], default="co_interviewer", max_length=20)),
                ("competencies_to_assess", models.JSONField(blank=True, default=list)),
                ("is_decision_maker", models.BooleanField(default=False)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="panel_role_assignments", to="tenants.tenant")),
                ("interview", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="panel_roles", to="applications.interview")),
                ("interviewer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="panel_role_assignments", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "panel_role_assignments", "ordering": ["interview","role"]},
        ),
        migrations.AlterUniqueTogether(
            name="panelroleassignment",
            unique_together={("interview","interviewer")},
        ),
        migrations.AddIndex(
            model_name="panelroleassignment",
            index=models.Index(fields=["tenant","interview"], name="pra_tenant_interview_idx"),
        ),

        # 11. AvailabilitySlot
        migrations.CreateModel(
            name="AvailabilitySlot",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("start_datetime", models.DateTimeField()),
                ("end_datetime", models.DateTimeField()),
                ("status", models.CharField(choices=[("available","Available"),("tentative","Tentative"),("blocked","Blocked"),("booked","Booked")], default="available", max_length=20)),
                ("timezone", models.CharField(default="UTC", max_length=50)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="availability_slots", to="tenants.tenant")),
                ("interviewer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="availability_slots", to=settings.AUTH_USER_MODEL)),
                ("booked_interview", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="booked_slots", to="applications.interview")),
            ],
            options={"db_table": "availability_slots", "ordering": ["interviewer","start_datetime"]},
        ),
        migrations.AddIndex(
            model_name="availabilityslot",
            index=models.Index(fields=["tenant","interviewer","start_datetime"], name="as_tenant_iv_start_idx"),
        ),
        migrations.AddIndex(
            model_name="availabilityslot",
            index=models.Index(fields=["tenant","start_datetime","status"], name="as_tenant_start_status_idx"),
        ),

        # 12. ConflictOfInterestDisclosure
        migrations.CreateModel(
            name="ConflictOfInterestDisclosure",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("has_conflict", models.BooleanField(default=False)),
                ("conflict_type", models.CharField(blank=True, choices=[("personal_relationship","Personal Relationship"),("family","Family Member"),("former_colleague","Former Colleague"),("financial_interest","Financial Interest"),("competitor","Competitor Affiliation"),("social_connection","Social / Online Connection"),("managed_previously","Previously Managed Candidate"),("other","Other")], default="", max_length=30)),
                ("description", models.TextField(blank=True, default="")),
                ("resolution", models.CharField(choices=[("pending","Pending Review"),("cleared","Cleared — No Conflict"),("recused","Recused from Panel"),("waived","Waived by Recruiter")], default="pending", max_length=20)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="coi_disclosures", to="tenants.tenant")),
                ("interview", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="coi_disclosures", to="applications.interview")),
                ("interviewer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="coi_disclosures", to=settings.AUTH_USER_MODEL)),
                ("resolved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="resolved_coi_disclosures", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "coi_disclosures", "ordering": ["-created_at"]},
        ),
        migrations.AlterUniqueTogether(
            name="conflictofinterestdisclosure",
            unique_together={("interview","interviewer")},
        ),
        migrations.AddIndex(
            model_name="conflictofinterestdisclosure",
            index=models.Index(fields=["tenant","interview"], name="coi_tenant_interview_idx"),
        ),

        # 13. NoteTakingTemplate
        migrations.CreateModel(
            name="NoteTakingTemplate",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("sections", models.JSONField(blank=True, default=list)),
                ("description", models.TextField(blank=True, default="")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="note_templates", to="tenants.tenant")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_note_templates", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "note_taking_templates", "ordering": ["name"]},
        ),

        # 14. InterviewNote
        migrations.CreateModel(
            name="InterviewNote",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("filled_sections", models.JSONField(blank=True, default=dict)),
                ("free_text_notes", models.TextField(blank=True, default="")),
                ("is_locked", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="interview_notes", to="tenants.tenant")),
                ("interview", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="structured_notes", to="applications.interview")),
                ("interviewer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="interview_notes", to=settings.AUTH_USER_MODEL)),
                ("template", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="interview_notes", to="interview_ops.notetakingtemplate")),
            ],
            options={"db_table": "interview_notes", "ordering": ["-created_at"]},
        ),
        migrations.AlterUniqueTogether(
            name="interviewNote".lower(),
            unique_together={("interview","interviewer")},
        ),

        # 15. FeedbackLock
        migrations.CreateModel(
            name="FeedbackLock",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("locked","Locked — Awaiting Submission"),("unlocked","Unlocked"),("unlocked_by_admin","Unlocked by Admin Override")], default="locked", max_length=20)),
                ("unlocked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="feedback_locks", to="tenants.tenant")),
                ("interview", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="feedback_locks", to="applications.interview")),
                ("interviewer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="feedback_locks", to=settings.AUTH_USER_MODEL)),
                ("unlocked_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="unlocked_feedback", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "feedback_locks", "ordering": ["-created_at"]},
        ),
        migrations.AlterUniqueTogether(
            name="feedbacklock",
            unique_together={("interview","interviewer")},
        ),

        # 16. DebriefWorkspace
        migrations.CreateModel(
            name="DebriefWorkspace",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("final_decision", models.CharField(choices=[("strong_hire","Strong Hire"),("hire","Hire"),("lean_hire","Lean Hire"),("lean_no_hire","Lean No Hire"),("no_hire","No Hire"),("strong_no_hire","Strong No Hire"),("hold","Hold"),("pending","Pending")], default="pending", max_length=20)),
                ("decision_rationale", models.TextField(blank=True, default="")),
                ("decision_made_at", models.DateTimeField(blank=True, null=True)),
                ("score_variance_flagged", models.BooleanField(default=False)),
                ("score_variance_notes", models.TextField(blank=True, default="")),
                ("fairness_flag", models.BooleanField(default=False)),
                ("fairness_flag_reason", models.TextField(blank=True, default="")),
                ("shared_notes", models.TextField(blank=True, default="")),
                ("action_items", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="debrief_workspaces", to="tenants.tenant")),
                ("application", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="debrief_workspaces", to="applications.application")),
                ("debrief_session", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="workspace", to="applications.debriefsession")),
                ("decision_made_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="debrief_decisions", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "debrief_workspaces", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="debriefworkspace",
            index=models.Index(fields=["tenant","application"], name="dw_tenant_application_idx"),
        ),

        # 17. DebriefVote
        migrations.CreateModel(
            name="DebriefVote",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("vote", models.CharField(choices=[("strong_hire","Strong Hire"),("hire","Hire"),("lean_hire","Lean Hire"),("lean_no_hire","Lean No Hire"),("no_hire","No Hire"),("strong_no_hire","Strong No Hire"),("abstain","Abstain")], max_length=20)),
                ("rationale", models.TextField(blank=True, default="")),
                ("top_strength", models.TextField(blank=True, default="")),
                ("top_concern", models.TextField(blank=True, default="")),
                ("is_submitted", models.BooleanField(default=False)),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="votes", to="interview_ops.debriefworkspace")),
                ("voter", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="debrief_votes", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "debrief_votes", "ordering": ["workspace","voter"]},
        ),
        migrations.AlterUniqueTogether(
            name="debriefvote",
            unique_together={("workspace","voter")},
        ),

        # 18. CalibrationAudit
        migrations.CreateModel(
            name="CalibrationAudit",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("avg_score_given", models.FloatField(blank=True, null=True)),
                ("median_score_given", models.FloatField(blank=True, null=True)),
                ("team_avg_score", models.FloatField(blank=True, null=True)),
                ("score_std_dev", models.FloatField(blank=True, null=True)),
                ("variance_from_team", models.FloatField(blank=True, null=True)),
                ("interviews_evaluated", models.IntegerField(default=0)),
                ("consistency_score", models.FloatField(blank=True, null=True)),
                ("is_outlier", models.BooleanField(default=False)),
                ("outlier_notes", models.TextField(blank=True, default="")),
                ("period_start", models.DateField(blank=True, null=True)),
                ("period_end", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="calibration_audits", to="tenants.tenant")),
                ("interviewer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="calibration_audits", to=settings.AUTH_USER_MODEL)),
                ("job", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="calibration_audits", to="jobs.job")),
            ],
            options={"db_table": "calibration_audits", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="calibrationaudit",
            index=models.Index(fields=["tenant","interviewer","job"], name="ca_tenant_iv_job_idx"),
        ),

        # 19. ScorecardReminder
        migrations.CreateModel(
            name="ScorecardReminder",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("trigger", models.CharField(choices=[("approaching_deadline","Approaching Deadline"),("past_deadline","Past Deadline"),("missing_after_interview","Missing After Interview"),("escalation","Escalation to Hiring Manager")], max_length=30)),
                ("sent_at", models.DateTimeField(auto_now_add=True)),
                ("reminder_count", models.IntegerField(default=1)),
                ("resolved", models.BooleanField(default=False)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="scorecard_reminders", to="tenants.tenant")),
                ("interview", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="scorecard_reminders", to="applications.interview")),
                ("interviewer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="scorecard_reminders", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "scorecard_reminders", "ordering": ["-sent_at"]},
        ),
        migrations.AddIndex(
            model_name="scorecardreminder",
            index=models.Index(fields=["tenant","interview","interviewer"], name="sr_tenant_iv_interviewer_idx"),
        ),

        # 20. InterviewerWorkload
        migrations.CreateModel(
            name="InterviewerWorkload",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("week_start", models.DateField()),
                ("max_interviews_per_week", models.IntegerField(default=5)),
                ("max_hours_per_week", models.FloatField(default=5.0)),
                ("scheduled_count", models.IntegerField(default=0)),
                ("completed_count", models.IntegerField(default=0)),
                ("scheduled_hours", models.FloatField(default=0.0)),
                ("is_overloaded", models.BooleanField(default=False)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="interviewer_workloads", to="tenants.tenant")),
                ("interviewer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="workload_records", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "interviewer_workloads", "ordering": ["-week_start"]},
        ),
        migrations.AlterUniqueTogether(
            name="interviewerworkload",
            unique_together={("interviewer","week_start")},
        ),
        migrations.AddIndex(
            model_name="interviewerworkload",
            index=models.Index(fields=["tenant","week_start"], name="iw_tenant_week_idx"),
        ),

        # 21. OnsiteAgenda
        migrations.CreateModel(
            name="OnsiteAgenda",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("candidate_name", models.CharField(blank=True, default="", max_length=255)),
                ("date", models.DateField(blank=True, null=True)),
                ("location", models.CharField(blank=True, default="", max_length=500)),
                ("arrival_instructions", models.TextField(blank=True, default="")),
                ("dress_code", models.CharField(blank=True, default="", max_length=100)),
                ("welcome_message", models.TextField(blank=True, default="")),
                ("is_published_to_candidate", models.BooleanField(default=False)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="onsite_agendas", to="tenants.tenant")),
                ("interview", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="onsite_agenda", to="applications.interview")),
            ],
            options={"db_table": "onsite_agendas", "ordering": ["-date"]},
        ),

        # 22. OnsiteAgendaSlot
        migrations.CreateModel(
            name="OnsiteAgendaSlot",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("slot_type", models.CharField(choices=[("interview","Interview"),("break","Break"),("lunch","Lunch"),("tour","Office Tour"),("intro","Team Introduction"),("presentation","Presentation"),("travel","Travel / Transit"),("other","Other")], default="interview", max_length=20)),
                ("title", models.CharField(max_length=255)),
                ("start_time", models.TimeField()),
                ("end_time", models.TimeField()),
                ("location", models.CharField(blank=True, default="", max_length=255)),
                ("notes", models.TextField(blank=True, default="")),
                ("order", models.PositiveIntegerField(default=0)),
                ("agenda", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="slots", to="interview_ops.onsiteagenda")),
                ("host", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="agenda_slots_hosted", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "onsite_agenda_slots", "ordering": ["agenda","order","start_time"]},
        ),

        # 23. TravelLogistics
        migrations.CreateModel(
            name="TravelLogistics",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("travel_required", models.BooleanField(default=False)),
                ("origin_city", models.CharField(blank=True, default="", max_length=150)),
                ("destination_city", models.CharField(blank=True, default="", max_length=150)),
                ("travel_date", models.DateField(blank=True, null=True)),
                ("return_date", models.DateField(blank=True, null=True)),
                ("booking_reference", models.CharField(blank=True, default="", max_length=255)),
                ("hotel_required", models.BooleanField(default=False)),
                ("hotel_name", models.CharField(blank=True, default="", max_length=255)),
                ("hotel_address", models.TextField(blank=True, default="")),
                ("hotel_confirmation", models.CharField(blank=True, default="", max_length=100)),
                ("reimbursement_status", models.CharField(choices=[("not_applicable","Not Applicable"),("pending_request","Pending Request"),("approved","Approved"),("submitted","Expenses Submitted"),("reimbursed","Reimbursed"),("declined","Declined")], default="not_applicable", max_length=25)),
                ("reimbursement_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("reimbursement_currency", models.CharField(default="USD", max_length=3)),
                ("expense_receipts", models.JSONField(blank=True, default=list)),
                ("special_instructions", models.TextField(blank=True, default="")),
                ("travel_contact_name", models.CharField(blank=True, default="", max_length=200)),
                ("travel_contact_email", models.EmailField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="travel_logistics", to="tenants.tenant")),
                ("interview", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="travel_logistics", to="applications.interview")),
            ],
            options={"db_table": "travel_logistics", "ordering": ["-created_at"]},
        ),

        # 24. InterviewerPerformanceRecord
        migrations.CreateModel(
            name="InterviewerPerformanceRecord",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("period_start", models.DateField()),
                ("period_end", models.DateField()),
                ("total_interviews", models.IntegerField(default=0)),
                ("completed_interviews", models.IntegerField(default=0)),
                ("cancelled_interviews", models.IntegerField(default=0)),
                ("avg_feedback_hours", models.FloatField(blank=True, null=True)),
                ("late_feedback_count", models.IntegerField(default=0)),
                ("missing_feedback_count", models.IntegerField(default=0)),
                ("avg_score_given", models.FloatField(blank=True, null=True)),
                ("score_variance", models.FloatField(blank=True, null=True)),
                ("hire_recommendation_count", models.IntegerField(default=0)),
                ("hire_recommendation_accuracy", models.FloatField(blank=True, null=True)),
                ("demographic_score_variance_flag", models.BooleanField(default=False)),
                ("fairness_score", models.FloatField(blank=True, null=True)),
                ("avg_candidate_rating", models.FloatField(blank=True, null=True)),
                ("certifications_current", models.BooleanField(default=True)),
                ("overdue_training_count", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="interviewer_performance", to="tenants.tenant")),
                ("interviewer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="performance_records", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "interviewer_performance_records", "ordering": ["-period_end"]},
        ),
        migrations.AlterUniqueTogether(
            name="interviewerperformancerecord",
            unique_together={("interviewer","period_start","period_end")},
        ),
        migrations.AddIndex(
            model_name="interviewerperformancerecord",
            index=models.Index(fields=["tenant","period_end"], name="ipr_tenant_period_end_idx"),
        ),

        # 25. NoShowPolicy
        migrations.CreateModel(
            name="NoShowPolicy",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("max_reschedule_attempts", models.IntegerField(default=2)),
                ("no_show_grace_period_minutes", models.IntegerField(default=10)),
                ("no_show_action", models.CharField(choices=[("auto_reject","Auto-Reject"),("hold","Place on Hold"),("notify_recruiter","Notify Recruiter")], default="notify_recruiter", max_length=30)),
                ("reminder_hours_before", models.JSONField(blank=True, default=list)),
                ("require_candidate_confirmation", models.BooleanField(default=True)),
                ("reschedule_deadline_hours", models.IntegerField(default=24)),
                ("is_default", models.BooleanField(default=False)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="no_show_policies", to="tenants.tenant")),
            ],
            options={"db_table": "no_show_policies", "ordering": ["name"]},
        ),

        # 26. CandidateInterviewReminder
        migrations.CreateModel(
            name="CandidateInterviewReminder",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("reminder_type", models.CharField(choices=[("confirmation","Interview Confirmation"),("reminder_48h","48-Hour Reminder"),("reminder_24h","24-Hour Reminder"),("reminder_2h","2-Hour Reminder"),("onsite_instructions","Onsite Instructions"),("video_link","Video Link / Join Instructions"),("agenda","Agenda Sent"),("reschedule_offer","Reschedule Offer"),("cancellation","Cancellation Notice"),("no_show_followup","No-Show Follow-Up")], max_length=30)),
                ("channel", models.CharField(choices=[("email","Email"),("sms","SMS"),("portal","Candidate Portal"),("whatsapp","WhatsApp")], default="email", max_length=20)),
                ("subject", models.CharField(blank=True, default="", max_length=255)),
                ("body", models.TextField(blank=True, default="")),
                ("sent_at", models.DateTimeField(auto_now_add=True)),
                ("delivered", models.BooleanField(default=False)),
                ("opened_at", models.DateTimeField(blank=True, null=True)),
                ("candidate_response", models.CharField(blank=True, default="", max_length=30)),
                ("responded_at", models.DateTimeField(blank=True, null=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="candidate_reminders", to="tenants.tenant")),
                ("interview", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="candidate_reminders", to="applications.interview")),
                ("candidate", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="interview_reminders", to="candidates.candidate")),
            ],
            options={"db_table": "candidate_interview_reminders", "ordering": ["-sent_at"]},
        ),
        migrations.AddIndex(
            model_name="candidateinterviewreminder",
            index=models.Index(fields=["tenant","interview"], name="cir_tenant_interview_idx"),
        ),
        migrations.AddIndex(
            model_name="candidateinterviewreminder",
            index=models.Index(fields=["tenant","candidate"], name="cir_tenant_candidate_idx"),
        ),

        # 27. PanelDiversitySnapshot
        migrations.CreateModel(
            name="PanelDiversitySnapshot",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("panel_size", models.IntegerField(default=0)),
                ("gender_diversity_met", models.BooleanField(blank=True, null=True)),
                ("ethnic_diversity_met", models.BooleanField(blank=True, null=True)),
                ("diversity_policy_met", models.BooleanField(blank=True, null=True)),
                ("diversity_policy_name", models.CharField(blank=True, default="", max_length=150)),
                ("notes", models.TextField(blank=True, default="")),
                ("checked_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="panel_diversity_snapshots", to="tenants.tenant")),
                ("interview", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="panel_diversity_snapshot", to="applications.interview")),
                ("checked_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="panel_diversity_checks", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "panel_diversity_snapshots", "ordering": ["-checked_at"]},
        ),
    ]
