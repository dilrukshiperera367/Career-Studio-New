"""Candidates views — all new Feature 4 views added after the existing views."""
from django.utils import timezone
from django.utils.text import slugify
from django.db import transaction
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.shared.permissions import IsSeeker
from .models import (
    SeekerProfile,
    SeekerBadge,
    SeekerActivityTimeline,
    ApplicationProfile,
)


def get_or_create_profile(user):
    return SeekerProfile.objects.get_or_create(user=user)[0]


def log_event(seeker: SeekerProfile, event_type: str, title: str, description: str = "", metadata: dict = None):
    """Helper to log an activity timeline event."""
    try:
        SeekerActivityTimeline.objects.create(
            seeker=seeker,
            event_type=event_type,
            title=title,
            description=description,
            metadata=metadata or {},
        )
    except Exception:
        pass


def award_badge(seeker: SeekerProfile, badge_type: str, note: str = ""):
    """Award a badge if not already awarded."""
    try:
        SeekerBadge.objects.get_or_create(
            seeker=seeker,
            badge_type=badge_type,
            defaults={"note": note},
        )
    except Exception:
        pass


def compute_trust_score(seeker: SeekerProfile) -> int:
    """
    Compute a 0-100 trust score based on profile quality signals.
    Higher = more trustworthy / more searchable.
    """
    score = 20  # Base score

    # Identity verification
    if seeker.nic_number:
        score += 10
    if seeker.avatar:
        score += 5

    # Profile completeness
    completeness = getattr(seeker, "profile_completeness", 0)
    score += int(completeness * 0.3)  # Max 30 pts from completeness

    # Social links (credibility signals)
    if seeker.linkedin_url:
        score += 5
    if seeker.github_url:
        score += 3
    if seeker.portfolio_url:
        score += 2

    # Engagement bonuses
    if seeker.resumes.filter(is_primary=True).exists():
        score += 5
    if seeker.skills.count() >= 5:
        score += 5
    if seeker.experiences.exists():
        score += 5
    if seeker.certifications.exists():
        score += 5
    if seeker.languages.count() >= 2:
        score += 3

    return min(score, 100)


# ── Job Preferences API ───────────────────────────────────────────────────────

class JobPreferencesView(APIView):
    """
    GET/PATCH the seeker's job preferences:
    target titles, industries, salary, work auth, shift, commute radius,
    notice period, relocation, open_to_work, recruiter_visibility.
    """
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get(self, request):
        profile = get_or_create_profile(request.user)
        data = {
            "target_titles": profile.desired_job_types,  # repurposed list
            "desired_job_types": profile.desired_job_types,
            "desired_industries": profile.desired_industries,
            "desired_locations": profile.desired_locations,
            "min_salary_expected": profile.min_salary_expected,
            "max_salary_expected": profile.max_salary_expected,
            "willing_to_relocate": profile.willing_to_relocate,
            "relocation_districts": profile.relocation_districts,
            "open_to_remote": profile.open_to_remote,
            "open_to_work": profile.open_to_work,
            "recruiter_visibility": profile.recruiter_visibility,
            "commute_radius_km": profile.commute_radius_km,
            "notice_period_weeks": profile.notice_period_weeks,
            "preferred_shift": profile.preferred_shift,
            "work_auth": profile.work_auth,
            "job_search_status": profile.job_search_status,
            "available_from": profile.available_from,
            "profile_visibility": profile.profile_visibility,
            "public_profile_slug": profile.public_profile_slug,
            "trust_score": profile.trust_score,
        }
        return Response(data)

    def patch(self, request):
        profile = get_or_create_profile(request.user)
        allowed_fields = [
            "desired_job_types", "desired_industries", "desired_locations",
            "min_salary_expected", "max_salary_expected",
            "willing_to_relocate", "relocation_districts", "open_to_remote",
            "open_to_work", "recruiter_visibility", "commute_radius_km",
            "notice_period_weeks", "preferred_shift", "work_auth",
            "job_search_status", "available_from", "profile_visibility",
        ]
        changed = []
        for field in allowed_fields:
            if field in request.data:
                setattr(profile, field, request.data[field])
                changed.append(field)

        if changed:
            profile.save(update_fields=changed + ["updated_at"])
            log_event(
                profile, "preferences_updated",
                "Preferences updated",
                f"Fields changed: {', '.join(changed)[:200]}",
            )

            # Award Open To Work badge
            if profile.open_to_work:
                award_badge(profile, "open_to_work", "Set Open to Work status")

        return Response({"detail": "Preferences saved.", "changed": changed})


