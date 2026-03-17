"""
Ranking Engine — Structured scoring + BM25 normalization + explainability.

Implements the scoring formulas from 00b-algorithm-spec.md:
- Weighted Jaccard skill_match
- Title match (exact/partial)
- Experience fit (within-range / below / above)
- Recency decay: exp(-0.35 * years_since)
- Domain match
- BM25 text normalization
- Hybrid and structured-only composite scores
"""

import math
import logging
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Component scoring functions
# ---------------------------------------------------------------------------

def skill_match(candidate_skills: set, job_required: set, job_optional: set) -> float:
    """
    Weighted Jaccard: required skills count 2x, optional 1x.

    candidate_skills: set of skill_id strings
    job_required: set of skill_id strings
    job_optional: set of skill_id strings
    """
    if not job_required and not job_optional:
        return 0.5  # no requirements → neutral

    weighted_intersection = 0.0
    weighted_union = 0.0

    for sid in job_required:
        weight = 2.0
        weighted_union += weight
        if sid in candidate_skills:
            weighted_intersection += weight

    for sid in job_optional:
        weight = 1.0
        weighted_union += weight
        if sid in candidate_skills:
            weighted_intersection += weight

    if weighted_union == 0:
        return 0.5

    return weighted_intersection / weighted_union


def title_match(candidate_title: str, target_titles: list) -> float:
    """
    Exact canonical match → 1.0, substring → 0.5, else 0.0.
    """
    if not target_titles or not candidate_title:
        return 0.0

    candidate_lower = candidate_title.lower().strip()

    for title in target_titles:
        title_lower = title.lower().strip()
        if candidate_lower == title_lower:
            return 1.0

    # Substring check
    for title in target_titles:
        title_lower = title.lower().strip()
        if title_lower in candidate_lower or candidate_lower in title_lower:
            return 0.5

    return 0.0


def experience_fit(total_years: Optional[float], min_years: Optional[float], max_years: Optional[float]) -> float:
    """
    1.0 if within [min, max], penalty for below/above.

    Within range → 1.0
    Below min → max(0, 1 - (min - total)/min)
    Above max → max(0.5, 1 - (total - max)/(max * 2))
    """
    if total_years is None:
        return 0.5  # unknown experience → neutral

    if min_years is not None and max_years is not None:
        if min_years <= total_years <= max_years:
            return 1.0
        elif total_years < min_years:
            if min_years == 0:
                return 1.0
            return max(0.0, 1.0 - (min_years - total_years) / min_years)
        else:  # above max
            return max(0.5, 1.0 - (total_years - max_years) / (max_years * 2))
    elif min_years is not None:
        return 1.0 if total_years >= min_years else max(0.0, 1.0 - (min_years - total_years) / max(min_years, 1))
    elif max_years is not None:
        return 1.0 if total_years <= max_years else max(0.5, 1.0 - (total_years - max_years) / (max_years * 2))
    return 1.0  # no requirements → perfect


def recency_score(score_value: Optional[float]) -> float:
    """Already computed during parsing. Just pass through."""
    if score_value is None:
        return 0.5
    return max(0.0, min(1.0, score_value))


def domain_match(candidate_tags: list, job_domains: list) -> float:
    """Jaccard similarity between candidate tags and job domain tags."""
    if not job_domains:
        return 0.5
    if not candidate_tags:
        return 0.0

    candidate_set = set(t.lower() for t in candidate_tags)
    job_set = set(d.lower() for d in job_domains)
    intersection = candidate_set & job_set
    union = candidate_set | job_set

    return len(intersection) / len(union) if union else 0.0


def normalize_bm25(raw_score: float, min_score: float, max_score: float) -> float:
    """Normalize BM25 score to [0, 1] using min-max: (x - min) / (max - min + 1e-9)."""
    return (raw_score - min_score) / (max_score - min_score + 1e-9)


# ---------------------------------------------------------------------------
# Composite scoring
# ---------------------------------------------------------------------------

