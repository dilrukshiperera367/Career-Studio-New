"""Marketplace Billing — serializers."""
from rest_framework import serializers
from .models import BillingPlan, EmployerSubscription, Invoice, AdBudget, AdBudgetTransaction, CouponCode


class BillingPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingPlan
        fields = ["id", "tier", "name", "price_monthly_lkr", "price_annual_lkr",
                  "job_posting_limit", "featured_job_slots", "resume_database_access",
                  "analytics_level", "max_team_members", "priority_support",
                  "custom_branding", "api_access", "features_json", "sort_order"]


class EmployerSubscriptionSerializer(serializers.ModelSerializer):
    plan = BillingPlanSerializer(read_only=True)
    plan_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = EmployerSubscription
        fields = ["id", "plan", "plan_id", "status", "billing_cycle",
                  "started_at", "expires_at", "auto_renew", "created_at"]


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ["id", "invoice_number", "amount_lkr", "tax_amount_lkr", "total_lkr",
                  "status", "description", "paid_at", "due_date", "created_at"]
        read_only_fields = ["invoice_number"]


class AdBudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdBudget
        fields = ["balance_lkr", "total_deposited_lkr", "total_spent_lkr",
                  "auto_topup_enabled", "auto_topup_threshold_lkr", "auto_topup_amount_lkr"]


class AdBudgetTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdBudgetTransaction
        fields = ["id", "tx_type", "amount_lkr", "balance_after_lkr", "description", "created_at"]
