"""
OpenSearch Integration — Index management, document CRUD, and search queries.
"""

import logging
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OpenSearch Client Singleton
# ---------------------------------------------------------------------------

_client = None


def get_client():
    """Get or create OpenSearch client."""
    global _client
    if _client is None:
        try:
            from opensearchpy import OpenSearch
            _client = OpenSearch(
                hosts=[{
                    "host": settings.OPENSEARCH_HOST,
                    "port": settings.OPENSEARCH_PORT,
                }],
                http_auth=settings.OPENSEARCH_HTTP_AUTH,
                use_ssl=settings.OPENSEARCH_USE_SSL,
                verify_certs=False,
                ssl_show_warn=False,
            )
        except ImportError:
            logger.error("opensearch-py not installed")
            return None
    return _client


# ---------------------------------------------------------------------------
# Index Management
# ---------------------------------------------------------------------------

CANDIDATE_INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "tenant_id": {"type": "keyword"},
            "candidate_id": {"type": "keyword"},
            "full_name": {"type": "text", "analyzer": "standard"},
            "headline": {"type": "text"},
            "location": {"type": "keyword"},
            "most_recent_title": {"type": "text", "analyzer": "standard", "fields": {"keyword": {"type": "keyword"}}},
            "most_recent_company": {"type": "text", "analyzer": "standard"},
            "total_experience_years": {"type": "float"},
            "recency_score": {"type": "float"},
            "skills": {
                "type": "nested",
                "properties": {
                    "skill_id": {"type": "keyword"},
                    "canonical_name": {"type": "keyword"},
                    "confidence": {"type": "float"},
                },
            },
            "resume_text": {"type": "text", "analyzer": "standard"},
            "source": {"type": "keyword"},
            "tags": {"type": "keyword"},
            "created_at": {"type": "date"},
            "updated_at": {"type": "date"},
        }
    },
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "analyzer": {
                "standard": {
                    "type": "standard",
                    "stopwords": "_english_",
                },
            },
        },
    },
}


def ensure_index(index_name: str = "candidates"):
    """Create index if it doesn't exist."""
    client = get_client()
    if client is None:
        return

    if not client.indices.exists(index=index_name):
        client.indices.create(index=index_name, body=CANDIDATE_INDEX_MAPPING)
        logger.info(f"Created OpenSearch index: {index_name}")


def index_candidate(tenant_id: str, candidate_id: str, doc: dict, index_name: str = "candidates"):
    """Index or update a candidate document."""
    client = get_client()
    if client is None:
        return

    doc["tenant_id"] = str(tenant_id)
    doc["candidate_id"] = str(candidate_id)
    doc_id = f"{tenant_id}_{candidate_id}"

    client.index(
        index=index_name,
        id=doc_id,
        body=doc,
        refresh="wait_for",
    )
    logger.info(f"Indexed candidate {candidate_id} for tenant {tenant_id}")


def delete_candidate(tenant_id: str, candidate_id: str, index_name: str = "candidates"):
    """Remove a candidate from the index."""
    client = get_client()
    if client is None:
        return

    doc_id = f"{tenant_id}_{candidate_id}"
    try:
        client.delete(index=index_name, id=doc_id, refresh="wait_for")
    except Exception:
        pass


