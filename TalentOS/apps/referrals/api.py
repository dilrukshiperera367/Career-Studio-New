"""
Referrals & Employee Advocacy — REST API
All routes registered at /api/v1/referrals/
"""

import secrets
from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg
from rest_framework import serializers, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter

from apps.referrals.models import (
    ReferralProgram, ReferralCampaign, Referral, ReferralLink,
    BonusRule, BonusPayout, ReferralLeaderboard,
    ReferralRequest, AmbassadorProfile, HMReferralPrompt,
    ReferralQualityScore, ReferralAnalyticsSnapshot,
)


# ── Serializers ───────────────────────────────────────────────────────────────

class ReferralProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferralProgram
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class ReferralCampaignSerializer(serializers.ModelSerializer):
    referral_count = serializers.SerializerMethodField()

    class Meta:
        model = ReferralCampaign
        fields = "__all__"
        read_only_fields = ["id", "created_at"]

    def get_referral_count(self, obj):
        return obj.referrals.count()


class ReferralSerializer(serializers.ModelSerializer):
    referrer_display = serializers.SerializerMethodField()
    quality_score_detail = serializers.SerializerMethodField()

    class Meta:
        model = Referral
        fields = "__all__"
        read_only_fields = ["id", "submitted_at", "updated_at"]

    def get_referrer_display(self, obj):
        if obj.referrer:
            return f"{obj.referrer.first_name} {obj.referrer.last_name}".strip()
        return obj.referrer_name or obj.referrer_email

    def get_quality_score_detail(self, obj):
        try:
            qs = obj.quality_detail
            return {
                "overall": qs.overall_score,
                "profile_completeness": qs.profile_completeness,
                "skills_match": qs.skills_match,
                "relationship_strength": qs.relationship_strength,
            }
        except Exception:
            return None


class ReferralLinkSerializer(serializers.ModelSerializer):
    share_url = serializers.SerializerMethodField()

    class Meta:
        model = ReferralLink
        fields = "__all__"
        read_only_fields = ["id", "token", "click_count", "conversion_count", "created_at"]

    def get_share_url(self, obj):
        return f"/refer/{obj.token}"


class BonusRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = BonusRule
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class BonusPayoutSerializer(serializers.ModelSerializer):
    referral_candidate = serializers.SerializerMethodField()
    recipient_display = serializers.SerializerMethodField()

    class Meta:
        model = BonusPayout
        fields = "__all__"
        read_only_fields = ["id", "created_at", "approved_at", "paid_at"]

    def get_referral_candidate(self, obj):
        return obj.referral.candidate_name

    def get_recipient_display(self, obj):
        if obj.recipient:
            return f"{obj.recipient.first_name} {obj.recipient.last_name}".strip()
        return obj.recipient_email


class ReferralLeaderboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferralLeaderboard
        fields = "__all__"
        read_only_fields = ["id", "generated_at"]


class ReferralRequestSerializer(serializers.ModelSerializer):
    requested_from_name = serializers.SerializerMethodField()
    requested_by_name = serializers.SerializerMethodField()
    job_title = serializers.SerializerMethodField()

    class Meta:
        model = ReferralRequest
        fields = "__all__"
        read_only_fields = ["id", "sent_at"]

    def get_requested_from_name(self, obj):
        return f"{obj.requested_from.first_name} {obj.requested_from.last_name}".strip()

    def get_requested_by_name(self, obj):
        return f"{obj.requested_by.first_name} {obj.requested_by.last_name}".strip()

    def get_job_title(self, obj):
        return obj.job.title if obj.job else ""


class AmbassadorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AmbassadorProfile
        fields = "__all__"
        read_only_fields = ["id", "total_referrals", "total_hires", "total_earnings",
                            "created_at", "updated_at"]


class HMReferralPromptSerializer(serializers.ModelSerializer):
    hm_name = serializers.SerializerMethodField()
    job_title = serializers.SerializerMethodField()

    class Meta:
        model = HMReferralPrompt
        fields = "__all__"
        read_only_fields = ["id", "created_at"]

    def get_hm_name(self, obj):
        return f"{obj.hiring_manager.first_name} {obj.hiring_manager.last_name}".strip()

    def get_job_title(self, obj):
        return obj.job.title if obj.job else ""


class ReferralQualityScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferralQualityScore
        fields = "__all__"
        read_only_fields = ["id", "scored_at"]


class ReferralAnalyticsSnapshotSerializer(serializers.ModelSerializer):
    hire_rate = serializers.SerializerMethodField()
    duplicate_rate = serializers.SerializerMethodField()

    class Meta:
        model = ReferralAnalyticsSnapshot
        fields = "__all__"
        read_only_fields = ["id"]

    def get_hire_rate(self, obj):
        if obj.total_referrals:
            return round(obj.hired / obj.total_referrals * 100, 1)
        return 0.0

    def get_duplicate_rate(self, obj):
        if obj.total_referrals:
            return round(obj.duplicates / obj.total_referrals * 100, 1)
        return 0.0


# ── ViewSets ──────────────────────────────────────────────────────────────────

class ReferralProgramViewSet(viewsets.ModelViewSet):
    serializer_class = ReferralProgramSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ReferralProgram.objects.filter(tenant=self.request.user.tenant)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)

    @action(detail=True, methods=["get"])
    def stats(self, request, pk=None):
        """Summary stats for a program."""
        program = self.get_object()
        referrals = Referral.objects.filter(program=program)
        total = referrals.count()
        hired = referrals.filter(status__in=["hired", "pending_payout", "paid"]).count()
        pending_payouts = BonusPayout.objects.filter(
            referral__program=program, status__in=["pending", "approved"]
        ).aggregate(total=Sum("amount"))["total"] or 0
        return Response({
            "total_referrals": total,
            "hired": hired,
            "conversion_rate": round(hired / total * 100, 1) if total else 0.0,
            "active_campaigns": program.campaigns.filter(status="active").count(),
            "pending_payout_amount": str(pending_payouts),
            "ambassador_count": program.ambassadors.filter(status="active").count(),
        })


class ReferralCampaignViewSet(viewsets.ModelViewSet):
    serializer_class = ReferralCampaignSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ReferralCampaign.objects.filter(tenant=self.request.user.tenant)
        if self.request.query_params.get("status"):
            qs = qs.filter(status=self.request.query_params["status"])
        if self.request.query_params.get("program"):
            qs = qs.filter(program_id=self.request.query_params["program"])
        return qs.select_related("program")

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        campaign = self.get_object()
        campaign.status = "paused"
        campaign.save(update_fields=["status"])
        return Response({"status": "paused"})

    @action(detail=True, methods=["post"])
    def end(self, request, pk=None):
        campaign = self.get_object()
        campaign.status = "ended"
        campaign.save(update_fields=["status"])
        return Response({"status": "ended"})

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        campaign = self.get_object()
        campaign.status = "active"
        campaign.save(update_fields=["status"])
        return Response({"status": "active"})

    @action(detail=True, methods=["get"])
    def referrals(self, request, pk=None):
        """All referrals under this campaign."""
        campaign = self.get_object()
        qs = campaign.referrals.all()
        return Response(ReferralSerializer(qs, many=True).data)


