"""
Extend referrals app:
  - Add new columns to ReferralProgram, ReferralCampaign, Referral, ReferralLink, BonusRule, BonusPayout
  - Add 5 new models: ReferralRequest, AmbassadorProfile, HMReferralPrompt,
    ReferralQualityScore, ReferralAnalyticsSnapshot
"""

import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("referrals", "0001_initial"),
        ("jobs", "0005_job_degree_optional_note_job_degree_required_and_more"),
        ("tenants", "0004_delete_subscription"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── Extend ReferralProgram ────────────────────────────────────────────
        migrations.AddField(
            model_name="referralprogram",
            name="portal_headline",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="referralprogram",
            name="portal_description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="referralprogram",
            name="portal_banner_url",
            field=models.URLField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="referralprogram",
            name="enable_hm_prompts",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="referralprogram",
            name="hm_prompt_days_after_open",
            field=models.PositiveSmallIntegerField(default=7),
        ),

        # ── Extend ReferralCampaign ───────────────────────────────────────────
        migrations.AddField(
            model_name="referralcampaign",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="referralcampaign",
            name="page_headline",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="referralcampaign",
            name="page_body",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="referralcampaign",
            name="page_image_url",
            field=models.URLField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="referralcampaign",
            name="share_message_template",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="referralcampaign",
            name="target_audience",
            field=models.CharField(
                choices=[
                    ("all", "All Employees"),
                    ("alumni", "Alumni"),
                    ("ambassadors", "External Ambassadors"),
                    ("custom", "Custom"),
                ],
                default="all",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="referralcampaign",
            name="custom_audience_ids",
            field=models.JSONField(blank=True, default=list),
        ),

        # ── Extend Referral ───────────────────────────────────────────────────
        migrations.AddField(
            model_name="referral",
            name="referrer_type",
            field=models.CharField(
                choices=[
                    ("employee", "Current Employee"),
                    ("alumni", "Alumni"),
                    ("ambassador", "External Ambassador"),
                    ("hiring_manager", "Hiring Manager"),
                ],
                default="employee",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="referral",
            name="candidate_phone",
            field=models.CharField(blank=True, default="", max_length=30),
        ),
        migrations.AddField(
            model_name="referral",
            name="candidate_linkedin",
            field=models.URLField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="referral",
            name="referral_link",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="referrals",
                to="referrals.referrallink",
            ),
        ),
        migrations.AddField(
            model_name="referral",
            name="relationship",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="referral",
            name="quality_score",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="referral",
            name="is_duplicate",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="referral",
            name="duplicate_of",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="duplicate_referrals",
                to="referrals.referral",
            ),
        ),
        migrations.AddField(
            model_name="referral",
            name="duplicate_resolved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="referral",
            name="duplicate_resolution_notes",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="referral",
            name="status",
            field=models.CharField(
                choices=[
                    ("submitted", "Submitted"),
                    ("under_review", "Under Review"),
                    ("screening", "In Screening"),
                    ("interviewing", "Interviewing"),
                    ("offer_extended", "Offer Extended"),
                    ("hired", "Hired"),
                    ("not_hired", "Not Hired / Declined"),
                    ("pending_payout", "Pending Payout"),
                    ("paid", "Paid"),
                    ("duplicate", "Duplicate — Conflict"),
                    ("withdrawn", "Withdrawn"),
                ],
                default="submitted",
                max_length=20,
            ),
        ),

        # ── Extend ReferralLink ───────────────────────────────────────────────
        migrations.AddField(
            model_name="referrallink",
            name="campaign",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="links",
                to="referrals.referralcampaign",
            ),
        ),
        migrations.AddField(
            model_name="referrallink",
            name="utm_source",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="referrallink",
            name="utm_medium",
            field=models.CharField(blank=True, default="", max_length=100),
        ),

        # ── Extend BonusRule ──────────────────────────────────────────────────
        migrations.AddField(
            model_name="bonusrule",
            name="job_level_filter",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="bonusrule",
            name="referrer_type_filter",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="bonusrule",
            name="requires_approval",
            field=models.BooleanField(default=True),
        ),

        # ── Extend BonusPayout ────────────────────────────────────────────────
        migrations.AddField(
            model_name="bonuspayout",
            name="approved_by",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="approved_payouts",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="bonuspayout",
            name="approved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="bonuspayout",
            name="payment_reference",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AlterField(
            model_name="bonuspayout",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("approved", "Approved"),
                    ("processing", "Processing"),
                    ("paid", "Paid"),
                    ("cancelled", "Cancelled"),
                    ("on_hold", "On Hold"),
                ],
                default="pending",
                max_length=20,
            ),
        ),

        # ── New model: ReferralRequest ────────────────────────────────────────
        migrations.CreateModel(
            name="ReferralRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("message", models.TextField(blank=True, default="")),
                ("status", models.CharField(
                    choices=[
                        ("sent", "Sent"),
                        ("viewed", "Viewed"),
                        ("acted", "Acted — Referral Submitted"),
                        ("declined", "Declined"),
                        ("expired", "Expired"),
                    ],
                    default="sent",
                    max_length=20,
                )),
                ("is_hm_prompt", models.BooleanField(default=False)),
                ("sent_at", models.DateTimeField(auto_now_add=True)),
                ("viewed_at", models.DateTimeField(blank=True, null=True)),
                ("acted_at", models.DateTimeField(blank=True, null=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("campaign", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="requests",
                    to="referrals.referralcampaign",
                )),
                ("job", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="referral_requests",
                    to="jobs.job",
                )),
                ("program", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="requests",
                    to="referrals.referralprogram",
                )),
                ("requested_by", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="referral_requests_sent",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("requested_from", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="referral_requests_received",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("tenant", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="referral_requests",
                    to="tenants.tenant",
                )),
            ],
            options={"db_table": "referral_requests", "ordering": ["-sent_at"]},
        ),

        # ── New model: AmbassadorProfile ──────────────────────────────────────
        migrations.CreateModel(
            name="AmbassadorProfile",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(blank=True, default="", max_length=255)),
                ("email", models.EmailField(blank=True, default="")),
                ("phone", models.CharField(blank=True, default="", max_length=30)),
                ("company", models.CharField(blank=True, default="", max_length=255)),
                ("ambassador_type", models.CharField(
                    choices=[
                        ("alumni", "Alumni"),
                        ("external_ambassador", "External Ambassador"),
                        ("contractor", "Contractor"),
                        ("partner", "Partner / Vendor"),
                    ],
                    default="external_ambassador",
                    max_length=30,
                )),
                ("status", models.CharField(
                    choices=[
                        ("invited", "Invited"),
                        ("active", "Active"),
                        ("inactive", "Inactive"),
                        ("revoked", "Revoked"),
                    ],
                    default="invited",
                    max_length=20,
                )),
                ("invite_token", models.CharField(blank=True, default="", max_length=64, unique=True)),
                ("bio", models.TextField(blank=True, default="")),
                ("linkedin_url", models.URLField(blank=True, default="")),
                ("total_referrals", models.PositiveIntegerField(default=0)),
                ("total_hires", models.PositiveIntegerField(default=0)),
                ("total_earnings", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("invited_by", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="invited_ambassadors",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("program", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="ambassadors",
                    to="referrals.referralprogram",
                )),
                ("tenant", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="ambassador_profiles",
                    to="tenants.tenant",
                )),
                ("user", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="ambassador_profiles",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "db_table": "referral_ambassador_profiles",
                "ordering": ["-total_hires", "-total_referrals"],
            },
        ),

        # ── New model: HMReferralPrompt ────────────────────────────────────────
        migrations.CreateModel(
            name="HMReferralPrompt",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(
                    choices=[
                        ("pending", "Pending Send"),
                        ("sent", "Sent"),
                        ("viewed", "Viewed"),
                        ("referrals_submitted", "Referrals Submitted"),
                        ("no_action", "No Action Taken"),
                    ],
                    default="pending",
                    max_length=30,
                )),
                ("referrals_submitted_count", models.PositiveSmallIntegerField(default=0)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("viewed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("hiring_manager", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="hm_referral_prompts",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("job", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="hm_prompts",
                    to="jobs.job",
                )),
                ("program", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="hm_prompts",
                    to="referrals.referralprogram",
                )),
                ("tenant", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="hm_prompts",
                    to="tenants.tenant",
                )),
            ],
            options={"db_table": "referral_hm_prompts", "ordering": ["-created_at"]},
        ),

        # ── New model: ReferralQualityScore ───────────────────────────────────
        migrations.CreateModel(
            name="ReferralQualityScore",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("profile_completeness", models.FloatField(default=0.0)),
                ("skills_match", models.FloatField(default=0.0)),
                ("relationship_strength", models.FloatField(default=0.0)),
                ("interview_pass_rate", models.FloatField(default=0.0)),
                ("time_to_hire", models.FloatField(default=0.0)),
                ("overall_score", models.FloatField(default=0.0)),
                ("scored_at", models.DateTimeField(auto_now=True)),
                ("notes", models.TextField(blank=True, default="")),
                ("referral", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="quality_detail",
                    to="referrals.referral",
                )),
            ],
            options={"db_table": "referral_quality_scores"},
        ),

        # ── New model: ReferralAnalyticsSnapshot ──────────────────────────────
        migrations.CreateModel(
            name="ReferralAnalyticsSnapshot",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("snapshot_date", models.DateField()),
                ("period", models.CharField(
                    choices=[("day", "Daily"), ("week", "Weekly"), ("month", "Monthly")],
                    default="day",
                    max_length=10,
                )),
                ("total_referrals", models.PositiveIntegerField(default=0)),
                ("under_review", models.PositiveIntegerField(default=0)),
                ("screening", models.PositiveIntegerField(default=0)),
                ("interviewing", models.PositiveIntegerField(default=0)),
                ("offers", models.PositiveIntegerField(default=0)),
                ("hired", models.PositiveIntegerField(default=0)),
                ("not_hired", models.PositiveIntegerField(default=0)),
                ("duplicates", models.PositiveIntegerField(default=0)),
                ("avg_quality_score", models.FloatField(default=0.0)),
                ("avg_time_to_hire_days", models.FloatField(blank=True, null=True)),
                ("total_bonus_paid", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("total_bonus_pending", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("cost_per_hire", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("employee_referrals", models.PositiveIntegerField(default=0)),
                ("alumni_referrals", models.PositiveIntegerField(default=0)),
                ("ambassador_referrals", models.PositiveIntegerField(default=0)),
                ("program", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="analytics_snapshots",
                    to="referrals.referralprogram",
                )),
                ("tenant", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="referral_snapshots",
                    to="tenants.tenant",
                )),
            ],
            options={
                "db_table": "referral_analytics_snapshots",
                "ordering": ["-snapshot_date"],
                "unique_together": {("tenant", "program", "snapshot_date", "period")},
            },
        ),
    ]
