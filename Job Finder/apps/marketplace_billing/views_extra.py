"""
Feature 9 — Employer Self-Serve Growth & Monetization
Extra views: employer onboarding wizard, company claim flow, plan management,
coupon validation, wallet top-up, job quality score, job ad preview/validation,
fraud risk check, campaign performance dashboard, role-based seats, multi-brand support.
"""
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BillingPlan, EmployerSubscription, Invoice, AdBudget, AdBudgetTransaction, CouponCode


def _get_employer(request):
    from apps.employers.models import EmployerAccount
    return EmployerAccount.objects.filter(team_members__user=request.user).first()


# ── Plan Catalogue ────────────────────────────────────────────────────────────

class BillingPlanCatalogueView(APIView):
    """GET /marketplace-billing/plans/ — full plan catalogue with feature comparison."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        plans = BillingPlan.objects.filter(is_active=True).order_by("sort_order")
        return Response([{
            "id": str(p.id),
            "tier": p.tier,
            "name": p.name,
            "price_monthly_lkr": float(p.price_monthly_lkr),
            "price_annual_lkr": float(p.price_annual_lkr),
            "annual_savings_pct": round((1 - float(p.price_annual_lkr) / (float(p.price_monthly_lkr) * 12)) * 100, 0) if p.price_monthly_lkr > 0 else 0,
            "job_posting_limit": p.job_posting_limit,
            "featured_job_slots": p.featured_job_slots,
            "resume_database_access": p.resume_database_access,
            "analytics_level": p.analytics_level,
            "max_team_members": p.max_team_members,
            "priority_support": p.priority_support,
            "custom_branding": p.custom_branding,
            "api_access": p.api_access,
            "features": p.features_json,
        } for p in plans])


# ── Coupon Validation ─────────────────────────────────────────────────────────

class CouponValidateView(APIView):
    """POST /marketplace-billing/coupon/validate/ — validate a coupon code."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        code = request.data.get("code", "").upper().strip()
        if not code:
            return Response({"valid": False, "message": "Code required."})

        try:
            coupon = CouponCode.objects.get(code=code, is_active=True)
        except CouponCode.DoesNotExist:
            return Response({"valid": False, "message": "Invalid or expired coupon code."})

        now = timezone.now()
        if coupon.valid_from and now < coupon.valid_from:
            return Response({"valid": False, "message": "Coupon not yet active."})
        if coupon.valid_until and now > coupon.valid_until:
            return Response({"valid": False, "message": "Coupon has expired."})
        if coupon.max_uses and coupon.uses_count >= coupon.max_uses:
            return Response({"valid": False, "message": "Coupon has reached its usage limit."})

        return Response({
            "valid": True,
            "code": coupon.code,
            "discount_type": coupon.discount_type,
            "discount_value": float(coupon.discount_value),
            "plan_restriction": coupon.plan.name if coupon.plan else None,
            "message": f"Coupon applied: {coupon.discount_value}{'%' if coupon.discount_type == 'percentage' else ' LKR'} off",
        })


# ── Apply Coupon ──────────────────────────────────────────────────────────────

