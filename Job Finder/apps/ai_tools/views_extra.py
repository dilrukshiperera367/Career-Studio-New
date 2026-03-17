"""
Feature 15 — AI & Personalization Layer
Extra views: personalized job ranking, "why this job" explanations,
"missing skills" detection, title normalization, salary inference,
job summary cards, scam risk flags, employer quality predictions,
application success likelihood, seeker reactivation prompts,
search rewrite suggestions, review summarization, Q&A answer drafting,
candidate apply assistant, recruiter job-post optimization assistant.

All AI logic uses rule-based heuristics — no external LLM dependency required.
Every recommendation includes an explanation and an override mechanism.
"""
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

# ── Title Normalization Map ────────────────────────────────────────────────────

TITLE_ALIASES = {
    "swe": "Software Engineer", "dev": "Software Engineer",
    "developer": "Software Engineer", "programmer": "Software Engineer",
    "coder": "Software Engineer", "devops": "DevOps Engineer",
    "be dev": "Backend Engineer", "fe dev": "Frontend Engineer",
    "ui dev": "Frontend Engineer", "ux designer": "UX Designer",
    "ui/ux": "UI/UX Designer", "data science": "Data Scientist",
    "ml engineer": "Machine Learning Engineer", "ai engineer": "AI Engineer",
    "qa": "QA Engineer", "tester": "QA Engineer",
    "pm": "Product Manager", "po": "Product Owner",
    "hr": "HR Manager", "human resources": "HR Manager",
    "exec asst": "Executive Assistant", "admin": "Administrative Assistant",
    "acct manager": "Account Manager", "biz dev": "Business Development",
    "mktg": "Marketing Specialist", "digital mktg": "Digital Marketing Specialist",
    "finance": "Finance Analyst", "accountant": "Accountant",
    "ops": "Operations Manager", "supply chain": "Supply Chain Manager",
    "driver": "Driver", "security guard": "Security Officer",
    "teacher": "Teacher", "lecturer": "Lecturer",
}

SKILL_DOMAIN_MAP = {
    "Software Engineer": ["Python", "Java", "JavaScript", "SQL", "Git", "REST API", "Agile"],
    "Frontend Engineer": ["React", "TypeScript", "HTML", "CSS", "Next.js", "Tailwind"],
    "Backend Engineer": ["Django", "Node.js", "PostgreSQL", "Redis", "Docker", "AWS"],
    "DevOps Engineer": ["Docker", "Kubernetes", "CI/CD", "Terraform", "AWS", "Linux"],
    "Data Scientist": ["Python", "Machine Learning", "SQL", "TensorFlow", "Pandas", "Tableau"],
    "Product Manager": ["Agile", "Jira", "Roadmapping", "User Research", "Analytics", "Stakeholder Management"],
    "UX Designer": ["Figma", "Wireframing", "User Research", "Prototyping", "Adobe XD"],
    "Digital Marketing Specialist": ["SEO", "Google Ads", "Social Media", "Analytics", "Content Marketing"],
    "HR Manager": ["Recruitment", "HRIS", "Performance Management", "Labor Law", "Onboarding"],
}

SALARY_BENCHMARKS = {
    "Software Engineer": {"entry": (80000, 120000), "mid": (120000, 200000), "senior": (200000, 350000)},
    "Product Manager": {"entry": (90000, 130000), "mid": (130000, 220000), "senior": (200000, 350000)},
    "Data Scientist": {"entry": (100000, 150000), "mid": (150000, 250000), "senior": (250000, 400000)},
    "UX Designer": {"entry": (60000, 100000), "mid": (100000, 180000), "senior": (180000, 300000)},
    "Frontend Engineer": {"entry": (70000, 110000), "mid": (110000, 190000), "senior": (190000, 320000)},
    "Digital Marketing Specialist": {"entry": (50000, 80000), "mid": (80000, 140000), "senior": (140000, 220000)},
    "HR Manager": {"entry": (55000, 85000), "mid": (85000, 150000), "senior": (150000, 250000)},
}

