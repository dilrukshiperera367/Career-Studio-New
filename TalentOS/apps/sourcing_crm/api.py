"""
Sourcing CRM & Talent Pools — REST API
All routes registered at /api/v1/sourcing/
"""

from django.utils import timezone
from django.db.models import Q, Count, Avg
from rest_framework import serializers, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter

from apps.sourcing_crm.models import (
    Prospect, TalentPool, PoolMembership, PoolHealthSnapshot,
    FollowUpTask, NurtureSequence, SequenceStep, SequenceEnrollment,
    OutreachCampaign, OutreachMessage, SavedSegment, DoNotContact,
    WarmIntro, CandidatePreference, SimilarProspectSuggestion,
    OutreachAnalyticsSnapshot,
)


# ── Serializers ───────────────────────────────────────────────────────────────

class ProspectSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Prospect
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()


class TalentPoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = TalentPool
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "member_count",
                            "engaged_count", "converted_count", "health_score"]


class PoolMembershipSerializer(serializers.ModelSerializer):
    prospect_name = serializers.SerializerMethodField()
    prospect_email = serializers.SerializerMethodField()
    prospect_title = serializers.SerializerMethodField()

    class Meta:
        model = PoolMembership
        fields = "__all__"
        read_only_fields = ["id", "added_at"]

    def get_prospect_name(self, obj):
        return f"{obj.prospect.first_name} {obj.prospect.last_name}".strip()

    def get_prospect_email(self, obj):
        return obj.prospect.email

    def get_prospect_title(self, obj):
        return obj.prospect.current_title


class PoolHealthSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = PoolHealthSnapshot
        fields = "__all__"
        read_only_fields = ["id"]


class FollowUpTaskSerializer(serializers.ModelSerializer):
    prospect_name = serializers.SerializerMethodField()

    class Meta:
        model = FollowUpTask
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_prospect_name(self, obj):
        return f"{obj.prospect.first_name} {obj.prospect.last_name}".strip()


class NurtureSequenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NurtureSequence
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class SequenceStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = SequenceStep
        fields = "__all__"
        read_only_fields = ["id"]


class SequenceEnrollmentSerializer(serializers.ModelSerializer):
    prospect_name = serializers.SerializerMethodField()

    class Meta:
        model = SequenceEnrollment
        fields = "__all__"
        read_only_fields = ["id", "enrolled_at"]

    def get_prospect_name(self, obj):
        return f"{obj.prospect.first_name} {obj.prospect.last_name}".strip()


class OutreachCampaignSerializer(serializers.ModelSerializer):
    open_rate = serializers.SerializerMethodField()
    reply_rate = serializers.SerializerMethodField()
    conversion_rate = serializers.SerializerMethodField()

    class Meta:
        model = OutreachCampaign
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at",
                            "sent_count", "delivered_count", "opened_count",
                            "clicked_count", "replied_count", "bounced_count",
                            "unsubscribed_count", "converted_count"]

    def get_open_rate(self, obj):
        if obj.delivered_count:
            return round(obj.opened_count / obj.delivered_count * 100, 1)
        return 0.0

    def get_reply_rate(self, obj):
        if obj.sent_count:
            return round(obj.replied_count / obj.sent_count * 100, 1)
        return 0.0

    def get_conversion_rate(self, obj):
        if obj.replied_count:
            return round(obj.converted_count / obj.replied_count * 100, 1)
        return 0.0


class OutreachMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutreachMessage
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class SavedSegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedSegment
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "prospect_count"]


class DoNotContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoNotContact
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class WarmIntroSerializer(serializers.ModelSerializer):
    prospect_name = serializers.SerializerMethodField()

    class Meta:
        model = WarmIntro
        fields = "__all__"
        read_only_fields = ["id", "created_at"]

    def get_prospect_name(self, obj):
        return f"{obj.prospect.first_name} {obj.prospect.last_name}".strip()


class CandidatePreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidatePreference
        fields = "__all__"
        read_only_fields = ["id", "unsubscribe_token", "updated_at"]


class SimilarProspectSuggestionSerializer(serializers.ModelSerializer):
    suggested_name = serializers.SerializerMethodField()
    suggested_title = serializers.SerializerMethodField()

    class Meta:
        model = SimilarProspectSuggestion
        fields = "__all__"
        read_only_fields = ["id", "created_at"]

    def get_suggested_name(self, obj):
        return f"{obj.suggested_prospect.first_name} {obj.suggested_prospect.last_name}".strip()

    def get_suggested_title(self, obj):
        return obj.suggested_prospect.current_title


class OutreachAnalyticsSnapshotSerializer(serializers.ModelSerializer):
    open_rate = serializers.SerializerMethodField()
    reply_rate = serializers.SerializerMethodField()
    delivery_rate = serializers.SerializerMethodField()
    conversion_rate = serializers.SerializerMethodField()

    class Meta:
        model = OutreachAnalyticsSnapshot
        fields = "__all__"
        read_only_fields = ["id"]

    def get_open_rate(self, obj):
        return round(obj.opened / obj.delivered * 100, 1) if obj.delivered else 0.0

    def get_reply_rate(self, obj):
        return round(obj.replied / obj.sent * 100, 1) if obj.sent else 0.0

    def get_delivery_rate(self, obj):
        return round(obj.delivered / obj.sent * 100, 1) if obj.sent else 0.0

    def get_conversion_rate(self, obj):
        return round(obj.prospects_converted / obj.prospects_contacted * 100, 1) if obj.prospects_contacted else 0.0


# ── ViewSets ──────────────────────────────────────────────────────────────────

