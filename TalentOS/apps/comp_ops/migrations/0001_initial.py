# Generated migration for apps.comp_ops

import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("tenants", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [

        # 1. OfferApprovalMatrix
        migrations.CreateModel(
            name="OfferApprovalMatrix",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, default="")),
                ("rules", models.JSONField(default=list)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="offer_approval_matrices", to="tenants.tenant")),
            ],
            options={"db_table": "comp_offer_approval_matrices", "ordering": ["name"]},
        ),

        # 2. CompensationBandGuardrail
        migrations.CreateModel(
            name="CompensationBandGuardrail",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("job_family", models.CharField(blank=True, default="", max_length=150)),
                ("job_level", models.CharField(blank=True, default="", max_length=30)),
                ("location", models.CharField(blank=True, default="", max_length=150)),
                ("currency", models.CharField(default="USD", max_length=10)),
                ("band_min", models.DecimalField(decimal_places=2, max_digits=12)),
                ("band_mid", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("band_max", models.DecimalField(decimal_places=2, max_digits=12)),
                ("hard_cap", models.BooleanField(default=False)),
                ("warn_above_mid", models.BooleanField(default=True)),
                ("effective_date", models.DateField(blank=True, null=True)),
                ("expires_date", models.DateField(blank=True, null=True)),
                ("source", models.CharField(blank=True, default="", max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="comp_band_guardrails", to="tenants.tenant")),
            ],
            options={"db_table": "comp_band_guardrails", "ordering": ["job_family", "job_level", "location"]},
        ),

        # 3. LocationPayRule
        migrations.CreateModel(
            name="LocationPayRule",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("location_name", models.CharField(max_length=150)),
                ("country", models.CharField(blank=True, default="", max_length=100)),
                ("state_province", models.CharField(blank=True, default="", max_length=100)),
                ("cost_of_living_index", models.DecimalField(decimal_places=3, default=1.0, max_digits=6)),
                ("pay_multiplier", models.DecimalField(decimal_places=4, default=1.0, max_digits=6)),
                ("currency", models.CharField(default="USD", max_length=10)),
                ("notes", models.TextField(blank=True, default="")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="location_pay_rules", to="tenants.tenant")),
            ],
            options={"db_table": "comp_location_pay_rules", "ordering": ["country", "state_province", "location_name"]},
        ),

        # 4. SignOnBonusRule
        migrations.CreateModel(
            name="SignOnBonusRule",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("job_level", models.CharField(blank=True, default="", max_length=30)),
                ("min_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("max_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("clawback_months", models.IntegerField(default=12)),
                ("clawback_percentage", models.DecimalField(decimal_places=2, default=100, max_digits=5)),
                ("requires_approval_above", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("conditions", models.TextField(blank=True, default="")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sign_on_bonus_rules", to="tenants.tenant")),
            ],
            options={"db_table": "comp_sign_on_bonus_rules", "ordering": ["name"]},
        ),

        # 5. RecurringBonusRule
        migrations.CreateModel(
            name="RecurringBonusRule",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("bonus_type", models.CharField(default="performance", max_length=50)),
                ("frequency", models.CharField(choices=[("monthly","Monthly"),("quarterly","Quarterly"),("semi_annual","Semi-Annual"),("annual","Annual")], default="annual", max_length=20)),
                ("target_pct_of_salary", models.DecimalField(decimal_places=2, default=10, max_digits=5)),
                ("min_pct", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("max_pct", models.DecimalField(decimal_places=2, default=30, max_digits=5)),
                ("eligibility_months", models.IntegerField(default=6)),
                ("notes", models.TextField(blank=True, default="")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="recurring_bonus_rules", to="tenants.tenant")),
            ],
            options={"db_table": "comp_recurring_bonus_rules", "ordering": ["name"]},
        ),

        # 6. EquityGrant
        migrations.CreateModel(
            name="EquityGrant",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("offer_version_id", models.UUIDField(blank=True, null=True)),
                ("candidate_name", models.CharField(blank=True, default="", max_length=255)),
                ("grant_type", models.CharField(choices=[("rsu","RSU"),("iso","ISO Options"),("nso","NSO Options"),("esop","ESOP"),("phantom","Phantom Equity"),("sar","Stock Appreciation Rights")], default="rsu", max_length=20)),
                ("units", models.IntegerField(default=0)),
                ("strike_price", models.DecimalField(blank=True, decimal_places=4, max_digits=10, null=True)),
                ("current_fmv", models.DecimalField(blank=True, decimal_places=4, max_digits=10, null=True)),
                ("vesting_schedule", models.CharField(default="4yr_1yr_cliff", max_length=50)),
                ("cliff_months", models.IntegerField(default=12)),
                ("total_vest_months", models.IntegerField(default=48)),
                ("grant_value_usd", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="equity_grants", to="tenants.tenant")),
            ],
            options={"db_table": "comp_equity_grants", "ordering": ["-created_at"]},
        ),

        # 7. RelocationPackage
        migrations.CreateModel(
            name="RelocationPackage",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("tier", models.CharField(default="standard", max_length=20)),
                ("lump_sum_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("includes_moving_service", models.BooleanField(default=False)),
                ("includes_temp_housing", models.BooleanField(default=False)),
                ("temp_housing_days", models.IntegerField(default=30)),
                ("includes_travel_allowance", models.BooleanField(default=False)),
                ("includes_spouse_support", models.BooleanField(default=False)),
                ("repayment_months", models.IntegerField(default=12)),
                ("notes", models.TextField(blank=True, default="")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="relocation_packages", to="tenants.tenant")),
            ],
            options={"db_table": "comp_relocation_packages", "ordering": ["tier", "name"]},
        ),

        # 8. VisaSponsorshipCost
        migrations.CreateModel(
            name="VisaSponsorshipCost",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("visa_type", models.CharField(max_length=50)),
                ("country", models.CharField(blank=True, default="", max_length=100)),
                ("estimated_cost_usd", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("attorney_fee", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("government_fee", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("processing_weeks", models.IntegerField(default=12)),
                ("premium_processing_available", models.BooleanField(default=False)),
                ("premium_processing_fee", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="visa_sponsorship_costs", to="tenants.tenant")),
            ],
            options={"db_table": "comp_visa_sponsorship_costs", "ordering": ["visa_type"]},
        ),

        # 9. InternalEquityCheck
        migrations.CreateModel(
            name="InternalEquityCheck",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("offer_version_id", models.UUIDField(blank=True, null=True)),
                ("candidate_name", models.CharField(blank=True, default="", max_length=255)),
                ("proposed_salary", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("comparable_employees", models.JSONField(default=list)),
                ("avg_peer_salary", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("equity_gap", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("equity_gap_pct", models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ("flag_raised", models.BooleanField(default=False)),
                ("flag_reason", models.TextField(blank=True, default="")),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="internal_equity_checks", to="tenants.tenant")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_equity_checks", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "comp_internal_equity_checks", "ordering": ["-created_at"]},
        ),

        # 10. PayCompetitivenessWarning
        migrations.CreateModel(
            name="PayCompetitivenessWarning",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("offer_version_id", models.UUIDField(blank=True, null=True)),
                ("candidate_name", models.CharField(blank=True, default="", max_length=255)),
                ("proposed_salary", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("market_p25", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("market_p50", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("market_p75", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("market_source", models.CharField(blank=True, default="", max_length=100)),
                ("compa_ratio", models.DecimalField(blank=True, decimal_places=3, max_digits=6, null=True)),
                ("warning_level", models.CharField(default="none", max_length=20)),
                ("warning_message", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pay_competitiveness_warnings", to="tenants.tenant")),
            ],
            options={"db_table": "comp_pay_competitiveness_warnings", "ordering": ["-created_at"]},
        ),

        # 11. OfferVersion
        migrations.CreateModel(
            name="OfferVersion",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("offer_id", models.UUIDField()),
                ("version_number", models.IntegerField(default=1)),
                ("candidate_name", models.CharField(blank=True, default="", max_length=255)),
                ("job_title", models.CharField(blank=True, default="", max_length=255)),
                ("base_salary", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("sign_on_bonus", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("target_bonus_pct", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("equity_units", models.IntegerField(default=0)),
                ("total_comp_estimate", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("details", models.JSONField(default=dict)),
                ("change_summary", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="offer_versions", to="tenants.tenant")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_offer_versions", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "comp_offer_versions", "ordering": ["-created_at"]},
        ),
        migrations.AlterUniqueTogether(
            name="offerversion",
            unique_together={("offer_id", "version_number")},
        ),

        # 12. CounterOfferPlan
        migrations.CreateModel(
            name="CounterOfferPlan",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("offer_version_id", models.UUIDField(blank=True, null=True)),
                ("candidate_name", models.CharField(blank=True, default="", max_length=255)),
                ("candidate_counter_salary", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("candidate_counter_notes", models.TextField(blank=True, default="")),
                ("our_revised_salary", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("our_revised_bonus", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("our_revised_equity", models.IntegerField(default=0)),
                ("walk_away_salary", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("close_strategy", models.TextField(blank=True, default="")),
                ("outcome", models.CharField(blank=True, default="", max_length=30)),
                ("outcome_notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="counteroffer_plans", to="tenants.tenant")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="counteroffer_plans", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "comp_counteroffer_plans", "ordering": ["-created_at"]},
        ),

        # 13. OfferApprovalAudit
        migrations.CreateModel(
            name="OfferApprovalAudit",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("offer_version_id", models.UUIDField(blank=True, null=True)),
                ("approval_step", models.IntegerField(default=1)),
                ("action", models.CharField(choices=[("pending","Pending"),("approved","Approved"),("rejected","Rejected"),("needs_revision","Needs Revision"),("escalated","Escalated")], default="pending", max_length=20)),
                ("note", models.TextField(blank=True, default="")),
                ("actioned_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="offer_approval_audits", to="tenants.tenant")),
                ("approver", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="offer_approval_audits", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "comp_offer_approval_audits", "ordering": ["-created_at"]},
        ),

        # 14. OfferCloseRisk
        migrations.CreateModel(
            name="OfferCloseRisk",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("offer_version_id", models.UUIDField(blank=True, null=True)),
                ("candidate_name", models.CharField(blank=True, default="", max_length=255)),
                ("risk_score", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("risk_level", models.CharField(default="low", max_length=10)),
                ("risk_factors", models.JSONField(default=list)),
                ("recommended_close_actions", models.JSONField(default=list)),
                ("computed_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="offer_close_risks", to="tenants.tenant")),
            ],
            options={"db_table": "comp_offer_close_risks", "ordering": ["-computed_at"]},
        ),

        # 15. CandidateDecisionDeadline
        migrations.CreateModel(
            name="CandidateDecisionDeadline",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("offer_version_id", models.UUIDField(blank=True, null=True)),
                ("candidate_name", models.CharField(blank=True, default="", max_length=255)),
                ("deadline", models.DateTimeField()),
                ("reminder_sent_at", models.DateTimeField(blank=True, null=True)),
                ("final_reminder_sent_at", models.DateTimeField(blank=True, null=True)),
                ("extended", models.BooleanField(default=False)),
                ("extended_deadline", models.DateTimeField(blank=True, null=True)),
                ("extension_reason", models.TextField(blank=True, default="")),
                ("decision", models.CharField(blank=True, default="", max_length=20)),
                ("decided_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="candidate_decision_deadlines", to="tenants.tenant")),
            ],
            options={"db_table": "comp_candidate_decision_deadlines", "ordering": ["-created_at"]},
        ),

        # 16. DeclineReasonTaxonomy
        migrations.CreateModel(
            name="DeclineReasonTaxonomy",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("category", models.CharField(max_length=100)),
                ("reason", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, default="")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="decline_reason_taxonomies", to="tenants.tenant")),
            ],
            options={"db_table": "comp_decline_reason_taxonomy", "ordering": ["category", "reason"]},
        ),

        # 17. StructuredClosePlan
        migrations.CreateModel(
            name="StructuredClosePlan",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("offer_version_id", models.UUIDField(blank=True, null=True)),
                ("candidate_name", models.CharField(blank=True, default="", max_length=255)),
                ("steps", models.JSONField(default=list)),
                ("candidate_motivators", models.TextField(blank=True, default="")),
                ("candidate_concerns", models.TextField(blank=True, default="")),
                ("competing_offers", models.TextField(blank=True, default="")),
                ("status", models.CharField(default="in_progress", max_length=20)),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
                ("outcome", models.CharField(blank=True, default="", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="structured_close_plans", to="tenants.tenant")),
                ("close_owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="close_plans", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "comp_structured_close_plans", "ordering": ["-created_at"]},
        ),

        # 18. OfferDocumentBundle
        migrations.CreateModel(
            name="OfferDocumentBundle",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("offer_version_id", models.UUIDField(blank=True, null=True)),
                ("candidate_name", models.CharField(blank=True, default="", max_length=255)),
                ("documents", models.JSONField(default=list)),
                ("generated_at", models.DateTimeField(blank=True, null=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("signed_at", models.DateTimeField(blank=True, null=True)),
                ("status", models.CharField(default="draft", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="offer_document_bundles", to="tenants.tenant")),
            ],
            options={"db_table": "comp_offer_document_bundles", "ordering": ["-created_at"]},
        ),

        # 19. CompBenchmarkIntegration
        migrations.CreateModel(
            name="CompBenchmarkIntegration",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("provider", models.CharField(max_length=100)),
                ("api_endpoint", models.URLField(blank=True, default="")),
                ("api_key_hint", models.CharField(blank=True, default="", max_length=20)),
                ("is_active", models.BooleanField(default=True)),
                ("last_synced_at", models.DateTimeField(blank=True, null=True)),
                ("sync_frequency_hours", models.IntegerField(default=24)),
                ("data_snapshot", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="comp_benchmark_integrations", to="tenants.tenant")),
            ],
            options={"db_table": "comp_benchmark_integrations", "ordering": ["provider"]},
        ),

        # 20. PreboardingChecklist
        migrations.CreateModel(
            name="PreboardingChecklist",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("offer_version_id", models.UUIDField(blank=True, null=True)),
                ("candidate_name", models.CharField(blank=True, default="", max_length=255)),
                ("offer_type", models.CharField(blank=True, default="", max_length=50)),
                ("items", models.JSONField(default=list)),
                ("kickoff_triggered_at", models.DateTimeField(blank=True, null=True)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("completion_pct", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="preboarding_checklists", to="tenants.tenant")),
                ("assigned_to", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="preboarding_checklists", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "comp_preboarding_checklists", "ordering": ["-created_at"]},
        ),
    ]
