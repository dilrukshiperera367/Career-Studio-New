"""
Candidate Deduplication Service.

Three-tier dedup: exact identity → fuzzy name/company/linkedin → flag/create.
Uses Jaro-Winkler similarity from jellyfish library.
"""

import logging
from typing import Optional

from django.conf import settings
from apps.candidates.models import Candidate, CandidateIdentity, MergeAudit

logger = logging.getLogger(__name__)


def resolve_candidate(
    tenant_id: str,
    full_name: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    linkedin: Optional[str] = None,
    company: Optional[str] = None,
) -> dict:
    """
    Resolve incoming candidate against existing records.

    Returns:
        {
            "candidate_id": uuid or None,
            "action": "existing" | "auto_linked" | "flagged" | "created",
            "confidence": float,
            "match_details": {...},
        }
    """
    auto_threshold = getattr(settings, "CANDIDATE_DEDUP_AUTO_THRESHOLD", 0.92)
    flag_threshold = getattr(settings, "CANDIDATE_DEDUP_FLAG_THRESHOLD", 0.85)

    # Tier 1: Exact email match
    if email:
        try:
            identity = CandidateIdentity.objects.get(
                tenant_id=tenant_id,
                identity_type="email",
                identity_value=email.lower().strip(),
            )
            return {
                "candidate_id": identity.candidate_id,
                "action": "existing",
                "confidence": 1.0,
                "match_details": {"method": "exact_email", "value": email},
            }
        except CandidateIdentity.DoesNotExist:
            pass

    # Tier 1: Exact phone match
    if phone:
        import re
        cleaned_phone = re.sub(r"[^\d+]", "", phone)
        try:
            identity = CandidateIdentity.objects.get(
                tenant_id=tenant_id,
                identity_type="phone",
                identity_value=cleaned_phone,
            )
            return {
                "candidate_id": identity.candidate_id,
                "action": "existing",
                "confidence": 1.0,
                "match_details": {"method": "exact_phone", "value": phone},
            }
        except CandidateIdentity.DoesNotExist:
            pass

    # Tier 2: Fuzzy matching
    candidates = Candidate.objects.filter(
        tenant_id=tenant_id,
        status="active",
    ).values("id", "full_name", "most_recent_company", "linkedin_url")[:500]

    best_match = None
    best_score = 0.0
    best_details = {}

    try:
        import jellyfish
    except ImportError:
        logger.error("jellyfish not installed — skipping fuzzy dedup")
        return _create_new_candidate_result()

    for cand in candidates:
        # Weighted: 0.65*name + 0.25*company + 0.10*linkedin
        name_sim = jellyfish.jaro_winkler_similarity(
            full_name.lower(), cand["full_name"].lower()
        )

        company_sim = 0.0
        if company and cand.get("most_recent_company"):
            company_sim = jellyfish.jaro_winkler_similarity(
                company.lower(), cand["most_recent_company"].lower()
            )

        linkedin_sim = 0.0
        if linkedin and cand.get("linkedin_url"):
            linkedin_norm = linkedin.lower().rstrip("/")
            cand_linkedin = cand["linkedin_url"].lower().rstrip("/")
            linkedin_sim = 1.0 if linkedin_norm == cand_linkedin else 0.0

        weighted_score = 0.65 * name_sim + 0.25 * company_sim + 0.10 * linkedin_sim

        if weighted_score > best_score:
            best_score = weighted_score
            best_match = cand
            best_details = {
                "name_similarity": round(name_sim, 3),
                "company_similarity": round(company_sim, 3),
                "linkedin_similarity": round(linkedin_sim, 3),
                "weighted_score": round(weighted_score, 3),
            }

    # Decision
    if best_match and best_score >= auto_threshold:
        return {
            "candidate_id": best_match["id"],
            "action": "auto_linked",
            "confidence": best_score,
            "match_details": {"method": "fuzzy", **best_details},
        }
    elif best_match and best_score >= flag_threshold:
        return {
            "candidate_id": best_match["id"],
            "action": "flagged",
            "confidence": best_score,
            "match_details": {"method": "fuzzy_flagged", **best_details},
        }
    else:
        return _create_new_candidate_result()


def _create_new_candidate_result() -> dict:
    return {
        "candidate_id": None,
        "action": "created",
        "confidence": 0.0,
        "match_details": {"method": "no_match"},
    }


def merge_candidates(
    tenant_id: str,
    from_candidate_id: str,
    to_candidate_id: str,
    actor_id: Optional[str] = None,
    reason: str = "auto_dedup",
) -> bool:
    """
    Merge 'from' candidate into 'to' candidate.
    Tombstone pattern: from_candidate.status = MERGED, redirect_to = to_candidate.
    """
    try:
        from_cand = Candidate.objects.get(id=from_candidate_id, tenant_id=tenant_id)
        to_cand = Candidate.objects.get(id=to_candidate_id, tenant_id=tenant_id)

        # Move identities
        CandidateIdentity.objects.filter(
            candidate=from_cand, tenant_id=tenant_id
        ).update(candidate=to_cand)

        # Move applications
        from apps.applications.models import Application
        Application.objects.filter(
            candidate=from_cand, tenant_id=tenant_id
        ).update(candidate=to_cand)

        # Tombstone the source
        from_cand.status = "merged"
        from_cand.redirect_to = to_cand
        from_cand.save()

        # Audit trail
        MergeAudit.objects.create(
            tenant_id=tenant_id,
            from_candidate=from_cand,
            to_candidate=to_cand,
            actor_id=actor_id,
            reason=reason,
            details={
                "identities_moved": True,
                "applications_moved": True,
            },
        )

        logger.info(f"Merged candidate {from_candidate_id} → {to_candidate_id}")
        return True

    except Candidate.DoesNotExist:
        logger.error(f"Candidate not found for merge: {from_candidate_id} or {to_candidate_id}")
        return False
