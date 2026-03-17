"""
JD Parser — Deterministic extraction of requirements from job descriptions.

No AI APIs. Uses:
  - Skill taxonomy dictionary matching (n-grams)
  - Per-line intent detection (required vs preferred vs neutral)
  - Weighted skill extraction (required=3.0, preferred=1.5, neutral→preferred=1.0)
  - Regex for years/experience extraction
  - Keyword dictionaries for location, education, certifications, work mode
  - Domain keyword matching (SaaS, B2B, fintech, etc.)
  - Target title extraction from JD text
"""

import re
from typing import Optional


# ---------------------------------------------------------------------------
# Intent detection indicators
# ---------------------------------------------------------------------------

REQUIRED_INDICATORS = [
    "must", "required", "essential", "mandatory", "necessary",
    "need to", "needs to", "require", "requires", "critical",
    "must-have", "must have", "key requirement", "prerequisite",
    "you will have", "minimum",
]

PREFERRED_INDICATORS = [
    "nice to have", "nice-to-have", "bonus", "plus", "a plus",
    "preferred", "desirable", "advantageous", "ideally", "optional",
    "good to have", "would be nice", "beneficial", "advantage",
]

# ---------------------------------------------------------------------------
# Years extraction patterns
# ---------------------------------------------------------------------------

YEARS_RANGE_RE = re.compile(
    r"(\d{1,2})\s*[-–to]+\s*(\d{1,2})\s*\+?\s*(?:years?|yrs?)\b",
    re.IGNORECASE,
)

