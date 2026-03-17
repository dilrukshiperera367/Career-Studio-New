"""Candidates URL routing — profile, resumes, skills, experience, education, certs, languages, Feature 4."""
from django.urls import path
from . import views
from . import views_extra

urlpatterns = [
    # ── Profile ──────────────────────────────────────────────────────────────
    path("profile/", views.SeekerProfileView.as_view(), name="seeker-profile"),
    path("profile/preview/", views.SeekerProfilePreviewView.as_view(), name="seeker-profile-preview"),
    path("profile/completeness/", views.ProfileCompletenessView.as_view(), name="seeker-profile-completeness"),
    path("profile/wizard/", views.WizardStepUpdateView.as_view(), name="seeker-profile-wizard"),
    path("profile/<uuid:pk>/", views.SeekerProfilePublicView.as_view(), name="seeker-profile-public-uuid"),

    # ── Feature 4: Identity 2.0 ───────────────────────────────────────────────
    path("preferences/", views_extra.JobPreferencesView.as_view(), name="seeker-preferences"),
    path("profile/public/<slug:slug>/", views_extra.PublicProfileBySlugView.as_view(), name="seeker-profile-public-slug"),
    path("profile/slug/", views_extra.PublicProfileSlugUpdateView.as_view(), name="seeker-profile-slug-update"),
    path("timeline/", views_extra.ActivityTimelineView.as_view(), name="seeker-timeline"),
    path("badges/", views_extra.ProfileBadgeView.as_view(), name="seeker-badges"),
    path("trust-score/", views_extra.TrustScoreView.as_view(), name="seeker-trust-score"),
    path("application-profile/", views_extra.ApplicationProfileView.as_view(), name="seeker-application-profile"),
    path("milestones/", views_extra.ProfileMilestonesView.as_view(), name="seeker-milestones"),
    path("import/careeros/", views_extra.CareerOSImportView.as_view(), name="seeker-import-careeros"),

    # ── Resumes ───────────────────────────────────────────────────────────────
    path("resumes/", views.ResumeListCreateView.as_view(), name="resume-list"),
    path("resumes/<uuid:pk>/", views.ResumeDetailView.as_view(), name="resume-detail"),
    path("resumes/<uuid:pk>/set-primary/", views.ResumeSetPrimaryView.as_view(), name="resume-set-primary"),
    path("resumes/<uuid:pk>/refresh/", views.ResumeRefreshView.as_view(), name="resume-refresh"),
    path("resumes/<uuid:pk>/retry-parse/", views.ResumeRetryParseView.as_view(), name="resume-retry-parse"),

    # ── Skills ────────────────────────────────────────────────────────────────
    path("skills/", views.SkillListCreateView.as_view(), name="skill-list"),
    path("skills/<int:pk>/", views.SkillDetailView.as_view(), name="skill-detail"),

    # ── Experience ────────────────────────────────────────────────────────────
    path("experiences/", views.ExperienceListCreateView.as_view(), name="experience-list"),
    path("experiences/<uuid:pk>/", views.ExperienceDetailView.as_view(), name="experience-detail"),

    # ── Education ─────────────────────────────────────────────────────────────
    path("education/", views.EducationListCreateView.as_view(), name="education-list"),
    path("education/<uuid:pk>/", views.EducationDetailView.as_view(), name="education-detail"),

    # ── Certifications ────────────────────────────────────────────────────────
    path("certifications/", views.CertificationListCreateView.as_view(), name="certification-list"),
    path("certifications/<uuid:pk>/", views.CertificationDetailView.as_view(), name="certification-detail"),

    # ── Languages ─────────────────────────────────────────────────────────────
    path("languages/", views.LanguageListCreateView.as_view(), name="language-list"),
    path("languages/<int:pk>/", views.LanguageDetailView.as_view(), name="language-detail"),

    # ── References ────────────────────────────────────────────────────────────
    path("references/", views.ReferenceListCreateView.as_view(), name="reference-list"),
    path("references/<uuid:pk>/", views.ReferenceDetailView.as_view(), name="reference-detail"),

    # ── Portfolio ─────────────────────────────────────────────────────────────
    path("portfolio/", views.PortfolioListCreateView.as_view(), name="portfolio-list"),
    path("portfolio/<uuid:pk>/", views.PortfolioDetailView.as_view(), name="portfolio-detail"),
]