class ProspectViewSet(viewsets.ModelViewSet):
    serializer_class = ProspectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Prospect.objects.filter(tenant=self.request.user.tenant)
        params = self.request.query_params
        if params.get("stage"):
            qs = qs.filter(stage=params["stage"])
        if params.get("source"):
            qs = qs.filter(source=params["source"])
        if params.get("recruiter"):
            qs = qs.filter(recruiter_id=params["recruiter"])
        if params.get("pool"):
            qs = qs.filter(pool_memberships__pool_id=params["pool"])
        if params.get("is_alumni"):
            qs = qs.filter(is_alumni=params["is_alumni"] == "true")
        if params.get("is_silver_medalist"):
            qs = qs.filter(is_silver_medalist=params["is_silver_medalist"] == "true")
        if params.get("is_passive"):
            qs = qs.filter(is_passive=params["is_passive"] == "true")
        if params.get("is_contractor"):
            qs = qs.filter(is_contractor=params["is_contractor"] == "true")
        if params.get("consent_status"):
            qs = qs.filter(consent_status=params["consent_status"])
        if params.get("q"):
            q = params["q"]
            qs = qs.filter(
                Q(first_name__icontains=q) | Q(last_name__icontains=q) |
                Q(email__icontains=q) | Q(current_title__icontains=q) |
                Q(current_company__icontains=q)
            )
        return qs.distinct()

    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        """Mark a prospect as converted to applicant."""
        prospect = self.get_object()
        prospect.stage = "converted"
        prospect.converted_at = timezone.now()
        prospect.converted_to_candidate_id = request.data.get("candidate_id")
        prospect.converted_to_application_id = request.data.get("application_id")
        prospect.save(update_fields=["stage", "converted_at",
                                     "converted_to_candidate_id",
                                     "converted_to_application_id"])
        return Response({"status": "converted"})

    @action(detail=True, methods=["post"])
    def add_to_pool(self, request, pk=None):
        """Add this prospect to a talent pool."""
        prospect = self.get_object()
        pool_id = request.data.get("pool_id")
        try:
            pool = TalentPool.objects.get(pk=pool_id, tenant=request.user.tenant)
        except TalentPool.DoesNotExist:
            return Response({"error": "Pool not found"}, status=404)
        membership, created = PoolMembership.objects.get_or_create(
            pool=pool, prospect=prospect,
            defaults={"added_by": request.user}
        )
        pool.member_count = pool.memberships.filter(status="active").count()
        pool.save(update_fields=["member_count"])
        return Response({"created": created, "membership_id": str(membership.id)})

    @action(detail=True, methods=["post"])
    def dnc(self, request, pk=None):
        """Add prospect to do-not-contact list."""
        prospect = self.get_object()
        dnc, _ = DoNotContact.objects.get_or_create(
            tenant=request.user.tenant,
            prospect=prospect,
            defaults={
                "email": prospect.email,
                "phone": prospect.phone,
                "reason": request.data.get("reason", "opted_out"),
                "notes": request.data.get("notes", ""),
                "added_by": request.user,
            }
        )
        prospect.stage = "do_not_contact"
        prospect.unsubscribed = True
        prospect.unsubscribed_at = timezone.now()
        prospect.save(update_fields=["stage", "unsubscribed", "unsubscribed_at"])
        return Response({"status": "added_to_dnc", "dnc_id": str(dnc.id)})

    @action(detail=True, methods=["get"])
    def similar(self, request, pk=None):
        """Return similar prospect suggestions."""
        prospect = self.get_object()
        suggestions = SimilarProspectSuggestion.objects.filter(
            source_prospect=prospect, is_dismissed=False
        ).select_related("suggested_prospect")[:10]
        return Response(SimilarProspectSuggestionSerializer(suggestions, many=True).data)

    @action(detail=True, methods=["post"])
    def enroll_sequence(self, request, pk=None):
        """Enroll this prospect in a nurture sequence."""
        prospect = self.get_object()
        seq_id = request.data.get("sequence_id")
        try:
            seq = NurtureSequence.objects.get(pk=seq_id, tenant=request.user.tenant)
        except NurtureSequence.DoesNotExist:
            return Response({"error": "Sequence not found"}, status=404)
        enrollment, created = SequenceEnrollment.objects.get_or_create(
            sequence=seq, prospect=prospect,
            defaults={"status": "active"}
        )
        return Response({"created": created, "enrollment_id": str(enrollment.id)})


class TalentPoolViewSet(viewsets.ModelViewSet):
    serializer_class = TalentPoolSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TalentPool.objects.filter(tenant=self.request.user.tenant)

    @action(detail=True, methods=["get"])
    def members(self, request, pk=None):
        """Return paginated members of this pool."""
        pool = self.get_object()
        memberships = pool.memberships.filter(status="active").select_related("prospect")
        serializer = PoolMembershipSerializer(memberships, many=True)
        return Response({"count": memberships.count(), "results": serializer.data})

    @action(detail=True, methods=["get"])
    def health(self, request, pk=None):
        """Return pool health snapshots (last 30)."""
        pool = self.get_object()
        snaps = pool.health_snapshots.order_by("-snapshot_date")[:30]
        return Response(PoolHealthSnapshotSerializer(snaps, many=True).data)

    @action(detail=True, methods=["post"])
    def recalc_health(self, request, pk=None):
        """Recalculate and update pool health score."""
        pool = self.get_object()
        memberships = pool.memberships.filter(status="active")
        total = memberships.count()
        engaged = memberships.filter(prospect__stage__in=["engaged", "ready"]).count()
        converted = memberships.filter(prospect__stage="converted").count()
        health = 0.0
        if total > 0:
            engagement_rate = engaged / total
            conversion_rate = converted / total
            health = min(100.0, (engagement_rate * 60 + conversion_rate * 40) * 100)
        pool.member_count = total
        pool.engaged_count = engaged
        pool.converted_count = converted
        pool.health_score = round(health, 1)
        pool.last_health_calc_at = timezone.now()
        pool.save(update_fields=["member_count", "engaged_count", "converted_count",
                                  "health_score", "last_health_calc_at"])
        # Create snapshot
        from django.utils.timezone import now
        today = now().date()
        PoolHealthSnapshot.objects.update_or_create(
            pool=pool, snapshot_date=today,
            defaults={
                "member_count": total, "engaged_count": engaged,
                "converted_count": converted, "health_score": health,
            }
        )
        return Response({
            "health_score": pool.health_score,
            "member_count": pool.member_count,
            "engaged_count": pool.engaged_count,
            "converted_count": pool.converted_count,
        })