def build_candidate_document(candidate, skills, resume_text: str = "") -> dict:
    """Build an OpenSearch document from a Candidate model instance."""
    return {
        "full_name": candidate.full_name,
        "headline": candidate.headline,
        "location": candidate.location,
        "most_recent_title": candidate.most_recent_title,
        "most_recent_company": candidate.most_recent_company,
        "total_experience_years": candidate.total_experience_years,
        "recency_score": candidate.recency_score,
        "skills": [
            {
                "skill_id": str(s.skill_id),
                "canonical_name": s.canonical_name,
                "confidence": s.confidence,
            }
            for s in skills
        ],
        "resume_text": resume_text[:10000],  # cap text size
        "source": candidate.source,
        "tags": candidate.tags,
        "created_at": candidate.created_at.isoformat() if candidate.created_at else None,
        "updated_at": candidate.updated_at.isoformat() if candidate.updated_at else None,
    }


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def search_candidates(
    tenant_id: str,
    query: str,
    filters: Optional[dict] = None,
    size: int = 25,
    offset: int = 0,
    index_name: str = "candidates",
) -> dict:
    """
    Execute BM25 search with hard filters.
    Falls back to DB search when OpenSearch is unavailable.
    """
    client = get_client()
    if client is None:
        return _db_search_fallback(tenant_id, query, filters, size, offset)

    try:
        return _opensearch_query(client, tenant_id, query, filters, size, offset, index_name)
    except Exception as e:
        logger.warning(f"OpenSearch query failed, falling back to DB: {e}")
        return _db_search_fallback(tenant_id, query, filters, size, offset)

def _opensearch_query(client, tenant_id, query, filters, size, offset, index_name):
    """Execute search via OpenSearch."""
    must_clauses = [{"term": {"tenant_id": str(tenant_id)}}]
    filter_clauses = []

    if filters:
        if filters.get("location"):
            filter_clauses.append({"term": {"location": filters["location"]}})
        if filters.get("min_experience") is not None:
            filter_clauses.append({"range": {"total_experience_years": {"gte": filters["min_experience"]}}})
        if filters.get("max_experience") is not None:
            filter_clauses.append({"range": {"total_experience_years": {"lte": filters["max_experience"]}}})
        if filters.get("required_skills"):
            for skill_id in filters["required_skills"]:
                filter_clauses.append({
                    "nested": {
                        "path": "skills",
                        "query": {"term": {"skills.skill_id": skill_id}},
                    },
                })

    if query:
        must_clauses.append({
            "multi_match": {
                "query": query,
                "fields": [
                    "full_name^1.5",
                    "headline^2.0",
                    "most_recent_title^3.0",
                    "most_recent_company^1.0",
                    "resume_text^1.0",
                ],
                "type": "best_fields",
                "fuzziness": "AUTO",
            },
        })

    body = {
        "query": {
            "bool": {
                "must": must_clauses,
                "filter": filter_clauses,
            }
        },
        "from": offset,
        "size": size,
        "sort": [
            "_score",
            {"updated_at": {"order": "desc"}},
        ],
    }

    result = client.search(index=index_name, body=body)
    hits = result.get("hits", {})

    return {
        "total": hits.get("total", {}).get("value", 0),
        "hits": [
            {
                "candidate_id": hit["_source"]["candidate_id"],
                "score": hit["_score"],
                "source": hit["_source"],
            }
            for hit in hits.get("hits", [])
        ],
    }