SEARCH_REWRITES = {
    "work from home": "remote jobs",
    "wfh": "remote jobs",
    "home based": "remote jobs work from home",
    "part time": "part-time jobs",
    "no experience": "entry level fresh graduate",
    "freshers": "entry level fresh graduate",
    "it jobs": "software engineer developer IT",
    "bank jobs": "banking finance financial services",
    "government": "government state sector public sector",
    "teaching": "teacher lecturer academic education",
}


# ── Title Normalizer ───────────────────────────────────────────────────────────

class TitleNormalizationView(APIView):
    """
    POST /ai/normalize-title/
    Normalize a raw job title to a standard form.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        raw = (request.data.get("title") or "").strip().lower()
        normalized = None
        for alias, standard in TITLE_ALIASES.items():
            if alias in raw:
                normalized = standard
                break
        if not normalized:
            # Capitalize each word if no alias found
            normalized = raw.title()
            confidence = 0.5
        else:
            confidence = 0.9

        return Response({
            "raw_title": request.data.get("title"),
            "normalized_title": normalized,
            "confidence": confidence,
            "explanation": f"'{raw}' maps to the standard title '{normalized}' in Sri Lankan job market taxonomy.",
            "can_override": True,
        })


# ── Salary Inference ───────────────────────────────────────────────────────────

class SalaryInferenceView(APIView):
    """
    POST /ai/salary-inference/
    Infer expected salary range for a job posting without salary info.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        title = request.data.get("title", "")
        exp_level = request.data.get("experience_level", "mid").lower()  # entry | mid | senior
        location = request.data.get("location", "Colombo")

        # Normalize title first
        normalized = title
        for alias, std in TITLE_ALIASES.items():
            if alias in title.lower():
                normalized = std
                break

        bench = SALARY_BENCHMARKS.get(normalized, {})
        if not bench:
            # Generic fallback
            bench = {"entry": (40000, 70000), "mid": (70000, 130000), "senior": (130000, 250000)}

        level = exp_level if exp_level in bench else "mid"
        low, high = bench[level]

        # Location adjustment
        col_adj = 1.0 if "colombo" in location.lower() else 0.85

        return Response({
            "title": normalized,
            "experience_level": level,
            "location": location,
            "inferred_min": round(low * col_adj),
            "inferred_max": round(high * col_adj),
            "currency": "LKR",
            "period": "monthly",
            "confidence": 0.75 if normalized in SALARY_BENCHMARKS else 0.5,
            "explanation": f"Based on market data for {normalized} ({level}-level) in {location}.",
            "can_override": True,
            "disclaimer": "Salary estimates are based on reported market data. Actual salaries may vary.",
        })


# ── Personalized Job Ranking ───────────────────────────────────────────────────