def compute_structured_score(
    candidate_skills: set,
    job_required: set,
    job_optional: set,
    candidate_title: str,
    target_titles: list,
    total_years: Optional[float],
    min_years: Optional[float],
    max_years: Optional[float],
    candidate_recency: Optional[float],
    candidate_tags: list,
    job_domains: list,
) -> dict:
    """
    Compute structured-only score.
    Weights: 0.45*skill + 0.20*title + 0.15*domain + 0.10*experience + 0.10*recency
    """
    weights = settings.RANKING_WEIGHTS.get("structured", {
        "skill_match": 0.45,
        "title_match": 0.20,
        "domain_match": 0.15,
        "experience_fit": 0.10,
        "recency": 0.10,
    })

    components = {
        "skill_match": skill_match(candidate_skills, job_required, job_optional),
        "title_match": title_match(candidate_title, target_titles),
        "domain_match": domain_match(candidate_tags, job_domains),
        "experience_fit": experience_fit(total_years, min_years, max_years),
        "recency": recency_score(candidate_recency),
    }

    total = sum(components[k] * weights.get(k, 0) for k in components)

    return {
        "score": round(total, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


def compute_hybrid_score(
    structured_components: dict,
    bm25_normalized: float,
) -> dict:
    """
    Compute hybrid score: 0.55*text_norm + 0.30*skill + 0.10*title + 0.05*recency
    """
    weights = settings.RANKING_WEIGHTS.get("hybrid", {
        "text_norm": 0.55,
        "skill_match": 0.30,
        "title_match": 0.10,
        "recency": 0.05,
    })

    components = {
        "text_norm": bm25_normalized,
        "skill_match": structured_components.get("skill_match", 0),
        "title_match": structured_components.get("title_match", 0),
        "recency": structured_components.get("recency", 0),
    }

    total = sum(components[k] * weights.get(k, 0) for k in components)

    return {
        "score": round(total, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
    }


# ---------------------------------------------------------------------------
# Explainability
# ---------------------------------------------------------------------------

def build_explanation(
    structured_result: dict,
    hybrid_result: Optional[dict] = None,
    candidate_skills: set = None,
    job_required: set = None,
    job_optional: set = None,
) -> dict:
    """
    Build human-readable explanation of the ranking.
    Returns score breakdown + reasons array.
    """
    reasons = []
    components = structured_result.get("components", {})

    # Skill match explanation
    sm = components.get("skill_match", 0)
    if sm >= 0.8:
        reasons.append(f"Strong skill match ({sm:.0%} of required/optional skills)")
    elif sm >= 0.5:
        reasons.append(f"Partial skill match ({sm:.0%} of required/optional skills)")
    elif sm > 0:
        reasons.append(f"Low skill match ({sm:.0%} of required/optional skills)")

    if candidate_skills and job_required:
        matched = candidate_skills & job_required
        missing = job_required - candidate_skills
        if matched:
            reasons.append(f"Has required skills: matched {len(matched)} of {len(job_required)}")
        if missing:
            reasons.append(f"Missing {len(missing)} required skill(s)")

    # Title match
    tm = components.get("title_match", 0)
    if tm == 1.0:
        reasons.append("Exact title match")
    elif tm == 0.5:
        reasons.append("Partial title match")
    elif tm == 0:
        reasons.append("No title match")

    # Experience fit
    ef = components.get("experience_fit", 0)
    if ef == 1.0:
        reasons.append("Experience within target range")
    elif ef >= 0.7:
        reasons.append("Experience close to target range")
    elif ef < 0.5:
        reasons.append("Experience outside target range")

    # Recency
    rec = components.get("recency", 0)
    if rec >= 0.8:
        reasons.append("Skills were recently used")
    elif rec >= 0.5:
        reasons.append("Some skills may be dated")
    elif rec < 0.5:
        reasons.append("Skills appear dated")

    return {
        "structured_score": structured_result.get("score"),
        "hybrid_score": hybrid_result.get("score") if hybrid_result else None,
        "breakdown": structured_result.get("components", {}),
        "weights": structured_result.get("weights", {}),
        "reasons": reasons,
    }


# ---------------------------------------------------------------------------
# Full ranking pipeline
# ---------------------------------------------------------------------------

def rank_candidates(candidates_data: list, job_data: dict, search_scores: Optional[dict] = None) -> list:
    """
    Rank a list of candidates against a job.

    candidates_data: list of dicts with candidate info
    job_data: dict with job requirements
    search_scores: optional dict of candidate_id → bm25_score from OpenSearch

    Returns ranked list with scores and explanations.
    """
    job_required = set(s["skill_id"] for s in job_data.get("required_skills", []))
    job_optional = set(s["skill_id"] for s in job_data.get("optional_skills", []))
    target_titles = job_data.get("target_titles", [])
    min_years = job_data.get("min_years_experience")
    max_years = job_data.get("max_years_experience")
    job_domains = job_data.get("domain_tags", [])

    # BM25 normalization
    bm25_min = bm25_max = 0.0
    if search_scores:
        scores = list(search_scores.values())
        if scores:
            bm25_min = min(scores)
            bm25_max = max(scores)

    scored = []
    for cand in candidates_data:
        cand_skills = set(cand.get("skill_ids", []))
        cand_title = cand.get("most_recent_title", "")
        cand_years = cand.get("total_experience_years")
        cand_recency = cand.get("recency_score")
        cand_tags = cand.get("tags", [])
        cand_id = cand.get("candidate_id")

        structured = compute_structured_score(
            candidate_skills=cand_skills,
            job_required=job_required,
            job_optional=job_optional,
            candidate_title=cand_title,
            target_titles=target_titles,
            total_years=cand_years,
            min_years=min_years,
            max_years=max_years,
            candidate_recency=cand_recency,
            candidate_tags=cand_tags,
            job_domains=job_domains,
        )

        # Hybrid if BM25 available
        hybrid = None
        if search_scores and cand_id in search_scores:
            bm25_norm = normalize_bm25(search_scores[cand_id], bm25_min, bm25_max)
            hybrid = compute_hybrid_score(structured["components"], bm25_norm)

        final_score = hybrid["score"] if hybrid else structured["score"]

        explanation = build_explanation(
            structured, hybrid,
            candidate_skills=cand_skills,
            job_required=job_required,
            job_optional=job_optional,
        )

        scored.append({
            "candidate_id": cand_id,
            "score": final_score,
            "score_breakdown": explanation,
            **cand,
        })

    # Sort by score descending
    scored.sort(key=lambda x: x["score"], reverse=True)

    return scored
