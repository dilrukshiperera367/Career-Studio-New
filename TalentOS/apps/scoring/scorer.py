"""
ATS Scorer — Deterministic, explainable 0-100 scoring algorithm.

Architecture (from spec):
  6 features (0→1) combined proportionally:
    A) Skill match:     45%  (weighted required/preferred coverage)
    B) Title match:     20%  (token overlap against JD target title)
    C) Domain match:    15%  (JD domain keywords present in CV text)
    D) Experience fit:  10%  (years within JD range)
    E) Recency:         10%  (exponential decay of skill freshness)

  Format/readability: applied as penalty (-15) / bonus (+5) on top.
  Must-have cap: missing must-haves → score capped at 35.
  Knockout rules: eligibility flags → mark as not eligible.

No AI APIs. Fully deterministic and explainable.
"""

import re
import math
from typing import Optional


# ---------------------------------------------------------------------------
# Scoring weights (proportional, must sum to 1.0)
# ---------------------------------------------------------------------------

W_SKILL   = 0.45
W_TITLE   = 0.20
W_DOMAIN  = 0.15
W_EXP     = 0.10
W_RECENCY = 0.10

# Format bonus/penalty range
FORMAT_MAX_BONUS   = 5    # max +5 points for excellent format
FORMAT_MAX_PENALTY = 15   # max -15 points for terrible format

# Must-have cap
CAP_IF_MUST_HAVE_MISSING = 35

# Recency exponential decay constant (higher = faster decay)
RECENCY_K = 0.35

# Normalization helper
RE_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _norm(s: str) -> str:
    s = s.lower().strip()
    s = RE_NON_ALNUM.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def _tokenize(s: str) -> set:
    return {t for t in _norm(s).split(" ") if t}


STOPWORDS = {"the", "a", "an", "and", "or", "of", "in", "at", "to", "for", "with", "is", "are"}


# ===========================================================================
# Main entry point
# ===========================================================================