class ReferralViewSet(viewsets.ModelViewSet):
    serializer_class = ReferralSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Referral.objects.filter(tenant=self.request.user.tenant)
        params = self.request.query_params
        if params.get("status"):
            qs = qs.filter(status=params["status"])
        if params.get("program"):
            qs = qs.filter(program_id=params["program"])
        if params.get("campaign"):
            qs = qs.filter(campaign_id=params["campaign"])
        if params.get("referrer"):
            qs = qs.filter(referrer_id=params["referrer"])
        if params.get("referrer_type"):
            qs = qs.filter(referrer_type=params["referrer_type"])
        if params.get("is_duplicate"):
            qs = qs.filter(is_duplicate=params["is_duplicate"] == "true")
        if params.get("job"):
            qs = qs.filter(job_id=params["job"])
        if params.get("q"):
            q = params["q"]
            qs = qs.filter(
                Q(candidate_name__icontains=q) |
                Q(candidate_email__icontains=q) |
                Q(referrer_name__icontains=q) |
                Q(referrer_email__icontains=q)
            )
        return qs.select_related("referrer", "job", "campaign").distinct()

    def perform_create(self, serializer):
        # Duplicate detection: check if candidate_email already exists for this tenant+job
        data = serializer.validated_data
        tenant = self.request.user.tenant
        existing = Referral.objects.filter(
            tenant=tenant,
            candidate_email=data.get("candidate_email", ""),
        )
        if data.get("job"):
            existing = existing.filter(job=data["job"])
        existing = existing.exclude(status__in=["withdrawn", "not_hired"]).first()

        if existing:
            obj = serializer.save(
                tenant=tenant,
                referrer=self.request.user,
                referrer_type="employee",
                is_duplicate=True,
                duplicate_of=existing,
                status="duplicate",
            )
        else:
            serializer.save(
                tenant=tenant,
                referrer=self.request.user,
                referrer_type="employee",
            )

    @action(detail=True, methods=["post"])
    def advance(self, request, pk=None):
        """Advance referral status along the funnel."""
        referral = self.get_object()
        next_status = request.data.get("status")
        valid = ["under_review", "screening", "interviewing", "offer_extended",
                 "hired", "not_hired", "pending_payout", "paid", "withdrawn"]
        if next_status not in valid:
            return Response({"error": f"Invalid status. Valid: {valid}"}, status=400)
        referral.status = next_status
        if next_status == "hired" and not referral.hired_at:
            referral.hired_at = timezone.now()
        referral.save(update_fields=["status", "hired_at", "updated_at"])
        return Response({"status": next_status})

    @action(detail=True, methods=["post"])
    def resolve_duplicate(self, request, pk=None):
        """Resolve a duplicate conflict — mark as valid or keep as duplicate."""
        referral = self.get_object()
        resolution = request.data.get("resolution", "keep_duplicate")  # "keep_duplicate" | "make_primary"
        notes = request.data.get("notes", "")
        if resolution == "make_primary":
            referral.is_duplicate = False
            referral.duplicate_of = None
            referral.status = "under_review"
        referral.duplicate_resolved_at = timezone.now()
        referral.duplicate_resolution_notes = notes
        referral.save(update_fields=["is_duplicate", "duplicate_of", "status",
                                     "duplicate_resolved_at", "duplicate_resolution_notes", "updated_at"])
        return Response({"resolution": resolution, "status": referral.status})

    @action(detail=True, methods=["post"])
    def score_quality(self, request, pk=None):
        """Save or update quality score breakdown for this referral."""
        referral = self.get_object()
        data = request.data
        components = {
            "profile_completeness": float(data.get("profile_completeness", 0)),
            "skills_match": float(data.get("skills_match", 0)),
            "relationship_strength": float(data.get("relationship_strength", 0)),
            "interview_pass_rate": float(data.get("interview_pass_rate", 0)),
            "time_to_hire": float(data.get("time_to_hire", 0)),
        }
        overall = round(sum(components.values()) / len(components), 1)
        qs, _ = ReferralQualityScore.objects.update_or_create(
            referral=referral,
            defaults={**components, "overall_score": overall,
                      "notes": data.get("notes", "")}
        )
        referral.quality_score = overall
        referral.save(update_fields=["quality_score", "updated_at"])
        return Response(ReferralQualityScoreSerializer(qs).data)

    @action(detail=True, methods=["post"])
    def trigger_payout(self, request, pk=None):
        """Manually trigger bonus payout creation for a hired referral."""
        referral = self.get_object()
        if referral.status not in ["hired", "pending_payout"]:
            return Response({"error": "Referral must be hired first."}, status=400)
        rules = BonusRule.objects.filter(
            program=referral.program, is_active=True, trigger_event="hired"
        )
        created = 0
        for rule in rules:
            if rule.referrer_type_filter and referral.referrer_type != rule.referrer_type_filter:
                continue
            _, was_new = BonusPayout.objects.get_or_create(
                tenant=referral.tenant,
                referral=referral,
                rule=rule,
                defaults={
                    "recipient": referral.referrer,
                    "recipient_email": referral.referrer_email,
                    "amount": rule.amount,
                    "currency": rule.currency,
                    "status": "pending",
                }
            )
            if was_new:
                created += 1
        referral.status = "pending_payout"
        referral.save(update_fields=["status", "updated_at"])
        return Response({"payouts_created": created})