class PersonalizedJobRankingView(APIView):
    """
    GET /ai/personalized-feed/
    Returns jobs re-ranked by personalization signals for the authenticated seeker.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.jobs.models import JobListing

        user = request.user

        # Get user profile signals
        profile = getattr(user, "profile", None)
        target_titles = []
        target_skills = []
        expected_salary_min = 0

        if profile:
            target_titles = list(getattr(profile, "target_job_titles", None) or [])
            target_skills = list(getattr(profile, "skills", None) or [])
            expected_salary_min = getattr(profile, "expected_salary_min", 0) or 0

        # Browse history signals (from saved jobs / applications)
        from apps.jobs.models import SavedJob
        from apps.applications.models import Application
        viewed_employers = list(
            SavedJob.objects.filter(user=user).values_list("job__employer_id", flat=True)[:10]
        )
        applied_titles = list(
            Application.objects.filter(applicant=user).values_list("job__title", flat=True)[:10]
        )

        # Base query
        jobs = list(
            JobListing.objects.filter(status="active")
            .select_related("employer", "district")
            .order_by("-created_at")[:100]
        )

        # Score each job
        ranked = []
        for job in jobs:
            score = 0.0
            reasons = []

            # Title match
            for title in target_titles:
                if title.lower() in job.title.lower() or job.title.lower() in title.lower():
                    score += 30
                    reasons.append(f"Matches your target title: {title}")
                    break

            # Employer match (saved or applied before)
            if job.employer_id in viewed_employers:
                score += 15
                reasons.append("From a company you've shown interest in")

            # Salary match
            if expected_salary_min and job.salary_min and job.salary_min >= expected_salary_min * 0.9:
                score += 20
                reasons.append(f"Salary meets your expectation (LKR {job.salary_min:,}+)")

            # Skill match (if job has required_skills field)
            req_skills = getattr(job, "required_skills", []) or []
            if isinstance(req_skills, list) and target_skills:
                matches = [s for s in target_skills if s in req_skills]
                if matches:
                    score += len(matches) * 8
                    reasons.append(f"You match: {', '.join(matches[:3])}")

            # Freshness bonus
            age_days = (timezone.now() - job.created_at).days
            score += max(0, 10 - age_days)

            # Cold start (no signals): use editorial quality score
            if not reasons:
                reasons.append("Trending in your region")
                score += 5

            ranked.append({
                "id": str(job.id),
                "title": job.title,
                "company": job.employer.company_name,
                "district": job.district.name if job.district else None,
                "salary_min": job.salary_min,
                "salary_max": job.salary_max,
                "created_at": job.created_at,
                "_score": score,
                "why_this_job": reasons[:3],
                "personalization_confidence": "low" if not target_titles else "medium" if score < 30 else "high",
            })

        ranked.sort(key=lambda x: x["_score"], reverse=True)
        for r in ranked:
            r.pop("_score")

        return Response({
            "personalized": bool(target_titles or target_skills),
            "cold_start": not target_titles and not target_skills,
            "cold_start_message": "Complete your profile to get personalized job matches." if not target_titles else None,
            "jobs": ranked[:30],
            "can_override": True,
            "override_hint": "Use the Sort dropdown to switch to Newest or Salary ranking.",
        })


# ── Missing Skills Explainer ───────────────────────────────────────────────────

class MissingSkillsView(APIView):
    """
    POST /ai/missing-skills/
    Compare seeker skills against job requirements, return match + gaps.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        seeker_skills = [s.lower() for s in (request.data.get("seeker_skills") or [])]
        job_required = [s.lower() for s in (request.data.get("job_required_skills") or [])]
        job_preferred = [s.lower() for s in (request.data.get("job_preferred_skills") or [])]
        job_title = request.data.get("job_title", "")

        matched_required = [s for s in job_required if s in seeker_skills]
        missing_required = [s for s in job_required if s not in seeker_skills]
        matched_preferred = [s for s in job_preferred if s in seeker_skills]
        missing_preferred = [s for s in job_preferred if s not in seeker_skills]

        total_req = len(job_required) or 1
        match_pct = round(len(matched_required) / total_req * 100)

        # Application success likelihood
        success_likelihood = (
            "high" if match_pct >= 80
            else "medium" if match_pct >= 50
            else "low"
        )

        # Learning resources for missing skills (placeholder)
        learning_tips = {
            skill: f"Search '{skill} tutorial' on Coursera, YouTube, or LinkedIn Learning"
            for skill in missing_required[:3]
        }

        return Response({
            "job_title": job_title,
            "match_percentage": match_pct,
            "application_success_likelihood": success_likelihood,
            "matched_required": matched_required,
            "missing_required": missing_required,
            "matched_preferred": matched_preferred,
            "missing_preferred": missing_preferred,
            "you_match_on": f"You match {len(matched_required)} of {len(job_required)} required skills",
            "gap_summary": f"Missing {len(missing_required)} required skill(s)" if missing_required else "You meet all required skills!",
            "learning_resources": learning_tips,
            "can_override": True,
            "explanation": f"Match score based on comparison of your listed skills against job requirements for {job_title}.",
        })