class PoolMembershipViewSet(viewsets.ModelViewSet):
    serializer_class = PoolMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = PoolMembership.objects.filter(pool__tenant=self.request.user.tenant)
        if self.request.query_params.get("pool"):
            qs = qs.filter(pool_id=self.request.query_params["pool"])
        if self.request.query_params.get("prospect"):
            qs = qs.filter(prospect_id=self.request.query_params["prospect"])
        return qs.select_related("prospect")


class FollowUpTaskViewSet(viewsets.ModelViewSet):
    serializer_class = FollowUpTaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = FollowUpTask.objects.filter(tenant=self.request.user.tenant)
        params = self.request.query_params
        if params.get("prospect"):
            qs = qs.filter(prospect_id=params["prospect"])
        if params.get("assigned_to"):
            qs = qs.filter(assigned_to_id=params["assigned_to"])
        if params.get("status"):
            qs = qs.filter(status=params["status"])
        if params.get("overdue") == "true":
            qs = qs.filter(due_at__lt=timezone.now(), status__in=["pending", "in_progress"])
        return qs.select_related("prospect")

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        task = self.get_object()
        task.status = "completed"
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "completed_at"])
        return Response({"status": "completed"})


class NurtureSequenceViewSet(viewsets.ModelViewSet):
    serializer_class = NurtureSequenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return NurtureSequence.objects.filter(tenant=self.request.user.tenant)

    @action(detail=True, methods=["get"])
    def steps(self, request, pk=None):
        seq = self.get_object()
        return Response(SequenceStepSerializer(seq.steps.all(), many=True).data)

    @action(detail=True, methods=["get"])
    def enrollments(self, request, pk=None):
        seq = self.get_object()
        return Response(SequenceEnrollmentSerializer(
            seq.enrollments.select_related("prospect"), many=True
        ).data)

    @action(detail=True, methods=["post"])
    def bulk_enroll(self, request, pk=None):
        """Enroll all members of a pool in this sequence."""
        seq = self.get_object()
        pool_id = request.data.get("pool_id")
        enrolled = 0
        skipped = 0
        if pool_id:
            memberships = PoolMembership.objects.filter(
                pool_id=pool_id, status="active"
            ).select_related("prospect")
            for m in memberships:
                p = m.prospect
                if p.unsubscribed or p.consent_status not in ("granted",):
                    skipped += 1
                    continue
                _, created = SequenceEnrollment.objects.get_or_create(
                    sequence=seq, prospect=p,
                    defaults={"status": "active"}
                )
                if created:
                    enrolled += 1
                else:
                    skipped += 1
        return Response({"enrolled": enrolled, "skipped": skipped})


class SequenceStepViewSet(viewsets.ModelViewSet):
    serializer_class = SequenceStepSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = SequenceStep.objects.filter(sequence__tenant=self.request.user.tenant)
        if self.request.query_params.get("sequence"):
            qs = qs.filter(sequence_id=self.request.query_params["sequence"])
        return qs