def compute_score(
    cv_parsed: dict,
    jd_requirements: dict,
    file_type: str = "pdf",
    raw_text: str = "",
    weights: Optional[dict] = None,
    jd_target_title: str = "",
    must_have_overrides: Optional[set] = None,
    eligibility: Optional[dict] = None,
) -> dict:
    """
    Compute ATS score for a parsed CV against JD requirements.

    Args:
        cv_parsed: Output from parsing.services.parse_resume_full()
                   Contains: skills, experiences, derived, identities, sections
        jd_requirements: Output from jd_parser.parse_jd()
                   Contains: required_skills (dict), preferred_skills (dict),
                             keywords, target_titles, must_have, min/max_years
        file_type: "pdf" or "docx"
        raw_text: Raw extracted text (for format checks + keyword matching)
        weights: Optional custom feature weights
        jd_target_title: Job title for title matching
        must_have_overrides: Additional must-have skill_ids
        eligibility: Optional {"work_auth_ok": bool, "location_ok": bool}

    Returns:
        {
            "score_total": int (0-100),
            "content_score": float,     # = skill_match (backward compat)
            "title_score": float,
            "experience_score": float,
            "recency_score": float,
            "format_score": float,
            "domain_score": float,
            "eligible": bool,
            "breakdown": {
                "skill_match": float,
                "required_coverage": float,
                "preferred_coverage": float,
                "title_match": float,
                "domain_match": float,
                "experience_fit": float,
                "recency": float,
                "format": float,
                "base_score_0_100": int,
                "format_adjustment_points": int,
                "matched_required": [...],
                "missing_required": [...],
                "matched_preferred": [...],
                "missing_preferred": [...],
                "matched_required_evidence": {...},
                "reasons": [...],
                "suggestions": [...],
                "format_penalties": [...],
            }
        }
    """
    # -----------------------------------------------------------------------
    # 1. Extract CV signals from parsed data
    # -----------------------------------------------------------------------
    cv_skills = _build_cv_skills_map(cv_parsed)
    derived = cv_parsed.get("derived", {})
    total_years = derived.get("total_experience_years", derived.get("total_years", 0))
    contact = cv_parsed.get("identities", cv_parsed.get("contact", {}))
    sections = cv_parsed.get("sections", {})

    # JD data
    jd_required = jd_requirements.get("required_skills", {})
    jd_preferred = jd_requirements.get("preferred_skills", {})
    jd_keywords = set(jd_requirements.get("keywords", []))
    jd_titles = jd_requirements.get("target_titles", [])
    jd_must_have = set(jd_requirements.get("must_have", []))
    if must_have_overrides:
        jd_must_have |= set(must_have_overrides)

    # If jd_target_title provided, prepend to jd_titles
    if jd_target_title and jd_target_title not in jd_titles:
        jd_titles = [jd_target_title] + jd_titles

    # -----------------------------------------------------------------------
    # 2. Feature A: Skill Match (0→1)
    # -----------------------------------------------------------------------
    req_cov, req_matched, req_missing = _weighted_skill_coverage(jd_required, cv_skills)
    pref_cov, pref_matched, pref_missing = _weighted_skill_coverage(jd_preferred, cv_skills)

    # Blend: 75% required, 25% preferred (spec)
    if jd_required and jd_preferred:
        skill_match = 0.75 * req_cov + 0.25 * pref_cov
    elif jd_required:
        skill_match = req_cov
    elif jd_preferred:
        skill_match = pref_cov
    else:
        skill_match = 1.0  # no skills in JD → don't punish

    # -----------------------------------------------------------------------
    # 3. Feature B: Title Match (0→1)
    # -----------------------------------------------------------------------
    title_match = _title_match_score(jd_titles, derived)

    # -----------------------------------------------------------------------
    # 4. Feature C: Domain/Keyword Match (0→1)
    # -----------------------------------------------------------------------
    domain_match = _domain_match_score(jd_keywords, raw_text)

    # -----------------------------------------------------------------------
    # 5. Feature D: Experience Fit (0→1)
    # -----------------------------------------------------------------------
    min_y = jd_requirements.get("min_years")
    max_y = jd_requirements.get("max_years")
    exp_fit, exp_note = _experience_fit_score(min_y, max_y, total_years)

    # -----------------------------------------------------------------------
    # 6. Feature E: Recency (0→1)
    # -----------------------------------------------------------------------
    recency = _recency_score(jd_required, cv_skills, derived)

    # -----------------------------------------------------------------------
    # 7. Combine into base score (0→100)
    # -----------------------------------------------------------------------
    w_skill = (weights or {}).get("skill", W_SKILL)
    w_title = (weights or {}).get("title", W_TITLE)
    w_domain = (weights or {}).get("domain", W_DOMAIN)
    w_exp = (weights or {}).get("experience", W_EXP)
    w_recency = (weights or {}).get("recency", W_RECENCY)

    base_01 = (
        w_skill * skill_match
        + w_title * title_match
        + w_domain * domain_match
        + w_exp * exp_fit
        + w_recency * recency
    )
    base_0_100 = int(round(100 * max(0.0, min(1.0, base_01))))

    # -----------------------------------------------------------------------
    # 8. Format adjustment (penalty/bonus, NOT a weighted component)
    # -----------------------------------------------------------------------
    fmt_01, fmt_warnings = _format_score(raw_text, file_type, contact, sections)

    if fmt_01 >= 0.85:
        fmt_adj = int(round((fmt_01 - 0.85) / 0.15 * FORMAT_MAX_BONUS))
    else:
        fmt_adj = -int(round((0.85 - fmt_01) / 0.85 * FORMAT_MAX_PENALTY))

    score_0_100 = max(0, min(100, base_0_100 + fmt_adj))

    # -----------------------------------------------------------------------
    # 9. Must-have cap
    # -----------------------------------------------------------------------
    must_have_reasons = []
    if jd_must_have:
        missing_must = [sid for sid in jd_must_have if sid not in cv_skills]
        if missing_must:
            score_0_100 = min(score_0_100, CAP_IF_MUST_HAVE_MISSING)
            # Resolve names
            missing_names = []
            for sid in missing_must:
                name = _resolve_skill_name(sid, jd_requirements)
                missing_names.append(name or sid)
            must_have_reasons.append(
                f"Missing must-have skills: {', '.join(missing_names)} (score capped at {CAP_IF_MUST_HAVE_MISSING})"
            )

    # -----------------------------------------------------------------------
    # 10. Knockout / eligibility checks
    # -----------------------------------------------------------------------
    is_eligible, knockout_reasons = _apply_knockouts(eligibility)

    # -----------------------------------------------------------------------
    # 11. Build explainability payload
    # -----------------------------------------------------------------------
    reasons = []
    reasons.append(f"Required skills coverage: {int(round(100 * req_cov))}%")
    if jd_preferred:
        reasons.append(f"Preferred skills coverage: {int(round(100 * pref_cov))}%")
    if req_missing:
        missing_names = [_resolve_skill_name(sid, jd_requirements) or sid for sid in req_missing[:10]]
        suffix = "..." if len(req_missing) > 10 else ""
        reasons.append(f"Missing required skills: {', '.join(missing_names)}{suffix}")
    if exp_note:
        reasons.append(exp_note)
    reasons.extend(fmt_warnings[:3])
    reasons.extend(must_have_reasons)
    reasons.extend(knockout_reasons)

    # Evidence per matched required skill
    matched_evidence = {}
    for sid in req_matched:
        if sid in cv_skills:
            matched_evidence[sid] = cv_skills[sid].get("evidence_lines", [])[:3]

    # Suggestions
    suggestions = _generate_suggestions(
        req_missing, pref_missing, fmt_warnings, exp_note, jd_requirements
    )

    # -----------------------------------------------------------------------
    # 12. Assemble result
    # -----------------------------------------------------------------------
    return {
        "score_total": score_0_100,
        # Backward-compatible individual scores (0→1)
        "content_score": round(skill_match, 4),
        "title_score": round(title_match, 4),
        "experience_score": round(exp_fit, 4),
        "recency_score": round(recency, 4),
        "format_score": round(fmt_01, 4),
        "domain_score": round(domain_match, 4),
        # Eligibility
        "eligible": is_eligible,
        # Rich breakdown
        "breakdown": {
            # Feature scores
            "skill_match": round(skill_match, 4),
            "required_coverage": round(req_cov, 4),
            "preferred_coverage": round(pref_cov, 4),
            "title_match": round(title_match, 4),
            "domain_match": round(domain_match, 4),
            "experience_fit": round(exp_fit, 4),
            "recency": round(recency, 4),
            "format": round(fmt_01, 4),
            # Score math
            "base_score_0_100": base_0_100,
            "format_adjustment_points": fmt_adj,
            # Skill lists
            "matched_required": [
                {"id": sid, "name": _resolve_skill_name(sid, jd_requirements) or sid}
                for sid in req_matched
            ],
            "missing_required": [
                {"id": sid, "name": _resolve_skill_name(sid, jd_requirements) or sid}
                for sid in req_missing
            ],
            "matched_preferred": [
                {"id": sid, "name": _resolve_skill_name(sid, jd_requirements) or sid}
                for sid in pref_matched
            ],
            "missing_preferred": [
                {"id": sid, "name": _resolve_skill_name(sid, jd_requirements) or sid}
                for sid in pref_missing
            ],
            "matched_required_evidence": matched_evidence,
            # Explanations
            "reasons": reasons,
            "suggestions": suggestions,
            "format_penalties": fmt_warnings,
        },
    }