def _db_search_fallback(
    tenant_id: str,
    query: str,
    filters: Optional[dict] = None,
    size: int = 25,
    offset: int = 0,
) -> dict:
    """
    Database-backed search fallback when OpenSearch is unavailable.
    Uses Django ORM with icontains for text search.
    """
    from django.db.models import Q, Value, FloatField, Case, When
    from apps.candidates.models import Candidate

    qs = Candidate.objects.filter(tenant_id=tenant_id)

    # Apply text query
    if query:
        q_terms = query.strip().split()
        text_q = Q()
        for term in q_terms:
            text_q &= (
                Q(full_name__icontains=term) |
                Q(headline__icontains=term) |
                Q(most_recent_title__icontains=term) |
                Q(most_recent_company__icontains=term) |
                Q(primary_email__icontains=term) |
                Q(location__icontains=term)
            )
        qs = qs.filter(text_q)

    # Apply filters
    if filters:
        if filters.get("location"):
            qs = qs.filter(location__icontains=filters["location"])
        if filters.get("min_experience") is not None:
            qs = qs.filter(total_experience_years__gte=filters["min_experience"])
        if filters.get("max_experience") is not None:
            qs = qs.filter(total_experience_years__lte=filters["max_experience"])
        if filters.get("required_skills"):
            for skill_id in filters["required_skills"]:
                qs = qs.filter(skills__skill_id=skill_id)

    total = qs.count()
    candidates = qs.order_by("-updated_at")[offset:offset + size]

    hits = []
    for cand in candidates:
        # Simple relevance score based on query match
        score = 1.0
        if query:
            q_lower = query.lower()
            if q_lower in (cand.most_recent_title or "").lower():
                score = 3.0
            elif q_lower in (cand.headline or "").lower():
                score = 2.0
            elif q_lower in (cand.full_name or "").lower():
                score = 1.5

        hits.append({
            "candidate_id": str(cand.id),
            "score": score,
            "source": {
                "candidate_id": str(cand.id),
                "full_name": cand.full_name,
                "headline": cand.headline or "",
                "location": cand.location or "",
                "most_recent_title": cand.most_recent_title or "",
                "most_recent_company": cand.most_recent_company or "",
                "total_experience_years": cand.total_experience_years,
                "recency_score": cand.recency_score,
                "skills": [
                    {"skill_id": str(s.skill_id), "canonical_name": s.canonical_name}
                    for s in cand.skills.all()[:20]
                ],
                "tags": cand.tags or [],
            },
        })

    return {"total": total, "hits": hits}


# ---------------------------------------------------------------------------
# Boolean Search Parser (Features 39-44)
# ---------------------------------------------------------------------------

def parse_boolean_query(query: str) -> dict:
    """
    Parse boolean search query with AND/OR/NOT operators.

    Examples:
        "python AND django"        → must include both
        "python OR java"           → include either
        "python NOT junior"        → include python, exclude junior
        "python AND (django OR flask)" → nested groups

    Returns: {"must": [...], "should": [...], "must_not": [...]}
    """
    import re

    # Normalize whitespace
    query = query.strip()

    result = {"must": [], "should": [], "must_not": []}

    if not query:
        return result

    # Handle quoted phrases first
    phrases = re.findall(r'"([^"]+)"', query)
    for phrase in phrases:
        result["must"].append(phrase)
        query = query.replace(f'"{phrase}"', '')

    # Split by AND/OR/NOT
    tokens = re.split(r'\s+', query.strip())

    mode = "must"
    for token in tokens:
        upper = token.upper()
        if upper == "AND":
            mode = "must"
        elif upper == "OR":
            mode = "should"
        elif upper == "NOT":
            mode = "must_not"
        elif upper in ("(", ")"):
            continue  # Simple skip for parentheses
        elif token.strip():
            result[mode].append(token.strip())
            mode = "must"  # Reset to default

    return result