class SequenceEnrollmentViewSet(viewsets.ModelViewSet):
    serializer_class = SequenceEnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = SequenceEnrollment.objects.filter(sequence__tenant=self.request.user.tenant)
        if self.request.query_params.get("sequence"):
            qs = qs.filter(sequence_id=self.request.query_params["sequence"])
        if self.request.query_params.get("prospect"):
            qs = qs.filter(prospect_id=self.request.query_params["prospect"])
        return qs.select_related("prospect")

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        enrollment = self.get_object()
        enrollment.status = "paused"
        enrollment.save(update_fields=["status"])
        return Response({"status": "paused"})

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        enrollment = self.get_object()
        enrollment.status = "active"
        enrollment.save(update_fields=["status"])
        return Response({"status": "active"})

    @action(detail=True, methods=["post"])
    def exit(self, request, pk=None):
        enrollment = self.get_object()
        enrollment.status = "exited"
        enrollment.exited_reason = request.data.get("reason", "manual")
        enrollment.completed_at = timezone.now()
        enrollment.save(update_fields=["status", "exited_reason", "completed_at"])
        return Response({"status": "exited"})


class OutreachCampaignViewSet(viewsets.ModelViewSet):
    serializer_class = OutreachCampaignSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = OutreachCampaign.objects.filter(tenant=self.request.user.tenant)
        if self.request.query_params.get("status"):
            qs = qs.filter(status=self.request.query_params["status"])
        if self.request.query_params.get("channel"):
            qs = qs.filter(channel=self.request.query_params["channel"])
        return qs

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        """Mark campaign as sending / trigger delivery."""
        campaign = self.get_object()
        campaign.status = "sending"
        campaign.sent_at = timezone.now()
        campaign.save(update_fields=["status", "sent_at"])
        return Response({"status": "sending", "sent_at": str(campaign.sent_at)})

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        campaign = self.get_object()
        campaign.status = "paused"
        campaign.save(update_fields=["status"])
        return Response({"status": "paused"})

    @action(detail=True, methods=["get"])
    def performance(self, request, pk=None):
        """Return per-campaign performance stats."""
        campaign = self.get_object()
        return Response({
            "sent": campaign.sent_count,
            "delivered": campaign.delivered_count,
            "opened": campaign.opened_count,
            "clicked": campaign.clicked_count,
            "replied": campaign.replied_count,
            "bounced": campaign.bounced_count,
            "unsubscribed": campaign.unsubscribed_count,
            "converted": campaign.converted_count,
            "open_rate": round(campaign.opened_count / campaign.delivered_count * 100, 1) if campaign.delivered_count else 0,
            "reply_rate": round(campaign.replied_count / campaign.sent_count * 100, 1) if campaign.sent_count else 0,
        })


class OutreachMessageViewSet(viewsets.ModelViewSet):
    serializer_class = OutreachMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = OutreachMessage.objects.filter(tenant=self.request.user.tenant)
        if self.request.query_params.get("prospect"):
            qs = qs.filter(prospect_id=self.request.query_params["prospect"])
        if self.request.query_params.get("campaign"):
            qs = qs.filter(campaign_id=self.request.query_params["campaign"])
        if self.request.query_params.get("status"):
            qs = qs.filter(status=self.request.query_params["status"])
        return qs

    @action(detail=True, methods=["post"])
    def record_reply(self, request, pk=None):
        """Record that the prospect replied."""
        msg = self.get_object()
        msg.status = "replied"
        msg.replied_at = timezone.now()
        msg.reply_body = request.data.get("reply_body", "")
        msg.save(update_fields=["status", "replied_at", "reply_body"])
        # Update prospect last_replied_at
        msg.prospect.last_replied_at = msg.replied_at
        msg.prospect.engagement_score = min(100, msg.prospect.engagement_score + 10)
        msg.prospect.save(update_fields=["last_replied_at", "engagement_score"])
        return Response({"status": "replied"})