# ===========================================================================
# CV skills map builder
# ===========================================================================

def _build_cv_skills_map(cv_parsed: dict) -> dict:
    """
    Convert parser's skill list into a dict keyed by skill_id.

    Input (from parser):  list of {"skill_id", "canonical_name", "confidence", "evidence"}
    Output: {skill_id: {"confidence", "evidence_lines", "last_seen_years_ago"}}
    """
    cv_skills = {}
    skills_list = cv_parsed.get("skills", [])

    # Handle nested parsed_json (parse_resume_full returns {raw_text, clean_text, parsed_json})
    if isinstance(skills_list, list) and not skills_list and "parsed_json" in cv_parsed:
        inner = cv_parsed["parsed_json"]
        skills_list = inner.get("skills", [])

    for s in skills_list:
        if isinstance(s, dict):
            sid = str(s.get("skill_id", s.get("id", "")))
            if sid:
                cv_skills[sid] = {
                    "confidence": s.get("confidence", 0.8),
                    "evidence_lines": s.get("evidence", s.get("evidence_lines", [])),
                    "last_seen_years_ago": s.get("last_seen_years_ago"),
                    "name": s.get("canonical_name", s.get("name", "")),
                }

    return cv_skills


# ===========================================================================
# Feature A: Weighted Skill Coverage
# ===========================================================================

def _weighted_skill_coverage(
    jd_skills: dict, cv_skills: dict
) -> tuple:
    """
    Presence-based weighted coverage (anti-stuffing).
    Each skill contributes at most once.

    Args:
        jd_skills: {skill_id: weight} from JD blueprint
        cv_skills: {skill_id: {...}} from CV

    Returns: (coverage_0_1, matched_ids, missing_ids)
    """
    if not jd_skills:
        return (1.0, [], [])

    total_w = sum(jd_skills.values())
    got_w = 0.0
    matched = []
    missing = []

    for sid, w in jd_skills.items():
        if sid in cv_skills:
            conf = cv_skills[sid].get("confidence", 0.8)
            # Confidence gating: >= 0.75 → full credit, else half
            if conf >= 0.75:
                got_w += w
            else:
                got_w += 0.5 * w
            matched.append(sid)
        else:
            missing.append(sid)

    coverage = min(1.0, got_w / (total_w + 1e-9))
    return (coverage, matched, missing)