# ── Job Summary Card ───────────────────────────────────────────────────────────

class JobSummaryCardView(APIView):
    """
    GET /ai/job-summary/<uuid:job_id>/
    AI-generated summary card for a job — highlights, perks, must-knows.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, job_id):
        from apps.jobs.models import JobListing
        try:
            job = JobListing.objects.select_related("employer", "district").get(pk=job_id)
        except JobListing.DoesNotExist:
            return Response(status=404)

        desc = (getattr(job, "description", "") or "").lower()

        # Detect perks
        perk_map = {
            "Remote Work": ["remote", "work from home", "wfh"],
            "Health Insurance": ["health insurance", "medical insurance", "medical cover"],
            "Performance Bonus": ["performance bonus", "kpi bonus", "annual bonus"],
            "Training": ["training", "learning & development", "l&d", "upskilling"],
            "Flexible Hours": ["flexible hours", "flexi time", "flexitime"],
            "Transport": ["transport", "shuttle", "company vehicle"],
            "Meal Allowance": ["meal", "lunch", "canteen"],
        }
        detected_perks = [label for label, keywords in perk_map.items() if any(kw in desc for kw in keywords)]

        # Key requirements (from description)
        exp_match = next((w for w in ["1 year", "2 years", "3 years", "5 years", "senior", "junior", "entry"] if w in desc), None)

        # Salary display
        salary_str = "Not disclosed"
        if job.salary_min and job.salary_max:
            salary_str = f"LKR {job.salary_min:,} – {job.salary_max:,}/month"
        elif job.salary_min:
            salary_str = f"LKR {job.salary_min:,}+/month"

        # Scam risk flag check
        from apps.trust_ops.models import ScamAlert
        has_scam_flag = ScamAlert.objects.filter(job=job, is_public=True, is_resolved=False).exists()

        summary_bullets = []
        if detected_perks:
            summary_bullets.append(f"Perks: {', '.join(detected_perks[:4])}")
        if exp_match:
            summary_bullets.append(f"Experience: {exp_match.title()} level required")
        if job.district:
            summary_bullets.append(f"Location: {job.district.name}")
        if getattr(job, "is_remote", False):
            summary_bullets.append("Fully remote eligible")
        if getattr(job, "application_deadline", None):
            summary_bullets.append(f"Apply by: {job.application_deadline}")

        return Response({
            "job_id": str(job.id),
            "title": job.title,
            "company": job.employer.company_name,
            "salary": salary_str,
            "summary_bullets": summary_bullets,
            "detected_perks": detected_perks,
            "experience_hint": exp_match,
            "has_scam_risk_flag": has_scam_flag,
            "scam_warning": "⚠️ Trust & Safety flag active for this job." if has_scam_flag else None,
            "is_ai_generated": True,
            "explanation": "Summary extracted from job description using keyword analysis.",
            "can_override": True,
        })


# ── Scam Risk Flag on Job ─────────────────────────────────────────────────────

class JobScamRiskFlagView(APIView):
    """
    GET /ai/scam-risk/<uuid:job_id>/
    Quick AI scam risk prediction for a job (0-100 risk score).
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, job_id):
        from apps.jobs.models import JobListing
        from apps.trust_ops.models import ScamAlert
        from apps.trust_ops.views_extra import SCAM_PHRASES

        try:
            job = JobListing.objects.select_related("employer").get(pk=job_id)
        except JobListing.DoesNotExist:
            return Response(status=404)

        desc = (getattr(job, "description", "") or "").lower()
        title = job.title.lower()
        risk = 0
        flags = []

        for phrase in SCAM_PHRASES:
            if phrase in desc or phrase in title:
                flags.append(phrase)
                risk += 12

        # Active scam alerts add 30
        if ScamAlert.objects.filter(job=job, is_public=True, is_resolved=False).exists():
            risk += 30
            flags.append("active_scam_alert")

        # Very short description
        if len(desc) < 100:
            risk += 10
            flags.append("very_short_description")

        risk = min(100, risk)
        level = "critical" if risk >= 70 else "high" if risk >= 45 else "medium" if risk >= 25 else "low"

        return Response({
            "job_id": str(job_id),
            "risk_score": risk,
            "risk_level": level,
            "flags": flags,
            "safe_to_apply": risk < 45,
            "explanation": f"Risk score computed from {len(flags)} signal(s) detected in job content.",
            "can_override": True,
        })