class SavedSegmentViewSet(viewsets.ModelViewSet):
    serializer_class = SavedSegmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SavedSegment.objects.filter(tenant=self.request.user.tenant)

    @action(detail=True, methods=["post"])
    def evaluate(self, request, pk=None):
        """Count prospects matching this segment's filters (simple field-match)."""
        segment = self.get_object()
        filters = segment.filters or {}
        qs = Prospect.objects.filter(tenant=request.user.tenant)
        for key, value in filters.items():
            try:
                qs = qs.filter(**{key: value})
            except Exception:
                pass
        count = qs.count()
        segment.prospect_count = count
        segment.last_evaluated_at = timezone.now()
        segment.save(update_fields=["prospect_count", "last_evaluated_at"])
        return Response({"prospect_count": count})


class DoNotContactViewSet(viewsets.ModelViewSet):
    serializer_class = DoNotContactSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = DoNotContact.objects.filter(tenant=self.request.user.tenant)
        if self.request.query_params.get("reason"):
            qs = qs.filter(reason=self.request.query_params["reason"])
        return qs

    @action(detail=False, methods=["post"])
    def check(self, request):
        """Check if an email/phone is on the DNC list."""
        email = request.data.get("email", "")
        phone = request.data.get("phone", "")
        q = Q()
        if email:
            q |= Q(email__iexact=email)
        if phone:
            q |= Q(phone=phone)
        if not q:
            return Response({"is_dnc": False})
        is_dnc = DoNotContact.objects.filter(tenant=request.user.tenant).filter(q).exists()
        return Response({"is_dnc": is_dnc})


class WarmIntroViewSet(viewsets.ModelViewSet):
    serializer_class = WarmIntroSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = WarmIntro.objects.filter(tenant=self.request.user.tenant)
        if self.request.query_params.get("prospect"):
            qs = qs.filter(prospect_id=self.request.query_params["prospect"])
        if self.request.query_params.get("status"):
            qs = qs.filter(status=self.request.query_params["status"])
        return qs.select_related("prospect")

    @action(detail=True, methods=["post"])
    def mark_made(self, request, pk=None):
        intro = self.get_object()
        intro.status = "made"
        intro.made_at = timezone.now()
        intro.save(update_fields=["status", "made_at"])
        return Response({"status": "made"})


class CandidatePreferenceViewSet(viewsets.ModelViewSet):
    serializer_class = CandidatePreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CandidatePreference.objects.filter(
            prospect__tenant=self.request.user.tenant
        )

    @action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny])
    def by_token(self, request):
        """Public endpoint — look up preferences by unsubscribe token."""
        token = request.query_params.get("token")
        if not token:
            return Response({"error": "token required"}, status=400)
        try:
            pref = CandidatePreference.objects.select_related("prospect").get(
                unsubscribe_token=token
            )
        except CandidatePreference.DoesNotExist:
            return Response({"error": "not found"}, status=404)
        return Response(CandidatePreferenceSerializer(pref).data)

    @action(detail=False, methods=["post"], permission_classes=[permissions.AllowAny])
    def unsubscribe(self, request):
        """Public endpoint — unsubscribe via token."""
        token = request.data.get("token")
        if not token:
            return Response({"error": "token required"}, status=400)
        try:
            pref = CandidatePreference.objects.select_related("prospect").get(
                unsubscribe_token=token
            )
        except CandidatePreference.DoesNotExist:
            return Response({"error": "not found"}, status=404)
        pref.prospect.unsubscribed = True
        pref.prospect.unsubscribed_at = timezone.now()
        pref.prospect.save(update_fields=["unsubscribed", "unsubscribed_at"])
        return Response({"status": "unsubscribed"})


class SimilarProspectSuggestionViewSet(viewsets.ModelViewSet):
    serializer_class = SimilarProspectSuggestionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = SimilarProspectSuggestion.objects.filter(
            source_prospect__tenant=self.request.user.tenant
        )
        if self.request.query_params.get("source"):
            qs = qs.filter(source_prospect_id=self.request.query_params["source"])
        if self.request.query_params.get("dismissed") == "false":
            qs = qs.filter(is_dismissed=False)
        return qs.select_related("suggested_prospect")

    @action(detail=True, methods=["post"])
    def dismiss(self, request, pk=None):
        suggestion = self.get_object()
        suggestion.is_dismissed = True
        suggestion.save(update_fields=["is_dismissed"])
        return Response({"status": "dismissed"})


