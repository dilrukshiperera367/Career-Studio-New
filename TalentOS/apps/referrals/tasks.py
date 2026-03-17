"""Celery tasks for Referrals."""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="apps.referrals.tasks.end_expired_referral_campaigns")
def end_expired_referral_campaigns():
    """
    Daily task: close referral campaigns whose end_date has passed.
    """
    from apps.referrals.models import ReferralCampaign

    today = timezone.now().date()
    updated = ReferralCampaign.objects.filter(
        status="active",
        end_date__lt=today,
    ).update(status="ended")

    logger.info("end_expired_referral_campaigns: %d campaigns ended", updated)
    return {"ended": updated}


@shared_task(name="apps.referrals.tasks.compute_referral_leaderboards")
def compute_referral_leaderboards():
    """
    Weekly task: recompute monthly and all-time leaderboard snapshots for each
    active referral program.
    """
    from django.db.models import Count
    from apps.referrals.models import ReferralProgram, Referral, ReferralLeaderboard

    today = timezone.now().date()
    month_start = today.replace(day=1)
    computed = 0

    for program in ReferralProgram.objects.filter(is_active=True):
        for period, start in [("month", month_start), ("all_time", None)]:
            qs = Referral.objects.filter(
                program=program,
                status__in=["hired", "pending_payout", "paid"],
            )
            if start:
                qs = qs.filter(submitted_at__date__gte=start)

            rankings_raw = (
                qs.values("referrer_id", "referrer__email")
                .annotate(total=Count("id"))
                .order_by("-total")[:50]
            )

            rankings = []
            for i, row in enumerate(rankings_raw, start=1):
                rankings.append({
                    "rank": i,
                    "user_id": str(row["referrer_id"]) if row["referrer_id"] else None,
                    "email": row.get("referrer__email", ""),
                    "referrals": row["total"],
                })

            ReferralLeaderboard.objects.update_or_create(
                tenant=program.tenant,
                program=program,
                period=period,
                period_start=start or today.replace(month=1, day=1),
                defaults={"rankings": rankings},
            )
            computed += 1

    logger.info("compute_referral_leaderboards: %d leaderboards computed", computed)
    return {"computed": computed}


@shared_task(name="apps.referrals.tasks.trigger_bonus_payouts_on_hire")
def trigger_bonus_payouts_on_hire():
    """
    Daily task: for referrals that just became 'hired' with no payout yet,
    create BonusPayout records per matching BonusRules.
    """
    from apps.referrals.models import Referral, BonusRule, BonusPayout

    hired_no_payout = Referral.objects.filter(
        status="hired",
    ).exclude(payouts__isnull=False)

    created = 0
    for referral in hired_no_payout:
        rules = BonusRule.objects.filter(
            program=referral.program,
            is_active=True,
            trigger_event="hired",
        )
        for rule in rules:
            if rule.department_filter and referral.job:
                if referral.job.department != rule.department_filter:
                    continue
            BonusPayout.objects.create(
                tenant=referral.tenant,
                referral=referral,
                rule=rule,
                recipient=referral.referrer,
                recipient_email=referral.referrer_email,
                amount=rule.amount,
                currency=rule.currency,
                status="pending",
            )
            created += 1

        # Move referral to pending_payout
        referral.status = "pending_payout"
        referral.save(update_fields=["status", "updated_at"])

    logger.info("trigger_bonus_payouts_on_hire: %d payout records created", created)
    return {"payouts_created": created}