# ── Trust Score View ──────────────────────────────────────────────────────────

class TrustScoreView(APIView):
    """Compute and return (and persist) the seeker's trust score."""
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get(self, request):
        profile = get_or_create_profile(request.user)
        score = compute_trust_score(profile)
        profile.trust_score = score
        profile.save(update_fields=["trust_score", "updated_at"])

        # Award trusted badge
        if score >= 80:
            award_badge(profile, "trusted", "Achieved trust score ≥ 80")

        breakdown = {
            "score": score,
            "level": "high" if score >= 75 else "medium" if score >= 50 else "low",
            "label": "Highly Trusted" if score >= 75 else "Trusted" if score >= 50 else "Building Trust",
            "tips": [],
        }
        if not profile.nic_number:
            breakdown["tips"].append("Add your NIC number (+10)")
        if not profile.avatar:
            breakdown["tips"].append("Upload a profile photo (+5)")
        if not profile.linkedin_url:
            breakdown["tips"].append("Add your LinkedIn profile (+5)")
        if not profile.certifications.exists():
            breakdown["tips"].append("Add certifications (+5)")

        return Response(breakdown)


# ── Public Profile by Slug ────────────────────────────────────────────────────

class PublicProfileBySlugView(APIView):
    """
    GET /candidates/profile/public/<slug>/
    Returns a public seeker profile, respecting visibility controls.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        try:
            profile = SeekerProfile.objects.select_related(
                "district", "user"
            ).prefetch_related(
                "skills__skill", "education", "experiences", "certifications", "languages", "badges"
            ).get(public_profile_slug=slug)
        except SeekerProfile.DoesNotExist:
            return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)

        if profile.profile_visibility == "hidden":
            return Response({"detail": "This profile is private."}, status=status.HTTP_403_FORBIDDEN)

        anonymous = profile.profile_visibility == "anonymous"

        data = {
            "slug": profile.public_profile_slug,
            "name": f"{profile.first_name} {profile.last_name[0]}." if anonymous else f"{profile.first_name} {profile.last_name}",
            "headline": profile.headline,
            "bio": profile.bio if not anonymous else None,
            "avatar": (profile.avatar.url if profile.avatar else None) if not anonymous else None,
            "district": str(profile.district) if profile.district else None,
            "open_to_work": profile.open_to_work,
            "job_search_status": profile.job_search_status,
            "profile_completeness": profile.profile_completeness,
            "trust_score": profile.trust_score,
            "linkedin_url": profile.linkedin_url if not anonymous else None,
            "github_url": profile.github_url if not anonymous else None,
            "portfolio_url": profile.portfolio_url if not anonymous else None,
            "skills": [
                {"name": s.skill.name_en, "proficiency": s.proficiency, "endorsed_count": s.endorsed_count}
                for s in profile.skills.all()[:15]
            ],
            "education": [
                {"institution": e.institution, "level": e.level, "field_of_study": e.field_of_study,
                 "start_year": e.start_year, "end_year": e.end_year, "is_current": e.is_current}
                for e in profile.education.all()[:5]
            ],
            "experiences": [
                {"company_name": e.company_name, "title": e.title, "start_date": str(e.start_date),
                 "end_date": str(e.end_date) if e.end_date else None, "is_current": e.is_current}
                for e in profile.experiences.all()[:5]
            ] if not anonymous else [],
            "badges": [
                {"badge_type": b.badge_type, "label": b.get_badge_type_display(), "awarded_at": b.awarded_at}
                for b in profile.badges.all()
            ],
        }
        return Response(data)


class PublicProfileSlugUpdateView(APIView):
    """
    POST /candidates/profile/slug/
    Set or regenerate the public profile slug.
    """
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def post(self, request):
        profile = get_or_create_profile(request.user)
        preferred = request.data.get("slug", "")

        if preferred:
            base = slugify(preferred)[:100]
        else:
            base = slugify(f"{profile.first_name} {profile.last_name}")[:100]

        # Uniquify
        slug = base
        counter = 1
        while SeekerProfile.objects.filter(public_profile_slug=slug).exclude(pk=profile.pk).exists():
            slug = f"{base}-{counter}"
            counter += 1

        profile.public_profile_slug = slug
        profile.save(update_fields=["public_profile_slug", "updated_at"])
        return Response({"slug": slug, "url": f"https://jobfinder.lk/en/talent/{slug}"})


# ── Activity Timeline View ────────────────────────────────────────────────────

class ActivityTimelineView(APIView):
    """GET the seeker's activity timeline (last 50 events)."""
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get(self, request):
        profile = get_or_create_profile(request.user)
        events = SeekerActivityTimeline.objects.filter(seeker=profile)[:50]
        return Response([
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "label": e.get_event_type_display(),
                "title": e.title,
                "description": e.description,
                "metadata": e.metadata,
                "created_at": e.created_at,
            }
            for e in events
        ])