def boolean_search_candidates(
    tenant_id: str,
    query: str,
    filters: Optional[dict] = None,
    size: int = 25,
    offset: int = 0,
) -> dict:
    """
    Execute boolean search with AND/OR/NOT operators.
    Uses parse_boolean_query to build structured queries.
    """
    from django.db.models import Q
    from apps.candidates.models import Candidate

    parsed = parse_boolean_query(query)
    qs = Candidate.objects.filter(tenant_id=tenant_id, status="active")

    search_fields = [
        "full_name", "headline", "most_recent_title",
        "most_recent_company", "primary_email", "location",
    ]

    # Must terms (AND)
    for term in parsed["must"]:
        term_q = Q()
        for field in search_fields:
            term_q |= Q(**{f"{field}__icontains": term})
        # Also search skills
        term_q |= Q(skills__canonical_name__icontains=term)
        qs = qs.filter(term_q)

    # Should terms (OR) — at least one must match
    if parsed["should"]:
        should_q = Q()
        for term in parsed["should"]:
            for field in search_fields:
                should_q |= Q(**{f"{field}__icontains": term})
            should_q |= Q(skills__canonical_name__icontains=term)
        qs = qs.filter(should_q)

    # Must-not terms (NOT)
    for term in parsed["must_not"]:
        exclude_q = Q()
        for field in search_fields:
            exclude_q |= Q(**{f"{field}__icontains": term})
        exclude_q |= Q(skills__canonical_name__icontains=term)
        qs = qs.exclude(exclude_q)

    # Apply standard filters
    if filters:
        if filters.get("location"):
            qs = qs.filter(location__icontains=filters["location"])
        if filters.get("pool_status"):
            qs = qs.filter(pool_status=filters["pool_status"])
        if filters.get("talent_tier"):
            qs = qs.filter(talent_tier=filters["talent_tier"])
        if filters.get("min_experience") is not None:
            qs = qs.filter(total_experience_years__gte=filters["min_experience"])
        if filters.get("max_experience") is not None:
            qs = qs.filter(total_experience_years__lte=filters["max_experience"])

    qs = qs.distinct()
    total = qs.count()
    candidates = qs.order_by("-updated_at")[offset:offset + size]

    hits = []
    for cand in candidates:
        hits.append({
            "candidate_id": str(cand.id),
            "score": 1.0,
            "source": {
                "candidate_id": str(cand.id),
                "full_name": cand.full_name,
                "headline": cand.headline or "",
                "location": cand.location or "",
                "most_recent_title": cand.most_recent_title or "",
                "pool_status": cand.pool_status,
                "talent_tier": cand.talent_tier,
                "rating": cand.rating,
            },
        })

    return {"total": total, "hits": hits}


# ---------------------------------------------------------------------------
# Auto-Match Candidates (Feature 45-48)
# ---------------------------------------------------------------------------

def auto_match_candidates(tenant_id: str, job_id: str, limit: int = 20) -> list:
    """
    Find top matching candidates from the talent pool for a job.
    Uses structured scoring from ranking engine.
    """
    from apps.jobs.models import Job
    from apps.candidates.models import Candidate
    from apps.search.ranking import compute_structured_score

    try:
        job = Job.objects.get(id=job_id, tenant_id=tenant_id)
    except Job.DoesNotExist:
        return []

    job_required = set(job.required_skills or [])
    job_optional = set(job.optional_skills or [])
    target_titles = job.target_titles or []
    job_domains = job.domain_tags or []

    # Get talent pool candidates (active/pipeline, not hired)
    candidates = Candidate.objects.filter(
        tenant_id=tenant_id,
        status="active",
        pool_status__in=["active", "pipeline", "new"],
    ).prefetch_related("skills")[:500]  # Cap for performance

    scored = []
    for cand in candidates:
        cand_skills = set(str(s.skill_id) for s in cand.skills.all())
        result = compute_structured_score(
            candidate_skills=cand_skills,
            job_required=job_required,
            job_optional=job_optional,
            candidate_title=cand.most_recent_title or "",
            target_titles=target_titles,
            total_years=cand.total_experience_years,
            min_years=job.min_years_experience,
            max_years=job.max_years_experience,
            candidate_recency=cand.recency_score,
            candidate_tags=cand.tags or [],
            job_domains=job_domains,
        )
        scored.append({
            "candidate_id": str(cand.id),
            "full_name": cand.full_name,
            "headline": cand.headline or "",
            "talent_tier": cand.talent_tier,
            "pool_status": cand.pool_status,
            "score": result["total"],
            "breakdown": result["components"],
        })

    # Sort by score descending, return top N
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]