class ReferralLinkViewSet(viewsets.ModelViewSet):
    serializer_class = ReferralLinkSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ReferralLink.objects.filter(tenant=self.request.user.tenant)
        if self.request.query_params.get("referrer"):
            qs = qs.filter(referrer_id=self.request.query_params["referrer"])
        if self.request.query_params.get("job"):
            qs = qs.filter(job_id=self.request.query_params["job"])
        if self.request.query_params.get("campaign"):
            qs = qs.filter(campaign_id=self.request.query_params["campaign"])
        return qs.select_related("referrer", "job")

    def perform_create(self, serializer):
        serializer.save(
            tenant=self.request.user.tenant,
            referrer=self.request.user,
            token=secrets.token_urlsafe(24),
        )

    @action(detail=True, methods=["post"])
    def track_click(self, request, pk=None):
        """Increment click count (called by public link redirect)."""
        link = self.get_object()
        ReferralLink.objects.filter(pk=link.pk).update(
            click_count=link.click_count + 1
        )
        return Response({"clicks": link.click_count + 1})

    @action(detail=False, methods=["get"])
    def my_links(self, request):
        """Return the current user's referral links."""
        qs = ReferralLink.objects.filter(
            tenant=request.user.tenant,
            referrer=request.user,
            is_active=True,
        ).select_related("job", "campaign")
        return Response(ReferralLinkSerializer(qs, many=True).data)


class BonusRuleViewSet(viewsets.ModelViewSet):
    serializer_class = BonusRuleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = BonusRule.objects.filter(tenant=self.request.user.tenant)
        if self.request.query_params.get("program"):
            qs = qs.filter(program_id=self.request.query_params["program"])
        if self.request.query_params.get("trigger_event"):
            qs = qs.filter(trigger_event=self.request.query_params["trigger_event"])
        if self.request.query_params.get("is_active"):
            qs = qs.filter(is_active=self.request.query_params["is_active"] == "true")
        return qs

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)


class BonusPayoutViewSet(viewsets.ModelViewSet):
    serializer_class = BonusPayoutSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = BonusPayout.objects.filter(tenant=self.request.user.tenant)
        if self.request.query_params.get("status"):
            qs = qs.filter(status=self.request.query_params["status"])
        if self.request.query_params.get("recipient"):
            qs = qs.filter(recipient_id=self.request.query_params["recipient"])
        if self.request.query_params.get("referral"):
            qs = qs.filter(referral_id=self.request.query_params["referral"])
        return qs.select_related("referral", "recipient", "approved_by")

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve a pending payout."""
        payout = self.get_object()
        if payout.status != "pending":
            return Response({"error": "Payout is not in pending state."}, status=400)
        payout.status = "approved"
        payout.approved_by = request.user
        payout.approved_at = timezone.now()
        payout.save(update_fields=["status", "approved_by", "approved_at"])
        return Response(BonusPayoutSerializer(payout).data)

    @action(detail=True, methods=["post"])
    def mark_paid(self, request, pk=None):
        """Mark payout as paid."""
        payout = self.get_object()
        payout.status = "paid"
        payout.paid_at = timezone.now()
        payout.payment_reference = request.data.get("payment_reference", "")
        payout.notes = request.data.get("notes", payout.notes)
        payout.save(update_fields=["status", "paid_at", "payment_reference", "notes"])
        return Response(BonusPayoutSerializer(payout).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        payout = self.get_object()
        payout.status = "cancelled"
        payout.notes = request.data.get("notes", payout.notes)
        payout.save(update_fields=["status", "notes"])
        return Response({"status": "cancelled"})

    @action(detail=True, methods=["post"])
    def hold(self, request, pk=None):
        payout = self.get_object()
        payout.status = "on_hold"
        payout.notes = request.data.get("notes", payout.notes)
        payout.save(update_fields=["status", "notes"])
        return Response({"status": "on_hold"})

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Aggregated payout summary for the tenant."""
        qs = self.get_queryset()
        totals = qs.aggregate(
            total_paid=Sum("amount", filter=Q(status="paid")),
            total_pending=Sum("amount", filter=Q(status__in=["pending", "approved"])),
            count_paid=Count("id", filter=Q(status="paid")),
            count_pending=Count("id", filter=Q(status__in=["pending", "approved"])),
        )
        return Response({
            "total_paid": str(totals["total_paid"] or 0),
            "total_pending": str(totals["total_pending"] or 0),
            "count_paid": totals["count_paid"] or 0,
            "count_pending": totals["count_pending"] or 0,
        })


class ReferralLeaderboardViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ReferralLeaderboardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ReferralLeaderboard.objects.filter(tenant=self.request.user.tenant)
        if self.request.query_params.get("program"):
            qs = qs.filter(program_id=self.request.query_params["program"])
        if self.request.query_params.get("period"):
            qs = qs.filter(period=self.request.query_params["period"])
        return qs

    @action(detail=False, methods=["post"])
    def recalculate(self, request):
        """Trigger live leaderboard recalculation for a program."""
        program_id = request.data.get("program_id")
        try:
            program = ReferralProgram.objects.get(
                pk=program_id, tenant=request.user.tenant
            )
        except ReferralProgram.DoesNotExist:
            return Response({"error": "Program not found."}, status=404)

        today = timezone.now().date()
        month_start = today.replace(day=1)
        computed = []

        for period, start in [("month", month_start), ("all_time", None)]:
            qs = Referral.objects.filter(
                program=program,
                status__in=["hired", "pending_payout", "paid"],
            )
            if start:
                qs = qs.filter(submitted_at__date__gte=start)

            raw = (
                qs.values("referrer_id", "referrer__first_name", "referrer__last_name", "referrer__email")
                .annotate(
                    referral_count=Count("id"),
                    earnings=Sum("payouts__amount", filter=Q(payouts__status="paid")),
                )
                .order_by("-referral_count")[:50]
            )

            rankings = [
                {
                    "rank": i,
                    "user_id": str(row["referrer_id"]) if row["referrer_id"] else None,
                    "name": f"{row['referrer__first_name'] or ''} {row['referrer__last_name'] or ''}".strip()
                            or row["referrer__email"],
                    "referrals": row["referral_count"],
                    "hires": row["referral_count"],
                    "earnings": str(row["earnings"] or 0),
                }
                for i, row in enumerate(raw, start=1)
            ]

            lb, _ = ReferralLeaderboard.objects.update_or_create(
                tenant=request.user.tenant,
                program=program,
                period=period,
                period_start=start or today.replace(month=1, day=1),
                defaults={"rankings": rankings},
            )
            computed.append({"period": period, "entries": len(rankings)})

        return Response({"computed": computed})


class ReferralRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ReferralRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ReferralRequest.objects.filter(tenant=self.request.user.tenant)
        params = self.request.query_params
        if params.get("status"):
            qs = qs.filter(status=params["status"])
        if params.get("requested_from"):
            qs = qs.filter(requested_from_id=params["requested_from"])
        if params.get("requested_by"):
            qs = qs.filter(requested_by_id=params["requested_by"])
        if params.get("job"):
            qs = qs.filter(job_id=params["job"])
        if params.get("is_hm_prompt"):
            qs = qs.filter(is_hm_prompt=params["is_hm_prompt"] == "true")
        return qs.select_related("requested_from", "requested_by", "job")

    def perform_create(self, serializer):
        serializer.save(
            tenant=self.request.user.tenant,
            requested_by=self.request.user,
        )

    @action(detail=True, methods=["post"])
    def mark_viewed(self, request, pk=None):
        req = self.get_object()
        if not req.viewed_at:
            req.viewed_at = timezone.now()
            req.status = "viewed"
            req.save(update_fields=["viewed_at", "status"])
        return Response({"status": "viewed"})

    @action(detail=True, methods=["post"])
    def mark_acted(self, request, pk=None):
        req = self.get_object()
        req.status = "acted"
        req.acted_at = timezone.now()
        req.save(update_fields=["status", "acted_at"])
        return Response({"status": "acted"})

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        req = self.get_object()
        req.status = "declined"
        req.save(update_fields=["status"])
        return Response({"status": "declined"})

    @action(detail=False, methods=["post"])
    def bulk_send(self, request):
        """Send referral requests to multiple employees for a job."""
        program_id = request.data.get("program_id")
        job_id = request.data.get("job_id")
        user_ids = request.data.get("user_ids", [])
        message = request.data.get("message", "")
        campaign_id = request.data.get("campaign_id")

        try:
            program = ReferralProgram.objects.get(pk=program_id, tenant=request.user.tenant)
        except ReferralProgram.DoesNotExist:
            return Response({"error": "Program not found"}, status=404)

        from apps.jobs.models import Job
        try:
            job = Job.objects.get(pk=job_id, tenant=request.user.tenant)
        except Job.DoesNotExist:
            return Response({"error": "Job not found"}, status=404)

        from apps.accounts.models import User
        campaign = None
        if campaign_id:
            try:
                campaign = ReferralCampaign.objects.get(pk=campaign_id, tenant=request.user.tenant)
            except ReferralCampaign.DoesNotExist:
                pass

        created = 0
        for uid in user_ids:
            try:
                user = User.objects.get(pk=uid, tenant=request.user.tenant)
            except User.DoesNotExist:
                continue
            ReferralRequest.objects.create(
                tenant=request.user.tenant,
                program=program,
                job=job,
                campaign=campaign,
                requested_from=user,
                requested_by=request.user,
                message=message,
            )
            created += 1

        return Response({"created": created})


