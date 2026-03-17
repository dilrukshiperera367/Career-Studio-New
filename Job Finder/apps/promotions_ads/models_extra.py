"""
Feature 10 — Recruitment Marketing Lite models.
Career site pages are managed in employers.CareerSitePage — here we add
TalentCommunityMember, SocialShareKit, and CampaignSourceAttribution.
"""
import uuid
from django.db import models
from django.conf import settings


class TalentCommunityMember(models.Model):
    """Talent community opt-in from a career page or referral landing."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE,
                                 related_name="talent_community")
    career_page_id = models.UUIDField(null=True, blank=True, help_text="ID of the employers.CareerSitePage")
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, default="")
    interested_roles = models.CharField(max_length=500, blank=True, default="")
    source = models.CharField(max_length=50, blank=True, default="", help_text="utm_source / referral code")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    is_existing_user = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_rm_talent_community"
        unique_together = [["employer", "email"]]
        ordering = ["-joined_at"]

    def __str__(self):
        return f"TalentCommunity: {self.email} -> {self.employer}"


class SocialShareKit(models.Model):
    """Pre-built social sharing assets for a job or campaign."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE,
                                 related_name="social_kits")
    job = models.ForeignKey("jobs.JobListing", on_delete=models.SET_NULL, null=True, blank=True,
                            related_name="social_kits")
    career_page_id = models.UUIDField(null=True, blank=True, help_text="ID of the employers.CareerSitePage")
    linkedin_text = models.TextField(blank=True, default="")
    twitter_text = models.TextField(blank=True, default="")
    whatsapp_text = models.TextField(blank=True, default="")
    facebook_text = models.TextField(blank=True, default="")
    share_image = models.ImageField(upload_to="social_kits/", null=True, blank=True)
    share_url = models.URLField(max_length=500, blank=True, default="")
    utm_campaign = models.CharField(max_length=100, blank=True, default="")
    click_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_rm_social_kits"
        ordering = ["-created_at"]

    def __str__(self):
        return f"SocialKit: {self.employer} - {self.utm_campaign}"


class CampaignSourceAttribution(models.Model):
    """Tracks where applies / page views / sign-ups came from (UTM source tracking)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE,
                                 related_name="source_attributions")
    event_type = models.CharField(max_length=20, choices=[
        ("page_view", "Page View"), ("apply", "Application"), ("talent_signup", "Talent Community Sign-up"),
        ("social_click", "Social Share Click"), ("email_open", "Email Open"),
    ])
    source = models.CharField(max_length=100, blank=True, default="")
    medium = models.CharField(max_length=100, blank=True, default="")
    campaign = models.CharField(max_length=100, blank=True, default="")
    content = models.CharField(max_length=100, blank=True, default="")
    job = models.ForeignKey("jobs.JobListing", on_delete=models.SET_NULL, null=True, blank=True)
    career_page_id = models.UUIDField(null=True, blank=True, help_text="ID of the employers.CareerSitePage")
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_rm_campaign_attributions"
        ordering = ["-recorded_at"]
        indexes = [
            models.Index(fields=["employer", "event_type", "-recorded_at"], name="idx_rm_csa_employer_event"),
        ]