def find_similar_candidates(tenant_id: str, candidate_id: str, limit: int = 10) -> list:
    """
    Find candidates similar to a given candidate based on skills, title, experience.
    """
    from apps.candidates.models import Candidate

    try:
        source = Candidate.objects.get(id=candidate_id, tenant_id=tenant_id)
    except Candidate.DoesNotExist:
        return []

    source_skills = set(str(s.skill_id) for s in source.skills.all())
    source_title = (source.most_recent_title or "").lower()
    source_exp = source.total_experience_years or 0

    candidates = Candidate.objects.filter(
        tenant_id=tenant_id,
        status="active",
    ).exclude(id=candidate_id).prefetch_related("skills")[:500]

    scored = []
    for cand in candidates:
        cand_skills = set(str(s.skill_id) for s in cand.skills.all())
        cand_title = (cand.most_recent_title or "").lower()
        cand_exp = cand.total_experience_years or 0

        # Skill overlap (Jaccard)
        if source_skills or cand_skills:
            skill_sim = len(source_skills & cand_skills) / max(len(source_skills | cand_skills), 1)
        else:
            skill_sim = 0.0

        # Title similarity
        title_sim = 0.0
        if source_title and cand_title:
            if source_title == cand_title:
                title_sim = 1.0
            elif source_title in cand_title or cand_title in source_title:
                title_sim = 0.5

        # Experience proximity
        exp_diff = abs(source_exp - cand_exp)
        exp_sim = max(0, 1.0 - (exp_diff / max(source_exp, 5)))

        total = 0.5 * skill_sim + 0.3 * title_sim + 0.2 * exp_sim

        if total > 0.1:  # Minimum threshold
            scored.append({
                "candidate_id": str(cand.id),
                "full_name": cand.full_name,
                "headline": cand.headline or "",
                "similarity_score": round(total, 3),
                "skill_overlap": round(skill_sim, 3),
                "shared_skills": len(source_skills & cand_skills),
            })

    scored.sort(key=lambda x: x["similarity_score"], reverse=True)
    return scored[:limit]


# ---------------------------------------------------------------------------
# Skill Gap Analysis (Feature 49-52)
# ---------------------------------------------------------------------------

def skill_gap_analysis(tenant_id: str, candidate_id: str, job_id: str) -> dict:
    """
    Compare candidate skills with job requirements.
    Returns matched, missing, and bonus (extra) skills.
    """
    from apps.jobs.models import Job
    from apps.candidates.models import Candidate

    try:
        candidate = Candidate.objects.get(id=candidate_id, tenant_id=tenant_id)
        job = Job.objects.get(id=job_id, tenant_id=tenant_id)
    except (Candidate.DoesNotExist, Job.DoesNotExist):
        return {"error": "Candidate or job not found"}

    cand_skills = set(str(s.skill_id) for s in candidate.skills.all())
    cand_skill_names = {str(s.skill_id): s.canonical_name for s in candidate.skills.all()}

    required = set(job.required_skills or [])
    optional = set(job.optional_skills or [])

    matched_required = required & cand_skills
    missing_required = required - cand_skills
    matched_optional = optional & cand_skills
    missing_optional = optional - cand_skills
    bonus_skills = cand_skills - required - optional

    return {
        "match_percentage": round(len(matched_required) / max(len(required), 1) * 100, 1),
        "matched_required": [cand_skill_names.get(s, s) for s in matched_required],
        "missing_required": list(missing_required),
        "matched_optional": [cand_skill_names.get(s, s) for s in matched_optional],
        "missing_optional": list(missing_optional),
        "bonus_skills": [cand_skill_names.get(s, s) for s in bonus_skills],
        "total_candidate_skills": len(cand_skills),
        "coverage": {
            "required": f"{len(matched_required)}/{len(required)}",
            "optional": f"{len(matched_optional)}/{len(optional)}",
        },
    }


# ---------------------------------------------------------------------------
# Rediscovery Search — surface previously-rejected or dormant candidates
# ---------------------------------------------------------------------------