# ── Profile Badges ────────────────────────────────────────────────────────────

class ProfileBadgeView(APIView):
    """GET the seeker's earned badges."""
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get(self, request):
        profile = get_or_create_profile(request.user)
        badges = SeekerBadge.objects.filter(seeker=profile)
        return Response([
            {
                "badge_type": b.badge_type,
                "label": b.get_badge_type_display(),
                "awarded_at": b.awarded_at,
                "note": b.note,
            }
            for b in badges
        ])


# ── Application Profile (Reusable) ────────────────────────────────────────────

class ApplicationProfileView(APIView):
    """GET/PATCH the seeker's reusable one-click application profile."""
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def get(self, request):
        seeker = get_or_create_profile(request.user)
        ap, _ = ApplicationProfile.objects.get_or_create(seeker=seeker)
        return Response({
            "full_name_override": ap.full_name_override,
            "phone_override": ap.phone_override,
            "email_override": ap.email_override,
            "cover_letter_template": ap.cover_letter_template,
            "expected_salary": ap.expected_salary,
            "salary_currency": ap.salary_currency,
            "work_auth_statement": ap.work_auth_statement,
            "linkedin_url": ap.linkedin_url,
            "portfolio_url": ap.portfolio_url,
            "github_url": ap.github_url,
            "additional_questions": ap.additional_questions,
            "updated_at": ap.updated_at,
        })

    def patch(self, request):
        seeker = get_or_create_profile(request.user)
        ap, _ = ApplicationProfile.objects.get_or_create(seeker=seeker)
        allowed = [
            "full_name_override", "phone_override", "email_override",
            "cover_letter_template", "expected_salary", "salary_currency",
            "work_auth_statement", "linkedin_url", "portfolio_url", "github_url",
            "additional_questions",
        ]
        for field in allowed:
            if field in request.data:
                setattr(ap, field, request.data[field])
        ap.save()
        log_event(seeker, "preferences_updated", "Application profile updated")
        return Response({"detail": "Application profile saved."})


# ── CareerOS Import View ──────────────────────────────────────────────────────

