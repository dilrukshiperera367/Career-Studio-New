"""Celery tasks for resume parsing and candidate indexing."""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def parse_resume(self, resume_document_id: str):
    """
    Full parsing pipeline for a resume document.

    1. Fetch resume file from storage
    2. Run parse pipeline (extract → clean → sections → entities → normalize)
    3. Update ResumeDocument with parsed data
    4. Update Candidate derived fields
    5. Trigger OpenSearch indexing
    """
    from apps.candidates.models import ResumeDocument, CandidateSkill, CandidateExperience

    try:
        resume = ResumeDocument.objects.select_related("candidate").get(id=resume_document_id)
    except ResumeDocument.DoesNotExist:
        logger.error(f"Resume {resume_document_id} not found")
        return

    # Mark as parsing
    resume.parse_status = "parsing"
    resume.save(update_fields=["parse_status"])

    try:
        # Read file from disk (local storage) or S3 in production
        import os
        from django.conf import settings as django_settings

        file_path = os.path.join(django_settings.MEDIA_ROOT, resume.file_url)
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                file_content = f.read()
        elif resume.raw_text:
            # Fallback to raw_text if file not on disk
            file_content = resume.raw_text.encode("utf-8")
        else:
            logger.error(f"Resume file not found: {file_path}")
            resume.parse_status = "failed"
            resume.save(update_fields=["parse_status"])
            return

        # Load skill taxonomy - build alias map
        from apps.taxonomy.models import SkillAlias
        alias_map = {}
        for alias in SkillAlias.objects.select_related("skill").all():
            alias_map[alias.alias_normalized] = {
                "skill_id": str(alias.skill_id),
                "canonical_name": alias.skill.canonical_name,
            }

        # Run pipeline
        from apps.parsing.services import parse_resume_full

        result = parse_resume_full(
            file_content=file_content,
            file_type=resume.file_type,
            taxonomy=alias_map,
        )

        # Update resume document
        resume.raw_text = result["raw_text"]
        resume.clean_text = result["clean_text"]
        resume.parsed_json = result["parsed_json"]
        resume.parse_status = "parsed"
        resume.save(update_fields=[
            "raw_text", "clean_text", "parsed_json", "parse_status", "updated_at",
        ])

        # Update candidate with derived fields
        candidate = resume.candidate
        derived = result["parsed_json"]["derived"]
        candidate.total_experience_years = derived.get("total_experience_years")
        candidate.most_recent_title = derived.get("most_recent_title", "")
        candidate.most_recent_company = derived.get("most_recent_company", "")
        candidate.recency_score = derived.get("recency_score")
        candidate.save(update_fields=[
            "total_experience_years", "most_recent_title",
            "most_recent_company", "recency_score", "updated_at",
        ])

        # Persist extracted skills
        for skill_data in result["parsed_json"].get("skills", []):
            CandidateSkill.objects.update_or_create(
                candidate=candidate,
                skill_id=skill_data["skill_id"],
                tenant_id=str(candidate.tenant_id),
                defaults={
                    "canonical_name": skill_data["canonical_name"],
                    "confidence": skill_data.get("confidence", 1.0),
                    "evidence": skill_data.get("evidence", []),
                },
            )

        # Persist extracted experiences
        for exp in result["parsed_json"].get("experience", []):
            from apps.parsing.services import parse_fuzzy_date
            CandidateExperience.objects.create(
                tenant_id=str(candidate.tenant_id),
                candidate=candidate,
                company_name=exp.get("company", ""),
                title=exp.get("title", ""),
                start_date=parse_fuzzy_date(exp.get("start", "")),
                end_date=parse_fuzzy_date(exp.get("end", "")),
                raw_block=exp.get("raw_block", ""),
            )

        # Trigger indexing
        index_candidate.delay(str(candidate.id), str(candidate.tenant_id))

        logger.info(f"Resume {resume_document_id} parsed successfully")

    except Exception as e:
        resume.parse_status = "failed"
        resume.parse_error = str(e)
        resume.save(update_fields=["parse_status", "parse_error"])
        logger.error(f"Resume parse failed: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def index_candidate(self, candidate_id: str, tenant_id: str):
    """Index candidate in OpenSearch."""
    try:
        from apps.candidates.models import Candidate
        from apps.search.services import (
            index_candidate as os_index,
            build_candidate_document,
        )

        candidate = Candidate.objects.get(id=candidate_id, tenant_id=tenant_id)
        skills = candidate.skills.all()

        # Get latest resume clean text
        latest_resume = candidate.resumes.filter(parse_status="parsed").first()
        resume_text = latest_resume.clean_text if latest_resume else ""

        doc = build_candidate_document(candidate, skills, resume_text)
        os_index(tenant_id, candidate_id, doc)

        logger.info(f"Candidate {candidate_id} indexed")
    except Exception as e:
        logger.error(f"Index failed: {e}")
        raise self.retry(exc=e)