# ===========================================================================
# Feature B: Title Match
# ===========================================================================

def _title_match_score(jd_titles: list, derived: dict) -> float:
    """
    Token overlap between candidate's recent title and JD target titles.
    Returns best match across all JD titles.
    """
    recent_title = (derived.get("most_recent_title", derived.get("recent_title", "")) or "").strip()
    if not recent_title:
        return 0.5  # neutral if no title found

    if not jd_titles:
        return 0.5  # neutral if no JD title target

    cv_tokens = _tokenize(recent_title) - STOPWORDS
    if not cv_tokens:
        return 0.5

    best = 0.0
    for jd_title in jd_titles:
        jd_tokens = _tokenize(jd_title) - STOPWORDS
        if not jd_tokens:
            continue
        overlap = len(cv_tokens & jd_tokens) / (len(jd_tokens) + 1e-9)
        best = max(best, overlap)

    return max(0.0, min(1.0, best))


# ===========================================================================
# Feature C: Domain / Keyword Match
# ===========================================================================

def _domain_match_score(jd_keywords: set, cv_text: str) -> float:
    """
    Fraction of JD domain keywords present in CV text.
    Neutral (0.5) if no keywords in JD.
    """
    if not jd_keywords:
        return 0.5

    cv_text_lower = (cv_text or "").lower()
    cv_tokens = set(re.findall(r"[a-z0-9/\-]+", cv_text_lower))

    hit = 0
    for kw in jd_keywords:
        if " " in kw:
            # Multi-word: substring match
            if kw in cv_text_lower:
                hit += 1
        else:
            if kw in cv_tokens:
                hit += 1

    return max(0.0, min(1.0, hit / (len(jd_keywords) + 1e-9)))


# ===========================================================================
# Feature D: Experience Fit
# ===========================================================================

def _experience_fit_score(
    min_y: Optional[int], max_y: Optional[int], years: float
) -> tuple:
    """
    Score how well candidate's years fit the JD requirement.
    Returns (score_0_1, explanation_note).
    """
    if years is None:
        years = 0

    if min_y is None and max_y is None:
        return 0.5, "No years requirement in JD"

    if min_y is not None and max_y is not None:
        if min_y <= years <= max_y:
            return 1.0, f"{years:.1f} years fits range [{min_y}-{max_y}]"
        if years < min_y:
            score = max(0.0, min(1.0, years / (min_y + 1e-9)))
            return score, f"{years:.1f} years below minimum {min_y}"
        # years > max_y (overqualified)
        score = max(0.0, min(1.0, max_y / (years + 1e-9)))
        return score, f"{years:.1f} years above maximum {max_y} (overqualified)"

    if min_y is not None:
        if years >= min_y:
            return 1.0, f"{years:.1f} years meets minimum {min_y}"
        score = max(0.0, min(1.0, years / (min_y + 1e-9)))
        return score, f"{years:.1f} years below minimum {min_y}"

    if max_y is not None:
        if years <= max_y:
            return 1.0, f"{years:.1f} years within maximum {max_y}"
        score = max(0.0, min(1.0, max_y / (years + 1e-9)))
        return score, f"{years:.1f} years above maximum {max_y}"

    return 0.5, "Could not determine experience match"


# ===========================================================================
# Feature E: Recency (exponential decay)
# ===========================================================================

def _recency_score(jd_required: dict, cv_skills: dict, derived: dict) -> float:
    """
    Weighted average recency for required skills using exponential decay.
    recency_skill = exp(-k * years_since_last_seen)
    """
    if not jd_required:
        return 0.5

    # Get skill recency from derived (computed by parser)
    skill_recency_map = derived.get("skill_recency", {})

    total_w = sum(jd_required.values())
    acc = 0.0

    for sid, w in jd_required.items():
        if sid not in cv_skills:
            continue  # missing skills contribute 0

        # Check if parser computed recency for this skill
        if sid in skill_recency_map:
            # Already computed as exp decay by parser
            acc += w * skill_recency_map[sid]
        else:
            # Estimate from last_seen_years_ago field
            years_since = cv_skills[sid].get("last_seen_years_ago")
            if years_since is None:
                years_since = 5.0  # assume older if unknown
            acc += w * math.exp(-RECENCY_K * max(0.0, years_since))

    return max(0.0, min(1.0, acc / (total_w + 1e-9)))


# ===========================================================================
# Format Score (penalty/bonus system)
# ===========================================================================