class CareerOSImportView(APIView):
    """
    POST /candidates/import/careeros/
    Accepts JSON payload from CareerOS and merges into the seeker's profile.
    Supports: personal info, education, experience, skills, languages.
    """
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    def post(self, request):
        from apps.taxonomy.models import Skill as TaxSkill, District
        from apps.candidates.models import (
            SeekerSkill, SeekerExperience, SeekerEducation, SeekerLanguage, SeekerCertification
        )

        seeker = get_or_create_profile(request.user)
        payload = request.data
        imported = []

        with transaction.atomic():
            # Personal info
            personal = payload.get("personal", {})
            if personal:
                for field in ["first_name", "last_name", "headline", "bio",
                               "linkedin_url", "github_url", "portfolio_url", "phone_secondary"]:
                    if personal.get(field):
                        setattr(seeker, field, personal[field])
                imported.append("personal_info")

            # Skills
            for skill_data in payload.get("skills", []):
                skill_name = skill_data.get("name", "").strip()
                if not skill_name:
                    continue
                tax_skill, _ = TaxSkill.objects.get_or_create(
                    slug=slugify(skill_name),
                    defaults={"name_en": skill_name, "name_si": skill_name, "name_ta": skill_name},
                )
                SeekerSkill.objects.get_or_create(
                    seeker=seeker, skill=tax_skill,
                    defaults={
                        "proficiency": skill_data.get("proficiency", "intermediate"),
                        "years_used": skill_data.get("years", None),
                    },
                )
            if payload.get("skills"):
                imported.append("skills")

            # Experiences
            for exp in payload.get("experiences", []):
                if exp.get("company") and exp.get("title"):
                    SeekerExperience.objects.get_or_create(
                        seeker=seeker,
                        company_name=exp["company"],
                        title=exp["title"],
                        start_date=exp.get("start_date", "2020-01-01"),
                        defaults={
                            "description": exp.get("description", ""),
                            "is_current": exp.get("is_current", False),
                            "end_date": exp.get("end_date") or None,
                            "employment_type": exp.get("type", "full_time"),
                        },
                    )
            if payload.get("experiences"):
                imported.append("experiences")

            # Education
            for edu in payload.get("education", []):
                if edu.get("institution"):
                    SeekerEducation.objects.get_or_create(
                        seeker=seeker,
                        institution=edu["institution"],
                        level=edu.get("level", "bachelors"),
                        start_year=edu.get("start_year", 2000),
                        defaults={
                            "field_of_study": edu.get("field_of_study", ""),
                            "is_current": edu.get("is_current", False),
                            "end_year": edu.get("end_year") or None,
                        },
                    )
            if payload.get("education"):
                imported.append("education")

            # Languages
            for lang in payload.get("languages", []):
                if lang.get("language"):
                    SeekerLanguage.objects.get_or_create(
                        seeker=seeker,
                        language=lang["language"],
                        defaults={"proficiency": lang.get("proficiency", "professional")},
                    )
            if payload.get("languages"):
                imported.append("languages")

            # Save profile updates
            seeker.save()

            # Recompute completeness
            seeker.compute_completeness()
            seeker.save(update_fields=["profile_completeness", "updated_at"])

        # Log event + award badge
        log_event(
            seeker, "careeros_import",
            "CareerOS profile imported",
            f"Imported: {', '.join(imported)}",
            {"imported_sections": imported},
        )
        award_badge(seeker, "careeros_import", "Imported profile from CareerOS")

        return Response({
            "detail": "CareerOS import complete.",
            "imported_sections": imported,
            "profile_completeness": seeker.profile_completeness,
        }, status=status.HTTP_200_OK)


# ── Completeness Milestones View ──────────────────────────────────────────────

class ProfileMilestonesView(APIView):
    """Returns profile completeness milestones and current badge checkpoints."""
    permission_classes = [permissions.IsAuthenticated, IsSeeker]

    MILESTONES = [
        {"pct": 20, "label": "Getting Started", "badge": None},
        {"pct": 40, "label": "Basic Profile", "badge": None},
        {"pct": 60, "label": "Good Standing", "badge": None},
        {"pct": 80, "label": "Star Candidate", "badge": "top_applicant"},
        {"pct": 100, "label": "Profile Complete", "badge": "profile_complete"},
    ]

    def get(self, request):
        seeker = get_or_create_profile(request.user)
        score = seeker.compute_completeness()
        seeker.save(update_fields=["profile_completeness", "updated_at"])
        earned_badges = set(SeekerBadge.objects.filter(seeker=seeker).values_list("badge_type", flat=True))

        milestones_out = []
        for m in self.MILESTONES:
            achieved = score >= m["pct"]
            if achieved and m["badge"]:
                award_badge(seeker, m["badge"], f"Reached {m['pct']}% profile completeness")
            milestones_out.append({
                **m,
                "achieved": achieved,
            })

        return Response({
            "profile_completeness": score,
            "milestones": milestones_out,
            "badges_earned": list(earned_badges),
            "suggestions": seeker.get_suggestions(),
        })
