# Generated migration for Feature 6: Screening & Assessment Orchestration
# Expands apps/assessments with 10 new models

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assessments', '0001_initial'),
        ('applications', '0005_offer_esign_document_url_offer_esign_envelope_id_and_more'),
        ('jobs', '0001_initial'),
        ('tenants', '0004_delete_subscription'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── Expand existing AssessmentVendor ──────────────────────────────────
        migrations.AddField(
            model_name='assessmentvendor',
            name='anti_cheating_features',
            field=models.JSONField(
                blank=True, default=list,
                help_text='["proctoring", "plagiarism_detection", "tab_switch_detection", "id_verification"]'
            ),
        ),

        # ── Expand existing AssessmentCatalogItem ─────────────────────────────
        migrations.AlterField(
            model_name='assessmentcatalogitem',
            name='assessment_type',
            field=models.CharField(
                max_length=30,
                default='custom',
                choices=[
                    ('coding', 'Coding Challenge'),
                    ('writing', 'Writing Assessment'),
                    ('case_study', 'Case Study'),
                    ('work_sample', 'Work Sample'),
                    ('portfolio', 'Portfolio Review'),
                    ('cognitive', 'Cognitive Ability'),
                    ('personality', 'Personality / Values'),
                    ('language', 'Language Proficiency'),
                    ('sjt', 'Situational Judgment Test'),
                    ('async_text', 'Async Text Response'),
                    ('async_audio', 'Async Audio Response'),
                    ('async_video', 'Async Video Response'),
                    ('credential', 'Credential / License Verification'),
                    ('custom', 'Custom'),
                ],
            ),
        ),
        migrations.AddField(
            model_name='assessmentcatalogitem',
            name='normalization_method',
            field=models.CharField(
                max_length=30, default='percentile',
                help_text='How raw scores are normalized: percentile, z_score, band, raw'
            ),
        ),
        migrations.AddField(
            model_name='assessmentcatalogitem',
            name='norm_reference_group',
            field=models.CharField(
                max_length=255, blank=True, default='',
                help_text="Reference population for normalization (e.g. 'SWE US 2024')"
            ),
        ),
        migrations.AddField(
            model_name='assessmentcatalogitem',
            name='anti_cheating_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='assessmentcatalogitem',
            name='anti_cheating_config',
            field=models.JSONField(
                default=dict, blank=True,
                help_text='{"proctoring": true, "plagiarism_detection": true}'
            ),
        ),

        # ── Expand existing AssessmentOrder ───────────────────────────────────
        migrations.AddField(
            model_name='assessmentorder',
            name='anti_cheating_flags',
            field=models.JSONField(
                default=list, blank=True,
                help_text='[{"flag": "tab_switch", "count": 3, "severity": "medium"}]'
            ),
        ),
        migrations.AddField(
            model_name='assessmentorder',
            name='anti_cheating_cleared',
            field=models.BooleanField(
                null=True, blank=True,
                help_text='Human reviewer cleared anti-cheating flags'
            ),
        ),

        # ── Expand existing AssessmentResult ──────────────────────────────────
        migrations.AddField(
            model_name='assessmentresult',
            name='normalized_score',
            field=models.FloatField(
                null=True, blank=True,
                help_text="Score normalized per catalog item's normalization_method"
            ),
        ),
        migrations.AddField(
            model_name='assessmentresult',
            name='explainability_payload',
            field=models.JSONField(
                default=dict, blank=True,
                help_text='Structured explanation of how score was derived (for audits/appeals)'
            ),
        ),

        # ── Expand existing AssessmentWaiver (add new reason choices) ─────────
        migrations.AlterField(
            model_name='assessmentwaiver',
            name='reason',
            field=models.CharField(
                max_length=30,
                choices=[
                    ('accommodation', 'Disability Accommodation'),
                    ('strong_referral', 'Strong Referral'),
                    ('repeat_candidate', 'Repeat / Known Candidate'),
                    ('exec_override', 'Executive Override'),
                    ('portfolio_substitution', 'Portfolio Substitution'),
                    ('prior_certification', 'Prior Certification on File'),
                    ('other', 'Other'),
                ],
            ),
        ),

        # ── NEW: ScreeningQuestionnaire ───────────────────────────────────────
        migrations.CreateModel(
            name='ScreeningQuestionnaire',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, default='')),
                ('is_active', models.BooleanField(default=True)),
                ('blind_review_enforced', models.BooleanField(default=False, help_text='Strip PII from reviewer view during screen review')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='screening_questionnaires', to='tenants.tenant')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_questionnaires', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'screening_questionnaires', 'ordering': ['-created_at']},
        ),

        # ── NEW: ScreeningQuestion ────────────────────────────────────────────
        migrations.CreateModel(
            name='ScreeningQuestion',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('order', models.PositiveIntegerField(default=0)),
                ('question_text', models.TextField()),
                ('question_type', models.CharField(
                    max_length=20, default='yes_no',
                    choices=[
                        ('yes_no', 'Yes / No'),
                        ('multiple_choice', 'Multiple Choice'),
                        ('single_choice', 'Single Choice'),
                        ('short_text', 'Short Text'),
                        ('long_text', 'Long Text'),
                        ('numeric', 'Numeric'),
                        ('date', 'Date'),
                        ('file_upload', 'File Upload'),
                        ('async_audio', 'Async Audio Response'),
                        ('async_video', 'Async Video Response'),
                        ('rating_scale', 'Rating Scale'),
                    ]
                )),
                ('options', models.JSONField(blank=True, default=list, help_text='For choice types: [{"value": "yes", "label": "Yes"}, ...]')),
                ('is_required', models.BooleanField(default=True)),
                ('is_knockout', models.BooleanField(default=False, help_text='If candidate answers disqualifying value, application is auto-rejected')),
                ('knockout_disqualifying_values', models.JSONField(blank=True, default=list, help_text='["no"] — values that trigger knockout disqualification')),
                ('knockout_reason_code', models.CharField(blank=True, default='', max_length=100, help_text='Links to ScreeningDisqualificationReason.code')),
                ('weight', models.FloatField(default=0.0, help_text='Weight of this question in overall screening score (0–100)')),
                ('ideal_answer', models.JSONField(default=None, null=True, blank=True, help_text='Answer value(s) that score full weight points')),
                ('scoring_rubric', models.JSONField(blank=True, default=dict, help_text='{"value": score} map for partial credit')),
                ('help_text_for_candidate', models.TextField(blank=True, default='')),
                ('questionnaire', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='questions', to='assessments.screeningquestionnaire')),
            ],
            options={'db_table': 'screening_questions', 'ordering': ['questionnaire', 'order']},
        ),

        # ── NEW: ScreeningQuestionnaireResponse ───────────────────────────────
        migrations.CreateModel(
            name='ScreeningQuestionnaireResponse',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('answers', models.JSONField(default=dict, help_text='{"<question_id>": <answer_value>}')),
                ('computed_score', models.FloatField(null=True, blank=True, help_text='Weighted total score after applying question weights/rubrics')),
                ('knockout_triggered', models.BooleanField(default=False)),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='questionnaire_responses', to='tenants.tenant')),
                ('application', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='screening_responses', to='applications.application')),
                ('questionnaire', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='responses', to='assessments.screeningquestionnaire')),
                ('knockout_question', models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, related_name='triggered_knockouts', to='assessments.screeningquestion')),
            ],
            options={'db_table': 'screening_questionnaire_responses'},
        ),
        migrations.AlterUniqueTogether(
            name='screeningquestionnaireresponse',
            unique_together={('application', 'questionnaire')},
        ),

        # ── NEW: ScreeningRuleSet ─────────────────────────────────────────────
        migrations.CreateModel(
            name='ScreeningRuleSet',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, default='')),
                ('is_template', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('auto_advance_threshold', models.FloatField(null=True, blank=True, help_text='Candidates scoring ≥ this weighted total are auto-advanced')),
                ('auto_reject_threshold', models.FloatField(null=True, blank=True, help_text='Candidates scoring < this weighted total are auto-rejected')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='screening_rule_sets', to='tenants.tenant')),
                ('job', models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, related_name='screening_rule_sets', to='jobs.job')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_rule_sets', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'screening_rule_sets', 'ordering': ['-created_at']},
        ),

        # ── NEW: ScreeningRule ────────────────────────────────────────────────
        migrations.CreateModel(
            name='ScreeningRule',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('order', models.PositiveIntegerField(default=0)),
                ('rule_type', models.CharField(
                    max_length=30,
                    choices=[
                        ('must_have', 'Must-Have Requirement'),
                        ('preferred', 'Preferred Requirement'),
                        ('nice_to_have', 'Nice-to-Have'),
                        ('disqualifier', 'Disqualifier'),
                        ('credential', 'Credential / License'),
                        ('experience_years', 'Years of Experience'),
                        ('education', 'Education Level'),
                        ('skill', 'Skill Match'),
                        ('location', 'Location / Commute'),
                        ('availability', 'Availability / Start Date'),
                        ('salary', 'Salary Expectation'),
                        ('questionnaire_score', 'Questionnaire Score'),
                        ('assessment_score', 'Assessment Score'),
                        ('custom', 'Custom Logic'),
                    ]
                )),
                ('field_path', models.CharField(blank=True, default='', max_length=255, help_text="Dot-path into candidate/application data: e.g. 'years_experience', 'skills'")),
                ('operator', models.CharField(
                    max_length=20, default='eq',
                    choices=[
                        ('eq', 'Equals'), ('neq', 'Not Equals'),
                        ('gte', 'Greater Than or Equal'), ('lte', 'Less Than or Equal'),
                        ('contains', 'Contains'), ('not_contains', 'Does Not Contain'),
                        ('in', 'In List'), ('not_in', 'Not In List'),
                        ('exists', 'Exists / Present'), ('not_exists', 'Not Present'),
                    ]
                )),
                ('expected_value', models.JSONField(default=None, null=True, blank=True, help_text='Value to compare against')),
                ('weight', models.FloatField(default=1.0, help_text='Weight in overall score when rule passes (0–100)')),
                ('is_knockout', models.BooleanField(default=False, help_text='Failure immediately disqualifies candidate')),
                ('knockout_reason_code', models.CharField(blank=True, default='', max_length=100)),
                ('description', models.CharField(blank=True, default='', max_length=500)),
                ('rule_set', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rules', to='assessments.screeningruleset')),
            ],
            options={'db_table': 'screening_rules', 'ordering': ['rule_set', 'order']},
        ),

        # ── NEW: ScreeningRuleEvaluation ──────────────────────────────────────
        migrations.CreateModel(
            name='ScreeningRuleEvaluation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('total_score', models.FloatField(default=0.0)),
                ('max_possible_score', models.FloatField(default=0.0)),
                ('passed_rules', models.JSONField(blank=True, default=list)),
                ('failed_rules', models.JSONField(blank=True, default=list)),
                ('auto_decision', models.CharField(blank=True, default='', max_length=20, help_text='advance | reject | review — set by rule engine')),
                ('explanation_payload', models.JSONField(blank=True, default=dict, help_text='Structured explanation: which rules passed/failed and why')),
                ('evaluated_at', models.DateTimeField(auto_now_add=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='screening_rule_evaluations', to='tenants.tenant')),
                ('application', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rule_evaluations', to='applications.application')),
                ('rule_set', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='evaluations', to='assessments.screeningruleset')),
                ('knockout_rule', models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, related_name='triggered_evaluations', to='assessments.screeningrule')),
            ],
            options={
                'db_table': 'screening_rule_evaluations',
                'ordering': ['-evaluated_at'],
                'indexes': [models.Index(fields=['application'], name='scr_rule_eval_app_idx')],
            },
        ),

        # ── NEW: CredentialVerification ───────────────────────────────────────
        migrations.CreateModel(
            name='CredentialVerification',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('credential_type', models.CharField(max_length=255, help_text='e.g. CPA, AWS Solutions Architect, State Bar License, RN License')),
                ('credential_number', models.CharField(blank=True, default='', max_length=255)),
                ('issuing_authority', models.CharField(blank=True, default='', max_length=255)),
                ('issued_date', models.DateField(null=True, blank=True)),
                ('expiry_date', models.DateField(null=True, blank=True)),
                ('status', models.CharField(
                    max_length=20, default='pending',
                    choices=[
                        ('pending', 'Pending'), ('in_progress', 'In Progress'),
                        ('verified', 'Verified'), ('failed', 'Failed / Not Verified'),
                        ('expired', 'Credential Expired'), ('waived', 'Waived'),
                    ]
                )),
                ('verification_method', models.CharField(blank=True, default='', max_length=50, help_text='manual | vendor_api | primary_source')),
                ('vendor_reference_id', models.CharField(blank=True, default='', max_length=255)),
                ('verified_at', models.DateTimeField(null=True, blank=True)),
                ('notes', models.TextField(blank=True, default='')),
                ('document_url', models.URLField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='credential_verifications', to='tenants.tenant')),
                ('application', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='credential_verifications', to='applications.application')),
                ('verified_by', models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, related_name='credential_verifications_performed', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'credential_verifications', 'ordering': ['-created_at']},
        ),

        # ── NEW: ScreeningDecisionReason ──────────────────────────────────────
        migrations.CreateModel(
            name='ScreeningDecisionReason',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('code', models.CharField(max_length=100)),
                ('label', models.CharField(max_length=255)),
                ('category', models.CharField(
                    max_length=20,
                    choices=[
                        ('pass', 'Pass / Advance'), ('hold', 'Hold for Review'),
                        ('reject', 'Reject / Disqualify'), ('appeal', 'Under Appeal'),
                    ]
                )),
                ('description', models.TextField(blank=True, default='')),
                ('requires_documentation', models.BooleanField(default=False)),
                ('is_protected_class_sensitive', models.BooleanField(default=False, help_text='Reason may trigger bias review; requires extra audit logging')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='screening_decision_reasons', to='tenants.tenant')),
            ],
            options={
                'db_table': 'screening_decision_reasons',
                'ordering': ['category', 'label'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='screeningdecisionreason',
            unique_together={('tenant', 'code')},
        ),

        # ── NEW: ScreeningDecision ────────────────────────────────────────────
        migrations.CreateModel(
            name='ScreeningDecision',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('decision', models.CharField(
                    max_length=30,
                    choices=[
                        ('advance', 'Advance'), ('hold', 'Hold'), ('reject', 'Reject'),
                        ('waive_assessment', 'Waive Assessment'), ('request_more_info', 'Request More Info'),
                    ]
                )),
                ('is_automated', models.BooleanField(default=False, help_text='True if decision was made by rule engine without human')),
                ('notes', models.TextField(blank=True, default='')),
                ('blind_review_active', models.BooleanField(default=False)),
                ('explanation_summary', models.TextField(blank=True, default='', help_text='Plain-language explanation of why this decision was reached')),
                ('decided_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='screening_decisions', to='tenants.tenant')),
                ('application', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='screening_decisions', to='applications.application')),
                ('reason', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='decisions', to='assessments.screeningdecisionreason')),
                ('rule_evaluation', models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, related_name='decisions', to='assessments.screeningruleevaluation')),
                ('decided_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='screening_decisions_made', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'screening_decisions',
                'ordering': ['-decided_at'],
                'indexes': [models.Index(fields=['application'], name='scr_decision_app_idx')],
            },
        ),

        # ── NEW: ScreenReviewQueue ────────────────────────────────────────────
        migrations.CreateModel(
            name='ScreenReviewQueue',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('priority', models.CharField(max_length=10, default='normal', choices=[('urgent', 'Urgent'), ('high', 'High'), ('normal', 'Normal'), ('low', 'Low')])),
                ('status', models.CharField(max_length=15, default='queued', choices=[('queued', 'Queued'), ('assigned', 'Assigned'), ('in_review', 'In Review'), ('completed', 'Completed'), ('escalated', 'Escalated')])),
                ('blind_review_mode', models.BooleanField(default=False, help_text='When true, reviewer UI strips candidate PII (name, photo, gender, age indicators)')),
                ('due_by', models.DateTimeField(null=True, blank=True)),
                ('review_started_at', models.DateTimeField(null=True, blank=True)),
                ('review_completed_at', models.DateTimeField(null=True, blank=True)),
                ('queue_reason', models.CharField(blank=True, default='', max_length=255, help_text='Why this application is in the queue (auto-populated)')),
                ('notes', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='screen_review_queue', to='tenants.tenant')),
                ('application', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='screen_queue_entries', to='applications.application')),
                ('assigned_to', models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_screen_reviews', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'screen_review_queue',
                'ordering': ['priority', 'created_at'],
                'indexes': [
                    models.Index(fields=['tenant', 'status'], name='scr_queue_tenant_status_idx'),
                    models.Index(fields=['assigned_to', 'status'], name='scr_queue_assignee_idx'),
                ],
            },
        ),

        # ── NEW: ScreeningAuditEntry ──────────────────────────────────────────
        migrations.CreateModel(
            name='ScreeningAuditEntry',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('action', models.CharField(
                    max_length=50,
                    choices=[
                        ('questionnaire_submitted', 'Questionnaire Submitted'),
                        ('knockout_triggered', 'Knockout Triggered'),
                        ('rule_evaluation_run', 'Rule Evaluation Run'),
                        ('auto_decision_made', 'Auto Decision Made'),
                        ('human_decision_made', 'Human Decision Made'),
                        ('blind_review_toggled', 'Blind Review Toggled'),
                        ('queue_assigned', 'Review Queue Assigned'),
                        ('queue_escalated', 'Review Queue Escalated'),
                        ('assessment_ordered', 'Assessment Ordered'),
                        ('assessment_completed', 'Assessment Completed'),
                        ('result_normalized', 'Result Normalized'),
                        ('anti_cheat_flag_raised', 'Anti-Cheat Flag Raised'),
                        ('anti_cheat_cleared', 'Anti-Cheat Flag Cleared'),
                        ('credential_verified', 'Credential Verified'),
                        ('waiver_granted', 'Waiver Granted'),
                        ('alternate_path_assigned', 'Alternate Path Assigned'),
                        ('appeal_submitted', 'Appeal Submitted'),
                        ('appeal_reviewed', 'Appeal Reviewed'),
                        ('explanation_generated', 'Explanation Generated'),
                        ('decision_overridden', 'Decision Overridden'),
                    ]
                )),
                ('actor_label', models.CharField(blank=True, default='', max_length=255, help_text='Captured display name at time of action (survives user deletion)')),
                ('is_system_action', models.BooleanField(default=False)),
                ('payload', models.JSONField(blank=True, default=dict, help_text='Snapshot of relevant data at time of action')),
                ('ip_address', models.GenericIPAddressField(null=True, blank=True)),
                ('user_agent', models.CharField(blank=True, default='', max_length=500)),
                ('occurred_at', models.DateTimeField(auto_now_add=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='screening_audit_entries', to='tenants.tenant')),
                ('application', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='screening_audit_entries', to='applications.application')),
                ('actor', models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, related_name='screening_audit_actions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'screening_audit_entries',
                'ordering': ['-occurred_at'],
                'indexes': [
                    models.Index(fields=['application'], name='scr_audit_app_idx'),
                    models.Index(fields=['tenant', 'action'], name='scr_audit_tenant_action_idx'),
                ],
            },
        ),

        # ── NEW: ScreeningAppeal ──────────────────────────────────────────────
        migrations.CreateModel(
            name='ScreeningAppeal',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('candidate_statement', models.TextField(help_text="Candidate's explanation/grounds for appeal")),
                ('supporting_evidence_urls', models.JSONField(blank=True, default=list, help_text='URLs to uploaded supporting documents')),
                ('status', models.CharField(
                    max_length=20, default='submitted',
                    choices=[
                        ('submitted', 'Submitted'), ('under_review', 'Under Review'),
                        ('upheld', 'Upheld — Decision Unchanged'), ('overturned', 'Overturned — Decision Reversed'),
                        ('withdrawn', 'Withdrawn by Candidate'), ('closed', 'Closed'),
                    ]
                )),
                ('reviewer_notes', models.TextField(blank=True, default='')),
                ('outcome_explanation', models.TextField(blank=True, default='', help_text='Plain-language explanation of appeal outcome sent to candidate')),
                ('reviewed_at', models.DateTimeField(null=True, blank=True)),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='screening_appeals', to='tenants.tenant')),
                ('application', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='screening_appeals', to='applications.application')),
                ('original_decision', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='appeals', to='assessments.screeningdecision')),
                ('assigned_reviewer', models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_appeals', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'screening_appeals', 'ordering': ['-submitted_at']},
        ),

        # ── NEW: ExplainableMatchSnapshot ─────────────────────────────────────
        migrations.CreateModel(
            name='ExplainableMatchSnapshot',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('overall_match_score', models.FloatField(null=True, blank=True)),
                ('screening_score', models.FloatField(null=True, blank=True)),
                ('assessment_score', models.FloatField(null=True, blank=True)),
                ('questionnaire_score', models.FloatField(null=True, blank=True)),
                ('score_breakdown', models.JSONField(blank=True, default=dict, help_text='Component scores: skills, experience, education, location, etc.')),
                ('must_have_checks', models.JSONField(blank=True, default=list, help_text='[{"requirement": "5+ years Python", "met": true, "evidence": "..."}]')),
                ('disqualifiers_triggered', models.JSONField(blank=True, default=list)),
                ('plain_language_summary', models.TextField(blank=True, default='')),
                ('engine_version', models.CharField(blank=True, default='', max_length=50)),
                ('generated_at', models.DateTimeField(auto_now_add=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='match_snapshots', to='tenants.tenant')),
                ('application', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='match_snapshots', to='applications.application')),
            ],
            options={
                'db_table': 'explainable_match_snapshots',
                'ordering': ['-generated_at'],
                'indexes': [models.Index(fields=['application'], name='match_snap_app_idx')],
            },
        ),
    ]
