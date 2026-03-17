# Generated migration for Feature 5 — Candidate Experience Portal 2.0
# Adds 14 new models + extends existing models with new fields

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0001_initial'),
        ('applications', '0005_offer_esign_document_url_offer_esign_envelope_id_and_more'),
        ('candidates', '0008_candidatefollowuptask_candidateoutreachlog_and_more'),
        ('jobs', '0005_job_degree_optional_note_job_degree_required_and_more'),
        ('tenants', '0004_delete_subscription'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── Extend existing models ─────────────────────────────────────────

        # JobAlert: add employment_type, salary_min, frequency, unsubscribe_token
        migrations.AddField(
            model_name='jobalert',
            name='employment_type',
            field=models.CharField(blank=True, default='', max_length=30),
        ),
        migrations.AddField(
            model_name='jobalert',
            name='salary_min',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='jobalert',
            name='frequency',
            field=models.CharField(
                choices=[('instant', 'Instant'), ('daily', 'Daily'), ('weekly', 'Weekly')],
                default='weekly', max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='jobalert',
            name='unsubscribe_token',
            field=models.CharField(blank=True, db_index=True, default='', max_length=80),
        ),

        # SavedApplicationDraft: add autofill_source, completion_pct
        migrations.AddField(
            model_name='savedapplicationdraft',
            name='autofill_source',
            field=models.CharField(blank=True, default='', max_length=30),
        ),
        migrations.AddField(
            model_name='savedapplicationdraft',
            name='completion_pct',
            field=models.IntegerField(default=0),
        ),

        # PortalToken: extend purpose help_text (no DB change needed, but bump help_text)
        migrations.AlterField(
            model_name='portaltoken',
            name='purpose',
            field=models.CharField(
                help_text=(
                    'status_check, document_upload, self_schedule, offer_review, feedback, '
                    'profile_update, withdraw, nps_survey, reschedule, prep_packet'
                ),
                max_length=50,
            ),
        ),

        # AccessibilityPreference: add auth_alternative
        migrations.AddField(
            model_name='accessibilitypreference',
            name='auth_alternative',
            field=models.CharField(blank=True, default='', max_length=30,
                help_text='magic_link, sms_otp, email_otp'),
        ),

        # ── New models ─────────────────────────────────────────────────────

        migrations.CreateModel(
            name='RoleApplicationForm',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('department', models.CharField(blank=True, default='', max_length=150)),
                ('fields', models.JSONField(blank=True, default=list)),
                ('enable_autofill', models.BooleanField(default=True)),
                ('one_click_threshold', models.IntegerField(default=80)),
                ('supported_locales', models.JSONField(blank=True, default=list)),
                ('legal_notices', models.JSONField(blank=True, default=dict)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('job', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='application_form', to='jobs.job')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='application_forms', to='tenants.tenant')),
            ],
            options={'db_table': 'role_application_forms',
                     'indexes': [models.Index(fields=['tenant', 'is_active'],
                                              name='role_app_forms_tenant_active_idx')]},
        ),

        migrations.CreateModel(
            name='CandidateDashboardSession',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('session_token', models.CharField(db_index=True, max_length=128, unique=True)),
                ('login_method', models.CharField(default='magic_link', max_length=20)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.CharField(blank=True, default='', max_length=500)),
                ('expires_at', models.DateTimeField()),
                ('last_activity_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('candidate', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='dashboard_sessions', to='candidates.candidate')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='dashboard_sessions', to='tenants.tenant')),
            ],
            options={'db_table': 'candidate_dashboard_sessions',
                     'indexes': [models.Index(fields=['tenant', 'candidate'],
                                              name='cand_dash_sess_tenant_cand_idx')]},
        ),

        migrations.CreateModel(
            name='ApplicationStageConfig',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('candidate_label', models.CharField(blank=True, default='', max_length=100)),
                ('description', models.TextField(blank=True, default='')),
                ('expected_timeline_days', models.IntegerField(blank=True, null=True)),
                ('next_steps_message', models.TextField(blank=True, default='')),
                ('translations', models.JSONField(blank=True, default=dict)),
                ('show_interviewer_names', models.BooleanField(default=False)),
                ('show_timeline', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('stage', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,
                    related_name='candidate_config', to='jobs.pipelinestage')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='stage_configs', to='tenants.tenant')),
            ],
            options={'db_table': 'application_stage_configs'},
        ),

        migrations.CreateModel(
            name='InterviewPrepPacket',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(blank=True, default='', max_length=200)),
                ('sections', models.JSONField(blank=True, default=list)),
                ('logistics', models.JSONField(blank=True, default=dict)),
                ('accessibility_notes', models.TextField(blank=True, default='')),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('viewed_at', models.DateTimeField(blank=True, null=True)),
                ('help_contact_name', models.CharField(blank=True, default='', max_length=200)),
                ('help_contact_email', models.EmailField(blank=True, default='')),
                ('help_contact_phone', models.CharField(blank=True, default='', max_length=30)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('application', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='prep_packets', to='applications.application')),
                ('interview', models.ForeignKey(blank=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='prep_packets', to='applications.interview')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='prep_packets', to='tenants.tenant')),
            ],
            options={'db_table': 'interview_prep_packets',
                     'indexes': [models.Index(fields=['tenant', 'application'],
                                              name='prep_packet_tenant_app_idx')]},
        ),

        migrations.CreateModel(
            name='SelfRescheduleRule',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('max_reschedules', models.IntegerField(default=2)),
                ('min_hours_before', models.IntegerField(default=24)),
                ('allowed_interview_types', models.JSONField(blank=True, default=list)),
                ('require_reason', models.BooleanField(default=False)),
                ('notify_recruiter', models.BooleanField(default=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('job', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='reschedule_rules', to='jobs.job')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='reschedule_rules', to='tenants.tenant')),
            ],
            options={'db_table': 'self_reschedule_rules'},
        ),

        migrations.CreateModel(
            name='CandidateWithdrawal',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('reason', models.CharField(
                    blank=True, default='', max_length=50,
                    choices=[
                        ('accepted_other_offer', 'Accepted another offer'),
                        ('role_not_right', 'Role is not the right fit'),
                        ('location', 'Location / remote policy'),
                        ('compensation', 'Compensation'),
                        ('personal', 'Personal reasons'),
                        ('too_long', 'Process taking too long'),
                        ('no_response', 'No response from company'),
                        ('other', 'Other'),
                    ],
                )),
                ('reason_detail', models.TextField(blank=True, default='')),
                ('would_apply_future', models.BooleanField(blank=True, null=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('withdrawn_at', models.DateTimeField(auto_now_add=True)),
                ('application', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,
                    related_name='withdrawal', to='applications.application')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    to='tenants.tenant')),
            ],
            options={'db_table': 'candidate_withdrawals'},
        ),

        migrations.CreateModel(
            name='MissingDocumentRequest',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('document_type', models.CharField(max_length=100)),
                ('instructions', models.TextField(blank=True, default='')),
                ('upload_token', models.CharField(db_index=True, max_length=128, unique=True)),
                ('status', models.CharField(
                    choices=[('pending', 'Pending'), ('uploaded', 'Uploaded'), ('cancelled', 'Cancelled')],
                    default='pending', max_length=20,
                )),
                ('uploaded_file_url', models.CharField(blank=True, default='', max_length=500)),
                ('due_date', models.DateField(blank=True, null=True)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('uploaded_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('application', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='doc_requests', to='applications.application')),
                ('requested_by', models.ForeignKey(blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='sent_doc_requests', to=settings.AUTH_USER_MODEL)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='doc_requests', to='tenants.tenant')),
            ],
            options={'db_table': 'missing_document_requests',
                     'indexes': [models.Index(fields=['tenant', 'application'],
                                              name='missing_doc_req_tenant_app_idx')]},
        ),

        migrations.CreateModel(
            name='AccommodationRequest',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('accommodation_type', models.CharField(
                    choices=[
                        ('interview_accessibility', 'Interview Accessibility'),
                        ('assessment_accessibility', 'Assessment Accessibility'),
                        ('workplace_accommodation', 'Workplace Accommodation'),
                        ('communication_preference', 'Communication Preference'),
                        ('language_support', 'Language Support'),
                        ('other', 'Other'),
                    ],
                    max_length=40,
                )),
                ('description', models.TextField()),
                ('needs', models.JSONField(blank=True, default=list)),
                ('status', models.CharField(
                    choices=[
                        ('submitted', 'Submitted'),
                        ('under_review', 'Under Review'),
                        ('approved', 'Approved'),
                        ('partially_approved', 'Partially Approved'),
                        ('declined', 'Declined'),
                        ('needs_info', 'Needs More Information'),
                    ],
                    default='submitted', max_length=30,
                )),
                ('reviewer_notes', models.TextField(blank=True, default='')),
                ('approved_accommodations', models.JSONField(blank=True, default=list)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('application', models.ForeignKey(blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='accommodation_requests', to='applications.application')),
                ('candidate', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='accommodation_requests', to='candidates.candidate')),
                ('reviewer', models.ForeignKey(blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='reviewed_accommodations', to=settings.AUTH_USER_MODEL)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='accommodation_requests', to='tenants.tenant')),
            ],
            options={'db_table': 'accommodation_requests',
                     'indexes': [models.Index(fields=['tenant', 'status'],
                                              name='accommodation_req_tenant_status_idx')]},
        ),

        migrations.CreateModel(
            name='TalentCommunityMember',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('email', models.EmailField()),
                ('name', models.CharField(blank=True, default='', max_length=200)),
                ('interests', models.JSONField(blank=True, default=list)),
                ('preferred_roles', models.JSONField(blank=True, default=list)),
                ('preferred_locations', models.JSONField(blank=True, default=list)),
                ('open_to_relocation', models.BooleanField(default=False)),
                ('linkedin_url', models.CharField(blank=True, default='', max_length=300)),
                ('status', models.CharField(
                    choices=[('active', 'Active'), ('unsubscribed', 'Unsubscribed'), ('converted', 'Converted')],
                    default='active', max_length=20,
                )),
                ('consent_marketing', models.BooleanField(default=False)),
                ('consent_given_at', models.DateTimeField(blank=True, null=True)),
                ('unsubscribe_token', models.CharField(blank=True, db_index=True, default='', max_length=80)),
                ('joined_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('assigned_recruiter', models.ForeignKey(blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='community_members', to=settings.AUTH_USER_MODEL)),
                ('candidate', models.ForeignKey(blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='community_memberships', to='candidates.candidate')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='talent_community', to='tenants.tenant')),
            ],
            options={'db_table': 'talent_community_members',
                     'indexes': [
                         models.Index(fields=['tenant', 'status'], name='talent_comm_tenant_status_idx'),
                         models.Index(fields=['email'], name='talent_comm_email_idx'),
                     ]},
        ),

        migrations.CreateModel(
            name='CandidateEvent',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=200)),
                ('event_type', models.CharField(
                    choices=[
                        ('info_session', 'Info Session'), ('open_day', 'Open Day'),
                        ('hackathon', 'Hackathon'), ('career_fair', 'Career Fair'),
                        ('webinar', 'Webinar'), ('networking', 'Networking'), ('other', 'Other'),
                    ],
                    default='info_session', max_length=30,
                )),
                ('description', models.TextField(blank=True, default='')),
                ('starts_at', models.DateTimeField()),
                ('ends_at', models.DateTimeField()),
                ('location', models.CharField(blank=True, default='', max_length=300)),
                ('is_virtual', models.BooleanField(default=True)),
                ('virtual_link', models.CharField(blank=True, default='', max_length=500)),
                ('max_registrants', models.IntegerField(blank=True, null=True)),
                ('is_public', models.BooleanField(default=True)),
                ('accessibility_info', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='candidate_events', to='tenants.tenant')),
            ],
            options={'db_table': 'candidate_events',
                     'indexes': [models.Index(fields=['tenant', 'starts_at'],
                                              name='cand_events_tenant_starts_idx')]},
        ),

        migrations.CreateModel(
            name='EventRegistration',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('email', models.EmailField()),
                ('name', models.CharField(blank=True, default='', max_length=200)),
                ('accessibility_needs', models.JSONField(blank=True, default=list)),
                ('attended', models.BooleanField(blank=True, null=True)),
                ('registered_at', models.DateTimeField(auto_now_add=True)),
                ('candidate', models.ForeignKey(blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='event_registrations', to='candidates.candidate')),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='registrations', to='portal.candidateevent')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    to='tenants.tenant')),
            ],
            options={'db_table': 'event_registrations',
                     'unique_together': {('event', 'email')}},
        ),

        migrations.CreateModel(
            name='HelpArticle',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('category', models.CharField(
                    choices=[
                        ('application', 'Application Process'), ('interview', 'Interview Prep'),
                        ('offer', 'Offers & Contracts'), ('profile', 'Your Profile'),
                        ('privacy', 'Privacy & Data'), ('accessibility', 'Accessibility'),
                        ('technical', 'Technical Issues'), ('general', 'General'),
                    ],
                    default='general', max_length=30,
                )),
                ('title', models.CharField(max_length=200)),
                ('slug', models.SlugField(max_length=200)),
                ('content', models.TextField()),
                ('translations', models.JSONField(blank=True, default=dict)),
                ('is_published', models.BooleanField(default=True)),
                ('is_pinned', models.BooleanField(default=False)),
                ('view_count', models.IntegerField(default=0)),
                ('helpful_votes', models.IntegerField(default=0)),
                ('unhelpful_votes', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.ForeignKey(blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='help_articles', to='tenants.tenant')),
            ],
            options={'db_table': 'help_articles',
                     'indexes': [models.Index(fields=['category', 'is_published'],
                                              name='help_article_cat_pub_idx')]},
        ),

        migrations.CreateModel(
            name='ConsentRecord',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('purpose', models.CharField(
                    choices=[
                        ('data_processing', 'Processing application data'),
                        ('marketing', 'Marketing communications'),
                        ('talent_pool', 'Talent pool / future roles'),
                        ('third_party_sharing', 'Sharing with third parties'),
                        ('profiling', 'Automated profiling / AI scoring'),
                        ('analytics', 'Anonymous analytics'),
                        ('cross_border_transfer', 'Cross-border data transfer'),
                    ],
                    max_length=30,
                )),
                ('granted', models.BooleanField()),
                ('granted_at', models.DateTimeField(blank=True, null=True)),
                ('withdrawn_at', models.DateTimeField(blank=True, null=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('locale', models.CharField(blank=True, default='en', max_length=10)),
                ('notice_text', models.TextField(blank=True, default='')),
                ('notice_version', models.CharField(blank=True, default='', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('candidate', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='portal_consents', to='candidates.candidate')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='portal_consents', to='tenants.tenant')),
            ],
            options={'db_table': 'portal_consent_records',
                     'indexes': [models.Index(fields=['tenant', 'candidate', 'purpose'],
                                              name='portal_consent_tenant_cand_purpose_idx')]},
        ),

        migrations.CreateModel(
            name='DataSubjectRequest',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('email', models.EmailField()),
                ('request_type', models.CharField(
                    choices=[
                        ('access', 'Right of Access'), ('erasure', 'Right to Erasure'),
                        ('portability', 'Data Portability'), ('rectification', 'Rectification'),
                        ('restriction', 'Restriction of Processing'),
                        ('objection', 'Objection to Processing'),
                    ],
                    max_length=20,
                )),
                ('description', models.TextField(blank=True, default='')),
                ('status', models.CharField(
                    choices=[
                        ('submitted', 'Submitted'), ('in_progress', 'In Progress'),
                        ('completed', 'Completed'), ('rejected', 'Rejected'),
                        ('extended', 'Extended (30+30 days)'),
                    ],
                    default='submitted', max_length=20,
                )),
                ('response_notes', models.TextField(blank=True, default='')),
                ('due_date', models.DateField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('candidate', models.ForeignKey(blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='portal_dsr', to='candidates.candidate')),
                ('handler', models.ForeignKey(blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='handled_dsr', to=settings.AUTH_USER_MODEL)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='portal_dsr', to='tenants.tenant')),
            ],
            options={'db_table': 'portal_data_subject_requests',
                     'indexes': [
                         models.Index(fields=['tenant', 'status'], name='portal_dsr_tenant_status_idx'),
                         models.Index(fields=['email'], name='portal_dsr_email_idx'),
                     ]},
        ),

        migrations.CreateModel(
            name='RecruiterSafeRoute',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('department', models.CharField(blank=True, default='', max_length=150)),
                ('location', models.CharField(blank=True, default='', max_length=255)),
                ('recruiter_display_name', models.CharField(blank=True, default='', max_length=200)),
                ('recruiter_display_email', models.EmailField(blank=True, default='')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('recruiter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='safe_routes', to=settings.AUTH_USER_MODEL)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='safe_routes', to='tenants.tenant')),
            ],
            options={'db_table': 'recruiter_safe_routes',
                     'indexes': [models.Index(fields=['tenant', 'is_active'],
                                              name='recruiter_safe_route_tenant_active_idx')]},
        ),
    ]