class CouponApplyView(APIView):
    """POST /marketplace-billing/coupon/apply/ — apply coupon to a plan purchase."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        code = request.data.get("code", "").upper()
        plan_id = request.data.get("plan_id")

        try:
            coupon = CouponCode.objects.get(code=code, is_active=True)
        except CouponCode.DoesNotExist:
            return Response({"detail": "Invalid coupon."}, status=400)

        try:
            plan = BillingPlan.objects.get(pk=plan_id)
        except BillingPlan.DoesNotExist:
            return Response({"detail": "Invalid plan."}, status=400)

        if coupon.plan and coupon.plan != plan:
            return Response({"detail": "Coupon not valid for this plan."}, status=400)

        base_price = float(plan.price_monthly_lkr)
        if coupon.discount_type == "percentage":
            discount = base_price * float(coupon.discount_value) / 100
        elif coupon.discount_type == "fixed_lkr":
            discount = float(coupon.discount_value)
        else:  # ad_credit
            discount = 0

        final_price = max(0, base_price - discount)

        # Increment coupon uses
        coupon.uses_count += 1
        coupon.save(update_fields=["uses_count"])

        return Response({
            "plan": plan.name,
            "original_price_lkr": base_price,
            "discount_amount_lkr": discount,
            "final_price_lkr": final_price,
            "ad_credit_lkr": float(coupon.discount_value) if coupon.discount_type == "ad_credit" else 0,
            "message": "Coupon applied successfully.",
        })


# ── Wallet Top-Up ─────────────────────────────────────────────────────────────

class WalletTopUpView(APIView):
    """POST /marketplace-billing/wallet/top-up/ — add funds to ad wallet."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        employer = _get_employer(request)
        if not employer:
            return Response({"detail": "Employer account not found."}, status=403)

        amount = request.data.get("amount_lkr", 0)
        payment_reference = request.data.get("payment_reference", "")

        if float(amount) <= 0:
            return Response({"detail": "Amount must be positive."}, status=400)

        budget, _ = AdBudget.objects.get_or_create(employer=employer)
        budget.balance_lkr = float(budget.balance_lkr) + float(amount)
        budget.total_deposited_lkr = float(budget.total_deposited_lkr) + float(amount)
        budget.save(update_fields=["balance_lkr", "total_deposited_lkr", "updated_at"])

        # Record transaction
        tx = AdBudgetTransaction.objects.create(
            budget=budget,
            tx_type="deposit",
            amount_lkr=amount,
            balance_after_lkr=budget.balance_lkr,
            description="Manual top-up",
            reference=payment_reference,
        )

        return Response({
            "new_balance_lkr": float(budget.balance_lkr),
            "transaction_id": str(tx.id),
            "message": f"LKR {float(amount):,.0f} added to ad wallet.",
        })


# ── Job Ad Quality Score ──────────────────────────────────────────────────────

class JobAdQualityScoreView(APIView):
    """
    POST /marketplace-billing/job-quality-score/
    Validates a job post draft and returns a quality score + suggestions.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        d = request.data
        score = 0
        suggestions = []
        checks = []

        # Title
        title = d.get("title", "")
        if len(title) >= 5:
            score += 15
            checks.append({"label": "Job title", "passed": True})
        else:
            checks.append({"label": "Job title", "passed": False, "tip": "Add a clear job title (min 5 characters)"})
            suggestions.append("Add a clear, specific job title")

        # Description length
        desc = d.get("description", "")
        if len(desc) >= 200:
            score += 20
            checks.append({"label": "Job description (200+ chars)", "passed": True})
        else:
            checks.append({"label": "Job description", "passed": False, "tip": "Write at least 200 characters"})
            suggestions.append(f"Expand description (currently {len(desc)} chars, target 200+)")

        # Salary shown
        if d.get("salary_min") or d.get("salary_max"):
            score += 20
            checks.append({"label": "Salary range shown", "passed": True})
        else:
            checks.append({"label": "Salary range", "passed": False, "tip": "Adding salary increases applications by 40%+"})
            suggestions.append("Add salary range to attract more candidates")

        # Skills
        skills = d.get("required_skills", "")
        if skills and len(skills) >= 10:
            score += 15
            checks.append({"label": "Required skills listed", "passed": True})
        else:
            checks.append({"label": "Required skills", "passed": False, "tip": "List required skills"})
            suggestions.append("Add required skills to help candidates self-qualify")

        # Experience level
        if d.get("experience_level"):
            score += 10
            checks.append({"label": "Experience level", "passed": True})
        else:
            checks.append({"label": "Experience level", "passed": False, "tip": "Specify entry/mid/senior"})
            suggestions.append("Specify required experience level")

        # Job type
        if d.get("job_type"):
            score += 10
            checks.append({"label": "Job type (full/part/contract)", "passed": True})
        else:
            checks.append({"label": "Job type", "passed": False})
            suggestions.append("Specify job type (full-time, part-time, contract)")

        # Benefits
        if d.get("benefits"):
            score += 10
            checks.append({"label": "Benefits mentioned", "passed": True})
        else:
            checks.append({"label": "Benefits mentioned", "passed": False})
            suggestions.append("Mention key benefits to stand out")

        return Response({
            "score": score,
            "max_score": 100,
            "grade": "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 50 else "D",
            "label": "Excellent" if score >= 85 else "Good" if score >= 70 else "Fair" if score >= 50 else "Needs Work",
            "checks": checks,
            "suggestions": suggestions,
        })


# ── Fraud Risk Check ──────────────────────────────────────────────────────────

class FraudRiskCheckView(APIView):
    """
    POST /marketplace-billing/fraud-check/
    Pre-publication fraud/risk signals for a new job posting.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        d = request.data
        flags = []
        risk_score = 0

        title = d.get("title", "").lower()
        desc = d.get("description", "").lower()

        SCAM_SIGNALS = [
            "guaranteed income", "no experience needed", "work from home earn",
            "earn $", "earn lkr", "daily payment", "whatsapp only", "no interview",
            "send money", "western union", "upfront fee", "registration fee",
        ]
        for signal in SCAM_SIGNALS:
            if signal in title or signal in desc:
                flags.append(f"Suspicious phrase detected: '{signal}'")
                risk_score += 20

        # Missing key fields
        if not d.get("salary_min") and not d.get("salary_max"):
            risk_score += 5
        if not d.get("company_registration"):
            risk_score += 5
        if len(desc) < 100:
            flags.append("Very short job description — potential low quality")
            risk_score += 10

        risk_score = min(risk_score, 100)

        return Response({
            "risk_score": risk_score,
            "risk_level": "High" if risk_score >= 60 else "Medium" if risk_score >= 30 else "Low",
            "flags": flags,
            "can_publish": risk_score < 60,
            "requires_review": risk_score >= 30,
            "message": "Post blocked — requires manual review" if risk_score >= 60
                       else "Post flagged for review before going live" if risk_score >= 30
                       else "Post cleared for publishing",
        })