def rediscovery_search(
    tenant_id: str,
    job_id: str,
    months_lookback: int = 18,
    min_score: float = 0.5,
    limit: int = 25,
) -> list:
    """
    Find candidates who applied in the past but were rejected or went cold,
    and who now appear to be a good fit (re-scored against current job requirements).

    Returns candidates sorted by re-match score descending.
    """
    from datetime import timedelta
    from django.utils import timezone
    from apps.jobs.models import Job
    from apps.candidates.models import Candidate
    from apps.applications.models import Application
    from apps.search.ranking import compute_structured_score

    try:
        job = Job.objects.get(id=job_id, tenant_id=tenant_id)
    except Job.DoesNotExist:
        return []

    cutoff = timezone.now() - timedelta(days=months_lookback * 30)

    # Find candidates with prior (non-active) applications to any job
    past_candidate_ids = Application.objects.filter(
        tenant_id=tenant_id,
        created_at__gte=cutoff,
        status__in=["rejected", "withdrawn"],
    ).values_list("candidate_id", flat=True).distinct()

    candidates = Candidate.objects.filter(
        tenant_id=tenant_id,
        id__in=past_candidate_ids,
        status="active",
    ).prefetch_related("skills")

    job_required = set(job.required_skills or [])
    job_optional = set(job.optional_skills or [])
    target_titles = job.target_titles or []
    job_domains = job.domain_tags or []

    results = []
    for cand in candidates:
        cand_skills = set(str(s.skill_id) for s in cand.skills.all())
        scored = compute_structured_score(
            candidate_skills=cand_skills,
            job_required=job_required,
            job_optional=job_optional,
            candidate_title=cand.most_recent_title or "",
            target_titles=target_titles,
            total_years=cand.total_experience_years,
            min_years=job.min_years_experience,
            max_years=job.max_years_experience,
            candidate_recency=cand.recency_score,
            candidate_tags=cand.tags or [],
            job_domains=job_domains,
        )
        if scored["total"] >= min_score:
            results.append({
                "candidate_id": str(cand.id),
                "full_name": cand.full_name,
                "headline": cand.headline or "",
                "most_recent_title": cand.most_recent_title or "",
                "talent_tier": cand.talent_tier,
                "re_match_score": round(scored["total"], 3),
                "breakdown": scored["components"],
            })

    results.sort(key=lambda x: x["re_match_score"], reverse=True)
    return results[:limit]


# ---------------------------------------------------------------------------
# Market Supply Estimate — estimate talent pool size for a given profile
# ---------------------------------------------------------------------------

def market_supply_estimate(
    tenant_id: str,
    required_skills: list,
    location: str = "",
    min_experience: Optional[float] = None,
    max_experience: Optional[float] = None,
) -> dict:
    """
    Estimate the number of matching candidates in the tenant's database
    (and optionally the wider indexed pool) for a given skills + location profile.

    Returns a supply estimate dict used by analytics_forecasting.
    """
    from apps.candidates.models import Candidate
    from django.db.models import Q

    qs = Candidate.objects.filter(tenant_id=tenant_id, status="active")

    if location:
        qs = qs.filter(location__icontains=location)

    if min_experience is not None:
        qs = qs.filter(total_experience_years__gte=min_experience)

    if max_experience is not None:
        qs = qs.filter(total_experience_years__lte=max_experience)

    for skill_id in required_skills:
        qs = qs.filter(skills__skill_id=skill_id)

    qs = qs.distinct()
    total_in_pool = qs.count()

    # Bucket breakdown
    active_count = qs.filter(pool_status="active").count()
    pipeline_count = qs.filter(pool_status="pipeline").count()
    new_count = qs.filter(pool_status="new").count()

    return {
        "total_matching": total_in_pool,
        "breakdown": {
            "active": active_count,
            "in_pipeline": pipeline_count,
            "new": new_count,
        },
        "supply_signal": (
            "high" if total_in_pool >= 50
            else "medium" if total_in_pool >= 10
            else "low"
        ),
        "filters_applied": {
            "required_skills": required_skills,
            "location": location,
            "min_experience": min_experience,
            "max_experience": max_experience,
        },
    }