class OutreachAnalyticsSnapshotViewSet(viewsets.ModelViewSet):
    serializer_class = OutreachAnalyticsSnapshotSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = OutreachAnalyticsSnapshot.objects.filter(tenant=self.request.user.tenant)
        if self.request.query_params.get("channel"):
            qs = qs.filter(channel=self.request.query_params["channel"])
        if self.request.query_params.get("source"):
            qs = qs.filter(source=self.request.query_params["source"])
        return qs

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Aggregated outreach analytics summary."""
        qs = self.get_queryset()
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        if date_from:
            qs = qs.filter(snapshot_date__gte=date_from)
        if date_to:
            qs = qs.filter(snapshot_date__lte=date_to)

        totals = qs.aggregate(
            total_sent=models_sum("sent"),
            total_delivered=models_sum("delivered"),
            total_opened=models_sum("opened"),
            total_replied=models_sum("replied"),
            total_bounced=models_sum("bounced"),
            total_converted=models_sum("prospects_converted"),
            total_contacted=models_sum("prospects_contacted"),
        )

        # By channel breakdown
        by_channel = list(
            qs.values("channel").annotate(
                sent=models_sum("sent"),
                replied=models_sum("replied"),
                converted=models_sum("prospects_converted"),
            ).order_by("-sent")
        )

        # By source breakdown
        by_source = list(
            qs.values("source").annotate(
                contacted=models_sum("prospects_contacted"),
                converted=models_sum("prospects_converted"),
            ).order_by("-contacted")
        )

        sent = totals["total_sent"] or 0
        replied = totals["total_replied"] or 0
        converted = totals["total_converted"] or 0
        contacted = totals["total_contacted"] or 0

        return Response({
            "total_sent": sent,
            "total_delivered": totals["total_delivered"] or 0,
            "total_opened": totals["total_opened"] or 0,
            "total_replied": replied,
            "total_bounced": totals["total_bounced"] or 0,
            "total_converted": converted,
            "reply_rate": round(replied / sent * 100, 1) if sent else 0,
            "conversion_rate": round(converted / replied * 100, 1) if replied else 0,
            "source_conversion_rate": round(converted / contacted * 100, 1) if contacted else 0,
            "by_channel": by_channel,
            "by_source": by_source,
        })


# Import Sum here to avoid circular issues
from django.db.models import Sum as models_sum


# ── Router ────────────────────────────────────────────────────────────────────

router = DefaultRouter()
router.register("prospects", ProspectViewSet, basename="prospect")
router.register("pools", TalentPoolViewSet, basename="talent-pool")
router.register("memberships", PoolMembershipViewSet, basename="pool-membership")
router.register("tasks", FollowUpTaskViewSet, basename="follow-up-task")
router.register("sequences", NurtureSequenceViewSet, basename="nurture-sequence")
router.register("sequence-steps", SequenceStepViewSet, basename="sequence-step")
router.register("enrollments", SequenceEnrollmentViewSet, basename="sequence-enrollment")
router.register("campaigns", OutreachCampaignViewSet, basename="outreach-campaign")
router.register("messages", OutreachMessageViewSet, basename="outreach-message")
router.register("segments", SavedSegmentViewSet, basename="saved-segment")
router.register("dnc", DoNotContactViewSet, basename="do-not-contact")
router.register("warm-intros", WarmIntroViewSet, basename="warm-intro")
router.register("preferences", CandidatePreferenceViewSet, basename="candidate-preference")
router.register("suggestions", SimilarProspectSuggestionViewSet, basename="similar-suggestion")
router.register("analytics", OutreachAnalyticsSnapshotViewSet, basename="outreach-analytics")

urlpatterns = router.urls