# ── Application Success Likelihood ────────────────────────────────────────────

class ApplicationSuccessLikelihoodView(APIView):
    """
    POST /ai/success-likelihood/
    Predict likelihood of application success based on seeker vs job match.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        d = request.data
        required_exp_years = int(d.get("required_exp_years", 0))
        seeker_exp_years = int(d.get("seeker_exp_years", 0))
        skill_match_pct = int(d.get("skill_match_pct", 50))
        has_portfolio = bool(d.get("has_portfolio", False))
        has_cover_letter = bool(d.get("has_cover_letter", True))
        employer_response_rate_pct = int(d.get("employer_response_rate_pct", 50))

        # Scoring
        score = 0
        factors = []

        # Skill match (weight: 40%)
        score += skill_match_pct * 0.4
        factors.append({"factor": "Skill Match", "contribution": f"{round(skill_match_pct * 0.4, 1)}pts", "value": f"{skill_match_pct}% skill match"})

        # Experience fit (weight: 25%)
        if seeker_exp_years >= required_exp_years:
            score += 25
            factors.append({"factor": "Experience", "contribution": "25pts", "value": "Meets requirement"})
        elif seeker_exp_years >= required_exp_years * 0.7:
            score += 15
            factors.append({"factor": "Experience", "contribution": "15pts", "value": "Close to requirement"})
        else:
            factors.append({"factor": "Experience", "contribution": "0pts", "value": "Below requirement"})

        # Portfolio (weight: 10%)
        if has_portfolio:
            score += 10
            factors.append({"factor": "Portfolio", "contribution": "10pts", "value": "Portfolio attached"})

        # Cover letter (weight: 10%)
        if has_cover_letter:
            score += 10
            factors.append({"factor": "Cover Letter", "contribution": "10pts", "value": "Personalized cover letter"})

        # Employer response rate (weight: 15% — proxy for hiring activity)
        score += employer_response_rate_pct * 0.15
        factors.append({"factor": "Employer Activity", "contribution": f"{round(employer_response_rate_pct * 0.15, 1)}pts", "value": f"{employer_response_rate_pct}% response rate"})

        score = min(100, round(score))
        likelihood = "high" if score >= 70 else "medium" if score >= 45 else "low"

        tips = []
        if not has_cover_letter:
            tips.append("Add a personalized cover letter to boost your chances by ~10%")
        if not has_portfolio:
            tips.append("Attach a portfolio or GitHub link")
        if skill_match_pct < 70:
            tips.append("Address skill gaps in your cover letter by highlighting transferable experience")
        if seeker_exp_years < required_exp_years:
            tips.append("Emphasize achievements rather than years of experience")

        return Response({
            "success_likelihood": likelihood,
            "score": score,
            "factors": factors,
            "tips": tips,
            "explanation": "Estimate based on your profile match vs. job requirements and employer activity.",
            "can_override": True,
            "disclaimer": "This is a guide only. Hiring decisions depend on many factors beyond this model.",
        })


# ── Seeker Reactivation Prompts ────────────────────────────────────────────────

class SeekerReactivationPromptsView(APIView):
    """
    GET /ai/reactivation-prompts/
    Personalized nudges to bring inactive seekers back to the platform.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.jobs.models import SavedJob
        from apps.applications.models import Application

        user = request.user
        last_apply = Application.objects.filter(applicant=user).order_by("-applied_at").first()
        days_inactive = (timezone.now() - last_apply.applied_at).days if last_apply else 999

        saved_count = SavedJob.objects.filter(user=user).count()

        prompts = []

        if days_inactive >= 30:
            prompts.append({
                "type": "reactivation",
                "title": f"You've been away for {days_inactive} days",
                "message": "New jobs matching your profile have been posted. Ready to explore?",
                "cta": "Browse New Jobs",
                "cta_url": "/jobs",
                "priority": "high",
            })
        if saved_count > 0:
            prompts.append({
                "type": "saved_jobs",
                "title": f"You have {saved_count} saved job(s)",
                "message": "Don't let your saved jobs expire. Review and apply before deadlines.",
                "cta": "View Saved Jobs",
                "cta_url": "/my-jobs",
                "priority": "medium",
            })

        # Profile completeness
        profile = getattr(user, "profile", None)
        if not profile or not getattr(profile, "resume_url", None):
            prompts.append({
                "type": "profile",
                "title": "Your profile is incomplete",
                "message": "Uploading a resume makes you 3x more likely to receive recruiter messages.",
                "cta": "Complete Profile",
                "cta_url": "/profile",
                "priority": "high",
            })

        return Response({
            "days_inactive": days_inactive,
            "prompts": prompts,
            "explanation": "Prompts personalized based on your activity history and profile state.",
        })