# ── Subscription Dashboard ────────────────────────────────────────────────────

class SubscriptionDashboardView(APIView):
    """GET /marketplace-billing/dashboard/ — employer billing overview."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        employer = _get_employer(request)
        if not employer:
            return Response({"detail": "Employer account not found."}, status=403)

        # Active subscription
        sub = EmployerSubscription.objects.filter(
            employer=employer, status="active"
        ).select_related("plan").first()

        # Invoices summary
        invoices = Invoice.objects.filter(employer=employer).order_by("-created_at")[:5]

        # Wallet
        wallet = AdBudget.objects.filter(employer=employer).first()

        from apps.jobs.models import JobListing
        active_jobs = JobListing.objects.filter(employer=employer, status="active").count()

        return Response({
            "employer": {"slug": employer.slug, "name": employer.company_name, "plan": employer.plan},
            "active_jobs": active_jobs,
            "job_limit": sub.plan.job_posting_limit if sub else employer.monthly_job_limit,
            "subscription": {
                "plan_name": sub.plan.name if sub else "Free",
                "status": sub.status if sub else "free",
                "billing_cycle": sub.billing_cycle if sub else None,
                "expires_at": sub.expires_at if sub else None,
                "auto_renew": sub.auto_renew if sub else False,
            } if sub else {"plan_name": "Free", "status": "free"},
            "wallet": {
                "balance_lkr": float(wallet.balance_lkr) if wallet else 0,
                "total_spent_lkr": float(wallet.total_spent_lkr) if wallet else 0,
            },
            "recent_invoices": [{
                "id": str(inv.id),
                "invoice_number": inv.invoice_number,
                "total_lkr": float(inv.total_lkr),
                "status": inv.status,
                "created_at": inv.created_at,
            } for inv in invoices],
        })


# ── Employer Onboarding Wizard State ─────────────────────────────────────────

class OnboardingWizardView(APIView):
    """
    GET /marketplace-billing/onboarding/
    Returns what onboarding steps are complete for a new employer.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        employer = _get_employer(request)
        if not employer:
            steps = [{"step": 1, "label": "Create Employer Account", "done": False}]
            return Response({"completed_pct": 0, "steps": steps})

        from apps.jobs.models import JobListing
        has_logo = bool(employer.logo)
        has_description = len(employer.description) >= 50
        has_jobs = JobListing.objects.filter(employer=employer).exists()
        has_billing = EmployerSubscription.objects.filter(employer=employer).exists()
        has_team = employer.team_members.count() > 1

        steps = [
            {"step": 1, "label": "Company profile created", "done": True},
            {"step": 2, "label": "Add company logo", "done": has_logo},
            {"step": 3, "label": "Write company description", "done": has_description},
            {"step": 4, "label": "Post your first job", "done": has_jobs},
            {"step": 5, "label": "Set up billing or stay free", "done": has_billing},
            {"step": 6, "label": "Invite team members", "done": has_team},
        ]
        done_count = sum(1 for s in steps if s["done"])
        return Response({
            "completed_pct": round(done_count / len(steps) * 100),
            "steps": steps,
            "next_step": next((s for s in steps if not s["done"]), None),
        })