YEARS_MIN_RE = re.compile(
    r"(\d{1,2})\s*\+?\s*(?:years?|yrs?)\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Education / certification keywords
# ---------------------------------------------------------------------------

EDUCATION_KEYWORDS = {
    "bachelor", "bachelors", "bachelor's", "bs", "ba", "b.s.", "b.a.",
    "master", "masters", "master's", "ms", "ma", "m.s.", "m.a.", "mba",
    "phd", "ph.d.", "doctorate", "doctoral",
    "degree", "diploma", "associate", "certification", "certified",
}

CERTIFICATION_KEYWORDS = {
    "pmp", "aws certified", "azure certified", "google certified",
    "cpa", "cfa", "cissp", "ccna", "scrum master", "csm",
    "six sigma", "itil", "comptia", "prince2",
}

# ---------------------------------------------------------------------------
# Work mode keywords
# ---------------------------------------------------------------------------

WORK_MODE_KEYWORDS = {
    "remote": ["remote", "work from home", "wfh", "fully remote", "100% remote"],
    "hybrid": ["hybrid", "flexible", "partially remote"],
    "onsite": ["onsite", "on-site", "in-office", "in office", "office-based"],
}

# ---------------------------------------------------------------------------
# Domain keywords (for Feature D: domain/keyword match)
# These are non-skill terms that help distinguish domain fit.
# ---------------------------------------------------------------------------

DOMAIN_KEYWORDS = {
    "saas", "b2b", "b2c", "fintech", "healthtech", "edtech", "martech",
    "adtech", "ecommerce", "e-commerce", "marketplace", "startup",
    "enterprise", "smb", "api", "microservices", "devops", "mlops",
    "data pipeline", "etl", "real-time", "streaming", "distributed",
    "cloud-native", "serverless", "ci/cd", "agile", "scrum", "kanban",
    "product-led", "growth", "seo", "sem", "ppc", "crm", "erp",
    "hubspot", "salesforce", "jira", "confluence", "notion",
    "figma", "sketch", "adobe", "photoshop", "illustrator",
    "blockchain", "web3", "defi", "nft", "cybersecurity",
    "data science", "machine learning", "deep learning", "nlp",
    "computer vision", "analytics", "bi", "data warehouse",
    "supply chain", "logistics", "healthcare", "pharma",
    "compliance", "gdpr", "hipaa", "sox", "pci",
}

# ---------------------------------------------------------------------------
# Title extraction patterns
# ---------------------------------------------------------------------------

TITLE_PATTERNS = [
    re.compile(
        r"(?:job\s*title|position|role)\s*[:—\-–]\s*(.+?)(?:\n|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:we are (?:looking|hiring|seeking) (?:for )?(?:an? )?)(.+?)(?:\.|to |\n|$)",
        re.IGNORECASE | re.MULTILINE,
    ),
]

# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

RE_NON_ALNUM = re.compile(r"[^a-z0-9#+.\-/]+")


def _norm(s: str) -> str:
    """Lowercase, collapse whitespace, strip non-alnum (keep #, +, ., -, /)."""
    s = s.lower().strip()
    s = RE_NON_ALNUM.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def _tokenize(s: str) -> list:
    return [t for t in _norm(s).split(" ") if t]


# ---------------------------------------------------------------------------
# Core line-level intent detection
# ---------------------------------------------------------------------------

def _detect_line_intent(line_lower: str) -> str:
    """
    Determine if a line signals 'required', 'preferred', or 'neutral'.
    Uses phrase matching (longer phrases checked first to avoid false positives).
    """
    for cue in PREFERRED_INDICATORS:
        if cue in line_lower:
            return "preferred"
    for cue in REQUIRED_INDICATORS:
        if cue in line_lower:
            return "required"
    return "neutral"


# ---------------------------------------------------------------------------
# Section-level context detection
# ---------------------------------------------------------------------------

_SECTION_REQUIRED_RE = re.compile(
    r"(?:requirements?|qualifications?|must.have|what you.?ll need|minimum)",
    re.IGNORECASE,
)
_SECTION_PREFERRED_RE = re.compile(
    r"(?:nice.to.have|preferred|bonus|desired|good.to.have|what.?s.a.plus)",
    re.IGNORECASE,
)


def _detect_section_intent(heading: str) -> str:
    if _SECTION_PREFERRED_RE.search(heading):
        return "preferred"
    if _SECTION_REQUIRED_RE.search(heading):
        return "required"
    return "neutral"


# ===========================================================================
# Main JD parsing function
# ===========================================================================

def parse_jd(jd_text: str, taxonomy: dict, must_have_overrides: set = None) -> dict:
    """
    Parse a job description and extract a structured 'JD blueprint'.

    Args:
        jd_text: Raw job description text
        taxonomy: {alias_normalized: {"skill_id": str, "canonical_name": str}}
        must_have_overrides: Optional set of skill_ids that company marks as must-have

    Returns:
        {
            "required_skills": {skill_id: weight},      # dict for scoring
            "preferred_skills": {skill_id: weight},      # dict for scoring
            "required_skills_list": [...],               # list for display
            "preferred_skills_list": [...],               # list for display
            "keywords": [str],                           # domain keywords found
            "target_titles": [str],                      # extracted target titles
            "must_have": [str],                          # skill_ids that are must-have
            "min_years": int | None,
            "max_years": int | None,
            "education": [str],
            "certifications": [str],
            "work_mode": str | None,
            "locations": [str],
            "raw_skill_count": int,
        }
    """
    must_have_overrides = must_have_overrides or set()
    text_lower = jd_text.lower()

    # 1. Extract skills with per-line intent detection
    skill_hits = _extract_skills_with_intent(jd_text, taxonomy)

    # 2. Classify skills into required / preferred / neutral
    required = {}       # skill_id → weight
    preferred = {}      # skill_id → weight
    skill_meta = {}     # skill_id → {"name": ..., "evidence_line": ...}

    for sid, info in skill_hits.items():
        skill_meta[sid] = {
            "id": sid,
            "name": info["canonical_name"],
        }

        intents = [e["intent"] for e in info["evidences"]]

        if "required" in intents:
            required[sid] = 3.0
        elif "preferred" in intents:
            preferred[sid] = 1.5
        else:
            # Neutral skills promoted to preferred with weight 1.0
            preferred[sid] = max(preferred.get(sid, 0.0), 1.0)

    # 3. Extract years
    min_years, max_years = _extract_years(text_lower)

    # 4. Extract education
    education = _extract_education(text_lower)

    # 5. Extract certifications
    certifications = _extract_certifications(text_lower)

    # 6. Extract work mode
    work_mode = _extract_work_mode(text_lower)

    # 7. Extract locations
    locations = _extract_locations(jd_text)

    # 8. Extract domain keywords
    keywords = _extract_domain_keywords(text_lower)

    # 9. Extract target titles
    target_titles = _extract_target_titles(jd_text)

    # 10. Must-have set
    must_have = list(must_have_overrides)

    # Build list forms for display (backward compat with frontend)
    required_list = [
        {"id": sid, "name": skill_meta[sid]["name"], "weight": w}
        for sid, w in required.items()
    ]
    preferred_list = [
        {"id": sid, "name": skill_meta[sid]["name"], "weight": w}
        for sid, w in preferred.items()
    ]

    return {
        # Dict forms (for scorer)
        "required_skills": required,
        "preferred_skills": preferred,
        # List forms (for display / frontend)
        "required_skills_list": required_list,
        "preferred_skills_list": preferred_list,
        # New fields
        "keywords": keywords,
        "target_titles": target_titles,
        "must_have": must_have,
        # Existing fields
        "min_years": min_years,
        "max_years": max_years,
        "education": education,
        "certifications": certifications,
        "work_mode": work_mode,
        "locations": locations,
        "raw_skill_count": len(skill_hits),
    }


# ===========================================================================
# Skill extraction with intent detection
# ===========================================================================

def _extract_skills_with_intent(jd_text: str, taxonomy: dict) -> dict:
    """
    Extract skills from JD text with per-line intent detection.

    Returns: {skill_id: {"canonical_name": str, "evidences": [{"line", "intent", "alias"}]}}
    """
    hits = {}  # skill_id → {canonical_name, evidences: []}
    lines = [ln.strip() for ln in jd_text.split("\n") if ln.strip()]

    # Track current section intent (headings affect lines below them)
    current_section_intent = "neutral"

    for ln in lines:
        ln_lower = ln.lower()

        # Check if this line is a section heading
        if len(ln) < 80 and (ln.endswith(":") or ln.isupper() or ln.startswith("#")):
            section_intent = _detect_section_intent(ln)
            if section_intent != "neutral":
                current_section_intent = section_intent
            continue

        # Determine line intent: explicit cues override section context
        line_intent = _detect_line_intent(ln_lower)
        if line_intent == "neutral":
            line_intent = current_section_intent

        # N-gram scan (3, 2, 1) against taxonomy
        words = re.findall(r"[a-z0-9#+.\-]+", ln_lower)
        matched_spans = set()  # avoid double-counting overlapping ngrams

        for n in (3, 2, 1):
            for i in range(max(0, len(words) - n + 1)):
                if any(j in matched_spans for j in range(i, i + n)):
                    continue  # skip if overlapping with a longer match

                phrase = " ".join(words[i:i + n])
                if phrase in taxonomy:
                    info = taxonomy[phrase]
                    sid = info["skill_id"]

                    if sid not in hits:
                        hits[sid] = {
                            "canonical_name": info["canonical_name"],
                            "evidences": [],
                        }

                    hits[sid]["evidences"].append({
                        "line": ln,
                        "intent": line_intent,
                        "alias": phrase,
                    })

                    # Mark these token positions as matched
                    for j in range(i, i + n):
                        matched_spans.add(j)

    return hits


# ===========================================================================
# Constraint extraction helpers (unchanged logic, cleaner code)
# ===========================================================================

def _extract_years(text: str) -> tuple:
    """Extract min/max years of experience."""
    range_match = YEARS_RANGE_RE.search(text)
    if range_match:
        a, b = int(range_match.group(1)), int(range_match.group(2))
        return min(a, b), max(a, b)

    min_match = YEARS_MIN_RE.search(text)
    if min_match:
        return int(min_match.group(1)), None

    return None, None


def _extract_education(text: str) -> list:
    """Find education keywords (>3 chars to avoid false positives)."""
    return sorted(kw for kw in EDUCATION_KEYWORDS if kw in text and len(kw) > 3)


def _extract_certifications(text: str) -> list:
    """Find certification keywords."""
    return sorted(kw for kw in CERTIFICATION_KEYWORDS if kw in text)


def _extract_work_mode(text: str) -> Optional[str]:
    """Detect remote/hybrid/onsite."""
    for mode, keywords in WORK_MODE_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return mode
    return None


def _extract_locations(text: str) -> list:
    """Basic location extraction from common patterns."""
    locations = []
    loc_pattern = re.compile(
        r"(?:location|based in|located in|office in)[:\s]+([A-Z][a-zA-Z\s,]+)",
        re.IGNORECASE,
    )
    for match in loc_pattern.finditer(text):
        loc = match.group(1).strip().rstrip(".")
        if len(loc) > 2 and loc not in locations:
            locations.append(loc)
    return locations


def _extract_domain_keywords(text_lower: str) -> list:
    """Find domain keywords present in JD text."""
    found = []
    # Single-word keywords: token match
    text_tokens = set(re.findall(r"[a-z0-9/\-]+", text_lower))
    for kw in DOMAIN_KEYWORDS:
        if " " in kw:
            # Multi-word: substring match
            if kw in text_lower:
                found.append(kw)
        else:
            if kw in text_tokens:
                found.append(kw)
    return sorted(found)


def _extract_target_titles(jd_text: str) -> list:
    """Extract job titles from JD text using patterns."""
    titles = []
    for pattern in TITLE_PATTERNS:
        for match in pattern.finditer(jd_text):
            title = match.group(1).strip().rstrip(".,;:")
            # Clean and validate
            if 3 < len(title) < 80 and title not in titles:
                titles.append(title)

    return titles[:3]  # max 3 target titles


# ===========================================================================
# Taxonomy builder (unchanged)
# ===========================================================================

def build_taxonomy_lookup() -> dict:
    """
    Build taxonomy lookup dict from database.
    Returns: {alias_normalized: {"skill_id": str, "canonical_name": str}}
    """
    from apps.taxonomy.models import SkillTaxonomy, SkillAlias

    lookup = {}

    # Add canonical names
    for skill in SkillTaxonomy.objects.all():
        norm = skill.canonical_name.lower().strip()
        lookup[norm] = {
            "skill_id": str(skill.id),
            "canonical_name": skill.canonical_name,
        }

    # Add aliases
    for alias in SkillAlias.objects.select_related("skill").all():
        lookup[alias.alias_normalized] = {
            "skill_id": str(alias.skill_id),
            "canonical_name": alias.skill.canonical_name,
        }

    return lookup