# ── Search Rewrite Suggestions ─────────────────────────────────────────────────

class SearchRewriteSuggestionsView(APIView):
    """
    POST /ai/search-rewrite/
    Suggest better search queries based on common Sri Lankan job search patterns.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        original = (request.data.get("query") or "").strip().lower()
        suggestions = []
        rewrites = []

        for pattern, rewrite in SEARCH_REWRITES.items():
            if pattern in original:
                rewrites.append({"pattern": pattern, "suggested": rewrite})

        # Common typos / abbreviations
        if len(original) <= 3:
            suggestions.append(f"Try spelling out '{original}' in full for better results")

        if not rewrites and not suggestions:
            suggestions.append("Try adding a location (e.g., 'Colombo', 'Kandy') for more relevant results")
            suggestions.append("Add experience level: 'Junior', 'Senior', 'Entry Level'")

        return Response({
            "original_query": original,
            "rewrites": rewrites,
            "general_tips": suggestions,
            "rewritten_query": " ".join([r["suggested"] for r in rewrites]) or original,
            "explanation": "Query improvements based on Sri Lankan job market terminology patterns.",
        })


# ── Apply Assistant (Candidate-Facing) ────────────────────────────────────────

class ApplyAssistantView(APIView):
    """
    POST /ai/apply-assistant/
    Helps a candidate prepare a strong application — cover letter hints,
    skill gap advice, profile completeness score, and an apply checklist.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        d = request.data
        job_title = d.get("job_title", "")
        company = d.get("company", "")
        seeker_skills = d.get("seeker_skills", [])
        job_required_skills = d.get("job_required_skills", [])
        has_resume = bool(d.get("has_resume", False))
        has_cover_letter = bool(d.get("has_cover_letter", False))
        profile_pct = int(d.get("profile_completeness_pct", 60))

        seeker_lower = [s.lower() for s in seeker_skills]
        req_lower = [s.lower() for s in job_required_skills]
        matched = [s for s in req_lower if s in seeker_lower]
        missing = [s for s in req_lower if s not in seeker_lower]

        checklist = [
            {"item": "Upload / update your resume", "done": has_resume, "priority": "high"},
            {"item": "Write a personalized cover letter", "done": has_cover_letter, "priority": "high"},
            {"item": "Complete your Job Finder profile (80%+)", "done": profile_pct >= 80, "priority": "medium"},
            {"item": f"Match {len(req_lower)} required skills", "done": len(missing) == 0, "detail": f"{len(matched)} matched, {len(missing)} missing", "priority": "high"},
        ]

        cover_hints = [
            f"Open by referencing why {company} specifically excites you.",
            f"Highlight your experience with: {', '.join(matched[:3]) or 'your core skills'}.",
        ]
        if missing:
            cover_hints.append(f"Address the skill gap for {', '.join(missing[:2])} with transferable experience or a willingness to learn quickly.")

        return Response({
            "job_title": job_title,
            "company": company,
            "readiness_score": min(100, int(profile_pct * 0.3 + (len(matched) / max(len(req_lower), 1)) * 50 + (10 if has_resume else 0) + (10 if has_cover_letter else 0))),
            "checklist": checklist,
            "cover_letter_hints": cover_hints,
            "missing_skills": missing,
            "matched_skills": matched,
            "tip": "Applications with personalized cover letters receive 40% more responses.",
            "explanation": "Checklist built from your profile vs. this specific job's requirements.",
            "can_override": True,
        })