class AmbassadorProfileViewSet(viewsets.ModelViewSet):
    serializer_class = AmbassadorProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = AmbassadorProfile.objects.filter(tenant=self.request.user.tenant)
        params = self.request.query_params
        if params.get("program"):
            qs = qs.filter(program_id=params["program"])
        if params.get("status"):
            qs = qs.filter(status=params["status"])
        if params.get("ambassador_type"):
            qs = qs.filter(ambassador_type=params["ambassador_type"])
        return qs.select_related("user", "program")

    def perform_create(self, serializer):
        token = secrets.token_urlsafe(24)
        serializer.save(tenant=self.request.user.tenant, invited_by=self.request.user, invite_token=token)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        amb = self.get_object()
        amb.status = "active"
        amb.save(update_fields=["status"])
        return Response({"status": "active"})

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        amb = self.get_object()
        amb.status = "revoked"
        amb.save(update_fields=["status"])
        return Response({"status": "revoked"})

    @action(detail=True, methods=["get"])
    def referrals(self, request, pk=None):
        """All referrals made by this ambassador."""
        amb = self.get_object()
        qs = Referral.objects.filter(
            tenant=request.user.tenant,
            referrer_email=amb.email,
            referrer_type__in=["alumni", "ambassador"],
        )
        return Response(ReferralSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"])
    def update_stats(self, request, pk=None):
        """Recalculate totals for this ambassador."""
        amb = self.get_object()
        qs = Referral.objects.filter(
            tenant=request.user.tenant,
        ).filter(
            Q(referrer=amb.user) | Q(referrer_email=amb.email)
        )
        amb.total_referrals = qs.count()
        amb.total_hires = qs.filter(status__in=["hired", "pending_payout", "paid"]).count()
        paid = BonusPayout.objects.filter(
            tenant=request.user.tenant,
            referral__in=qs,
            status="paid",
        ).aggregate(total=Sum("amount"))["total"] or 0
        amb.total_earnings = paid
        amb.save(update_fields=["total_referrals", "total_hires", "total_earnings", "updated_at"])
        return Response(AmbassadorProfileSerializer(amb).data)


class HMReferralPromptViewSet(viewsets.ModelViewSet):
    serializer_class = HMReferralPromptSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = HMReferralPrompt.objects.filter(tenant=self.request.user.tenant)
        params = self.request.query_params
        if params.get("status"):
            qs = qs.filter(status=params["status"])
        if params.get("hiring_manager"):
            qs = qs.filter(hiring_manager_id=params["hiring_manager"])
        if params.get("job"):
            qs = qs.filter(job_id=params["job"])
        return qs.select_related("hiring_manager", "job")

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        prompt = self.get_object()
        prompt.status = "sent"
        prompt.sent_at = timezone.now()
        prompt.save(update_fields=["status", "sent_at"])
        return Response({"status": "sent"})

    @action(detail=True, methods=["post"])
    def mark_viewed(self, request, pk=None):
        prompt = self.get_object()
        if not prompt.viewed_at:
            prompt.viewed_at = timezone.now()
            prompt.status = "viewed"
            prompt.save(update_fields=["viewed_at", "status"])
        return Response({"status": "viewed"})


class ReferralQualityScoreViewSet(viewsets.ModelViewSet):
    serializer_class = ReferralQualityScoreSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ReferralQualityScore.objects.filter(
            referral__tenant=self.request.user.tenant
        ).select_related("referral")


class ReferralAnalyticsSnapshotViewSet(viewsets.ModelViewSet):
    serializer_class = ReferralAnalyticsSnapshotSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ReferralAnalyticsSnapshot.objects.filter(tenant=self.request.user.tenant)
        params = self.request.query_params
        if params.get("program"):
            qs = qs.filter(program_id=params["program"])
        if params.get("period"):
            qs = qs.filter(period=params["period"])
        if params.get("date_from"):
            qs = qs.filter(snapshot_date__gte=params["date_from"])
        if params.get("date_to"):
            qs = qs.filter(snapshot_date__lte=params["date_to"])
        return qs

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Live aggregated analytics — all referrals for this tenant."""
        tenant = request.user.tenant
        program_id = request.query_params.get("program")

        qs = Referral.objects.filter(tenant=tenant)
        if program_id:
            qs = qs.filter(program_id=program_id)

        total = qs.count()
        hired = qs.filter(status__in=["hired", "pending_payout", "paid"]).count()
        duplicates = qs.filter(is_duplicate=True).count()
        avg_quality = qs.filter(quality_score__isnull=False).aggregate(
            avg=Avg("quality_score")
        )["avg"] or 0

        by_status = list(
            qs.values("status").annotate(count=Count("id")).order_by("-count")
        )
        by_type = list(
            qs.values("referrer_type").annotate(count=Count("id")).order_by("-count")
        )
        by_job = list(
            qs.values("job__title").annotate(count=Count("id")).order_by("-count")[:10]
        )

        payout_qs = BonusPayout.objects.filter(tenant=tenant)
        if program_id:
            payout_qs = payout_qs.filter(referral__program_id=program_id)

        payout_totals = payout_qs.aggregate(
            paid=Sum("amount", filter=Q(status="paid")),
            pending=Sum("amount", filter=Q(status__in=["pending", "approved"])),
        )

        return Response({
            "total_referrals": total,
            "hired": hired,
            "duplicates": duplicates,
            "conversion_rate": round(hired / total * 100, 1) if total else 0.0,
            "duplicate_rate": round(duplicates / total * 100, 1) if total else 0.0,
            "avg_quality_score": round(avg_quality, 1),
            "total_bonus_paid": str(payout_totals["paid"] or 0),
            "total_bonus_pending": str(payout_totals["pending"] or 0),
            "by_status": by_status,
            "by_referrer_type": by_type,
            "top_jobs": by_job,
        })


# ── Router ────────────────────────────────────────────────────────────────────

router = DefaultRouter()
router.register("programs", ReferralProgramViewSet, basename="referral-program")
router.register("campaigns", ReferralCampaignViewSet, basename="referral-campaign")
router.register("referrals", ReferralViewSet, basename="referral")
router.register("links", ReferralLinkViewSet, basename="referral-link")
router.register("bonus-rules", BonusRuleViewSet, basename="bonus-rule")
router.register("bonus-payouts", BonusPayoutViewSet, basename="bonus-payout")
router.register("leaderboard", ReferralLeaderboardViewSet, basename="referral-leaderboard")
router.register("requests", ReferralRequestViewSet, basename="referral-request")
router.register("ambassadors", AmbassadorProfileViewSet, basename="ambassador")
router.register("hm-prompts", HMReferralPromptViewSet, basename="hm-prompt")
router.register("quality-scores", ReferralQualityScoreViewSet, basename="quality-score")
router.register("analytics", ReferralAnalyticsSnapshotViewSet, basename="referral-analytics")

from django.urls import path, include

urlpatterns = router.urls