def _format_score(
    raw_text: str, file_type: str, contact: dict, sections: dict
) -> tuple:
    """
    Deterministic ATS readability score (0→1) + warning list.
    This is NOT a weighted component — it's converted to penalty/bonus points.
    """
    score = 1.0
    warnings = []

    # File type check
    if file_type not in ("pdf", "docx"):
        score -= 0.25
        warnings.append("Unsupported file format (use PDF or DOCX)")

    # Text extractable?
    text_chars = len((raw_text or "").strip())
    if text_chars < 50:
        score -= 0.35
        warnings.append("Very little text extracted — may be scanned image")
    elif text_chars < 300:
        score -= 0.20
        warnings.append("Low extractable text (may be scanned or image-heavy)")

    # Contact info present
    has_email = bool(contact.get("emails") or contact.get("email"))
    has_phone = bool(contact.get("phones") or contact.get("phone"))
    if not has_email and not has_phone:
        score -= 0.15
        warnings.append("No contact information (email/phone) detected")
    elif not has_email:
        score -= 0.05
        warnings.append("No email address found")

    # Standard headings (Experience / Education / Skills)
    expected = {"experience", "education", "skills"}
    found = set()
    if sections:
        found = {s.lower() for s in sections.keys()}
    missing_sections = expected - found
    if missing_sections:
        penalty = len(missing_sections) * 0.08
        score -= penalty
        warnings.append(f"Missing standard sections: {', '.join(sorted(missing_sections))}")

    # Text density (indication of tables / images)
    if raw_text:
        lines = raw_text.split("\n")
        non_empty = [ln for ln in lines if ln.strip()]
        if non_empty:
            avg_len = sum(len(ln) for ln in non_empty) / len(non_empty)
            if avg_len < 15:
                score -= 0.10
                warnings.append("Low text density — may have formatting issues")

    # Length checks
    word_count = len((raw_text or "").split())
    if word_count < 100:
        score -= 0.15
        warnings.append("Resume appears very short")
    elif word_count > 3000:
        score -= 0.05
        warnings.append("Resume is very long — consider condensing")

    return (max(0.0, min(1.0, score)), warnings)


# ===========================================================================
# Knockout / Eligibility
# ===========================================================================

def _apply_knockouts(eligibility: Optional[dict]) -> tuple:
    """
    Check eligibility flags. Returns (is_eligible, reasons).
    """
    if not eligibility:
        return True, []

    reasons = []
    for key, value in eligibility.items():
        if value is False:
            label = key.replace("_", " ").title()
            reasons.append(f"Knockout: {label} — not eligible")

    return (len(reasons) == 0), reasons


# ===========================================================================
# Skill name resolver
# ===========================================================================

def _resolve_skill_name(skill_id: str, jd_requirements: dict) -> str:
    """Look up skill name from JD requirement lists."""
    # Check list forms first (have name field)
    for item in jd_requirements.get("required_skills_list", []):
        if item.get("id") == skill_id:
            return item.get("name", "")
    for item in jd_requirements.get("preferred_skills_list", []):
        if item.get("id") == skill_id:
            return item.get("name", "")
    return skill_id


# ===========================================================================
# Suggestions generator
# ===========================================================================

def _generate_suggestions(
    req_missing: list,
    pref_missing: list,
    fmt_warnings: list,
    exp_note: str,
    jd_requirements: dict,
) -> list:
    """Generate actionable, prioritized improvement suggestions."""
    suggestions = []

    # Missing required skills (high priority)
    if req_missing:
        names = [_resolve_skill_name(sid, jd_requirements) for sid in req_missing[:5]]
        suggestions.append({
            "type": "skills",
            "priority": "high",
            "message": f"Add these missing required skills to your resume: {', '.join(names)}",
        })

    # Missing preferred skills (medium priority)
    if pref_missing:
        names = [_resolve_skill_name(sid, jd_requirements) for sid in pref_missing[:3]]
        suggestions.append({
            "type": "skills",
            "priority": "medium",
            "message": f"Consider adding preferred skills: {', '.join(names)}",
        })

    # Format issues
    for warning in fmt_warnings[:3]:
        suggestions.append({
            "type": "format",
            "priority": "medium",
            "message": warning,
        })

    # Experience gap
    if exp_note and "below" in exp_note:
        suggestions.append({
            "type": "experience",
            "priority": "high",
            "message": "Your experience is below the job's requirement. Highlight relevant projects, freelance work, or certifications.",
        })
    elif exp_note and "above" in exp_note:
        suggestions.append({
            "type": "experience",
            "priority": "low",
            "message": "You may be overqualified. Consider emphasizing leadership and mentoring experience.",
        })

    return suggestions