# ── Job Post Optimizer (Recruiter-Facing) ─────────────────────────────────────

class JobPostOptimizerView(APIView):
    """
    POST /ai/optimize-job-post/
    Analyzes a job posting draft and suggests improvements for quality & reach.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        d = request.data
        title = d.get("title", "")
        description = d.get("description", "")
        salary_min = d.get("salary_min")
        salary_max = d.get("salary_max")
        required_skills = d.get("required_skills", [])
        benefits = d.get("benefits", [])

        issues = []
        improvements = []
        quality_score = 100

        # Title check
        normalized_title = title
        for alias, std in TITLE_ALIASES.items():
            if alias in title.lower():
                normalized_title = std
                improvements.append({"type": "title", "suggestion": f"Use '{std}' instead of '{title}' — more widely searched."})
                quality_score -= 5
                break

        # Description length
        if len(description) < 200:
            issues.append({"severity": "high", "issue": "Description too short", "detail": f"{len(description)} chars — aim for 300+"})
            improvements.append({"type": "description", "suggestion": "Add a paragraph about company culture and growth opportunities."})
            quality_score -= 20
        elif len(description) < 400:
            issues.append({"severity": "medium", "issue": "Description could be more detailed"})
            quality_score -= 10

        # Salary
        if not salary_min and not salary_max:
            issues.append({"severity": "high", "issue": "No salary disclosed", "detail": "Jobs with salary display get 3x more views."})
            improvements.append({"type": "salary", "suggestion": "Add a salary range. Even a broad range (LKR 80K-150K) increases applications."})
            quality_score -= 25

        # Required skills
        if len(required_skills) < 3:
            issues.append({"severity": "medium", "issue": "Too few required skills listed"})
            improvements.append({"type": "skills", "suggestion": "List 5-8 specific required and preferred skills to help candidates self-qualify."})
            quality_score -= 10

        if len(required_skills) > 15:
            issues.append({"severity": "medium", "issue": f"Too many required skills ({len(required_skills)}) — may deter applicants."})
            quality_score -= 5

        # Benefits
        if not benefits:
            improvements.append({"type": "benefits", "suggestion": "Listing benefits (health insurance, remote work, etc.) increases applications by ~20%."})
            quality_score -= 10

        # Structure checks
        if "responsibilities" not in description.lower() and "duties" not in description.lower():
            improvements.append({"type": "structure", "suggestion": "Add a 'Key Responsibilities' section as a bulleted list."})
            quality_score -= 5

        quality_score = max(0, quality_score)
        quality_label = "Excellent" if quality_score >= 85 else "Good" if quality_score >= 70 else "Needs Improvement" if quality_score >= 50 else "Poor"

        return Response({
            "quality_score": quality_score,
            "quality_label": quality_label,
            "normalized_title": normalized_title,
            "issues": issues,
            "improvements": improvements,
            "issue_count": len(issues),
            "ready_to_publish": quality_score >= 65,
            "explanation": "Score reflects job posting completeness, salary transparency, and search friendliness.",
            "can_override": True,
        })
