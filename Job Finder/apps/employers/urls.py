"""Employers URL routing — list, detail, create, team, branding, follow, salary, TalentOS."""
from django.urls import path
from . import views
from . import talentos_views as tv

urlpatterns = [
    path("", views.EmployerListView.as_view(), name="employer-list"),
    path("create/", views.EmployerCreateView.as_view(), name="employer-create"),
    path("followed/", views.FollowedCompaniesView.as_view(), name="followed-companies"),
    path("<slug:slug>/", views.EmployerDetailView.as_view(), name="employer-detail"),
    path("<slug:slug>/update/", views.EmployerUpdateView.as_view(), name="employer-update"),
    path("<slug:slug>/team/", views.TeamListView.as_view(), name="team-list"),
    path("<slug:slug>/team/invite/", views.TeamInviteView.as_view(), name="team-invite"),
    path("<slug:slug>/team/<uuid:member_id>/remove/", views.TeamMemberRemoveView.as_view(), name="team-member-remove"),
    path("<slug:slug>/branding/", views.BrandingView.as_view(), name="employer-branding"),
    path("<slug:slug>/follow/", views.CompanyFollowToggleView.as_view(), name="company-follow"),
    path("<slug:slug>/is-following/", views.IsFollowingView.as_view(), name="company-is-following"),
    path("<slug:slug>/salary-reports/", views.SalaryReportListView.as_view(), name="salary-reports"),
    path("<slug:slug>/salary-reports/submit/", views.SalaryReportCreateView.as_view(), name="salary-report-create"),

    # ── TalentOS ──────────────────────────────────────────────────────────
    # JD Builder
    path("jd-builder/", tv.JobDescriptionListCreateView.as_view(), name="jd-builder-list"),
    path("jd-builder/<uuid:pk>/", tv.JobDescriptionDetailView.as_view(), name="jd-builder-detail"),

    # Interview Kits
    path("interview-kits/", tv.InterviewKitListCreateView.as_view(), name="interview-kit-list"),
    path("interview-kits/<uuid:pk>/", tv.InterviewKitDetailView.as_view(), name="interview-kit-detail"),
    path("interview-kits/<uuid:kit_id>/questions/", tv.InterviewQuestionListCreateView.as_view(), name="interview-question-list"),

    # Silver Medalists
    path("silver-medalists/", tv.SilverMedalistListCreateView.as_view(), name="silver-medalist-list"),
    path("silver-medalists/<uuid:pk>/", tv.SilverMedalistDetailView.as_view(), name="silver-medalist-detail"),

    # Referral Campaigns
    path("referral-campaigns/", tv.ReferralCampaignListCreateView.as_view(), name="referral-campaign-list"),
    path("referral-campaigns/<uuid:pk>/", tv.ReferralCampaignDetailView.as_view(), name="referral-campaign-detail"),
    path("referrals/", tv.ReferralCreateView.as_view(), name="referral-create"),

    # Recruiter CRM
    path("crm-contacts/", tv.RecruiterContactListCreateView.as_view(), name="crm-contact-list"),
    path("crm-contacts/<uuid:pk>/", tv.RecruiterContactDetailView.as_view(), name="crm-contact-detail"),

    # Career Site CMS
    path("career-site/", tv.CareerSitePageListCreateView.as_view(), name="career-site-list"),
    path("career-site/<uuid:pk>/", tv.CareerSitePageDetailView.as_view(), name="career-site-detail"),

    # Interview Debriefs
    path("debriefs/", tv.InterviewDebriefListCreateView.as_view(), name="debrief-list"),
    path("debriefs/<uuid:pk>/", tv.InterviewDebriefDetailView.as_view(), name="debrief-detail"),
    path("debriefs/<uuid:debrief_id>/feedback/", tv.DebriefFeedbackCreateView.as_view(), name="debrief-feedback-create"),
]
