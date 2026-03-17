"""Recruitment Marketing app — Career sites, brand assets, job ad variants, UTM tracking, social posts."""

import uuid
from django.db import models


class CareerSite(models.Model):
    """A tenant's branded career site configuration."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("live", "Live"),
        ("maintenance", "Maintenance"),
        ("archived", "Archived"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="career_sites")
    name = models.CharField(max_length=255)
    subdomain = models.SlugField(max_length=100, unique=True)
    custom_domain = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    brand_color_primary = models.CharField(max_length=7, default="#000000")
    brand_color_secondary = models.CharField(max_length=7, default="#FFFFFF")
    logo_url = models.URLField(blank=True, default="")
    favicon_url = models.URLField(blank=True, default="")
    tagline = models.CharField(max_length=255, blank=True, default="")
    meta_title = models.CharField(max_length=255, blank=True, default="")
    meta_description = models.TextField(blank=True, default="")
    google_analytics_id = models.CharField(max_length=50, blank=True, default="")
    linkedin_insight_tag = models.CharField(max_length=100, blank=True, default="")
    custom_css = models.TextField(blank=True, default="")
    custom_js = models.TextField(blank=True, default="")
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "career_sites"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.subdomain})"


class CareerSitePage(models.Model):
    """A content page on the career site (e.g. About, Culture, Benefits)."""

    PAGE_TYPE_CHOICES = [
        ("home", "Home"),
        ("culture", "Culture"),
        ("benefits", "Benefits"),
        ("teams", "Teams"),
        ("diversity", "Diversity & Inclusion"),
        ("faq", "FAQ"),
        ("custom", "Custom"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="career_site_pages")
    site = models.ForeignKey(CareerSite, on_delete=models.CASCADE, related_name="pages")
    page_type = models.CharField(max_length=20, choices=PAGE_TYPE_CHOICES, default="custom")
    slug = models.SlugField(max_length=100)
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True, default="", help_text="Rich-text / HTML content (sanitized on save)")
    hero_image_url = models.URLField(blank=True, default="")
    is_published = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "career_site_pages"
        ordering = ["site", "display_order"]
        unique_together = [("site", "slug")]

    def __str__(self):
        return f"{self.title} ({self.site.name})"


class CampaignLanding(models.Model):
    """A targeted landing page for a specific recruiting campaign."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="campaign_landings")
    site = models.ForeignKey(CareerSite, on_delete=models.CASCADE, related_name="campaign_landings")
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=150)
    headline = models.CharField(max_length=255)
    body = models.TextField(blank=True, default="")
    cta_label = models.CharField(max_length=100, default="Apply Now")
    cta_job = models.ForeignKey(
        "jobs.Job", on_delete=models.SET_NULL, null=True, blank=True, related_name="campaign_landings"
    )
    is_active = models.BooleanField(default=True)
    view_count = models.IntegerField(default=0)
    conversion_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "campaign_landings"
        unique_together = [("site", "slug")]

    def __str__(self):
        return f"{self.name} ({self.site.name})"


class BrandAsset(models.Model):
    """A brand asset (image, video, PDF) used across career site and campaigns."""

    ASSET_TYPE_CHOICES = [
        ("image", "Image"),
        ("video", "Video"),
        ("document", "Document"),
        ("icon", "Icon"),
        ("template", "Template"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="brand_assets")
    name = models.CharField(max_length=255)
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPE_CHOICES, default="image")
    file_url = models.URLField()
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    mime_type = models.CharField(max_length=100, blank=True, default="")
    alt_text = models.CharField(max_length=255, blank=True, default="", help_text="WCAG 2.2 — alt text required")
    tags = models.JSONField(default=list, blank=True)
    uploaded_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="uploaded_brand_assets"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "brand_assets"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.get_asset_type_display()})"


class JobAdVariant(models.Model):
    """An A/B variant of a job advertisement copy."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("paused", "Paused"),
        ("ended", "Ended"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="job_ad_variants")
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="ad_variants")
    name = models.CharField(max_length=255)
    headline = models.CharField(max_length=255)
    body = models.TextField()
    channel = models.CharField(max_length=50, default="linkedin", help_text="e.g. linkedin, indeed, google_jobs")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    applications = models.IntegerField(default=0)
    spend_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="USD")
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "job_ad_variants"
        ordering = ["job", "-created_at"]

    def __str__(self):
        return f"{self.name} ({self.channel}) — {self.job.title}"


class UTMTracking(models.Model):
    """UTM parameter set associated with a job application or campaign click."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="utm_tracking")
    application = models.ForeignKey(
        "applications.Application", on_delete=models.CASCADE, null=True, blank=True,
        related_name="utm_tracking"
    )
    landing = models.ForeignKey(
        CampaignLanding, on_delete=models.SET_NULL, null=True, blank=True, related_name="utm_hits"
    )
    utm_source = models.CharField(max_length=255, blank=True, default="")
    utm_medium = models.CharField(max_length=255, blank=True, default="")
    utm_campaign = models.CharField(max_length=255, blank=True, default="")
    utm_term = models.CharField(max_length=255, blank=True, default="")
    utm_content = models.CharField(max_length=255, blank=True, default="")
    referrer_url = models.URLField(blank=True, default="")
    ip_hash = models.CharField(max_length=64, blank=True, default="", help_text="SHA-256 of IP for fraud detection")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "utm_tracking"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "utm_campaign"]),
            models.Index(fields=["utm_source", "utm_medium"]),
        ]

    def __str__(self):
        return f"{self.utm_source}/{self.utm_medium}/{self.utm_campaign}"


class SocialPost(models.Model):
    """A social media post promoting a job or employer brand."""

    CHANNEL_CHOICES = [
        ("linkedin", "LinkedIn"),
        ("twitter", "X / Twitter"),
        ("facebook", "Facebook"),
        ("instagram", "Instagram"),
        ("glassdoor", "Glassdoor"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("scheduled", "Scheduled"),
        ("published", "Published"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="social_posts")
    job = models.ForeignKey(
        "jobs.Job", on_delete=models.SET_NULL, null=True, blank=True, related_name="social_posts"
    )
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    content = models.TextField()
    image_url = models.URLField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    scheduled_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    external_post_id = models.CharField(max_length=255, blank=True, default="")
    impressions = models.IntegerField(default=0)
    likes = models.IntegerField(default=0)
    shares = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="social_posts"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "social_posts"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_channel_display()} post — {self.status}"


class TalentCommunitySignup(models.Model):
    """An expression of interest from a passive candidate who joined the talent community."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="talent_community_signups")
    email = models.EmailField()
    first_name = models.CharField(max_length=100, blank=True, default="")
    last_name = models.CharField(max_length=100, blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")
    areas_of_interest = models.JSONField(default=list, blank=True)
    linkedin_url = models.URLField(blank=True, default="")
    resume_url = models.URLField(blank=True, default="")
    utm_source = models.CharField(max_length=255, blank=True, default="")
    opted_in_at = models.DateTimeField(auto_now_add=True)
    opted_out_at = models.DateTimeField(null=True, blank=True)
    consent_recorded = models.BooleanField(default=False, help_text="GDPR/CCPA consent captured")

    class Meta:
        db_table = "talent_community_signups"
        ordering = ["-opted_in_at"]
        unique_together = [("tenant", "email")]

    def __str__(self):
        return f"{self.email} — {self.tenant.name}"


class FAQItem(models.Model):
    """A FAQ item displayed on the career site."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="faq_items")
    site = models.ForeignKey(CareerSite, on_delete=models.CASCADE, related_name="faq_items")
    question = models.CharField(max_length=500)
    answer = models.TextField()
    display_order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "faq_items"
        ordering = ["site", "display_order"]

    def __str__(self):
        return f"FAQ: {self.question[:60]}"


class RecruitingCalendarEvent(models.Model):
    """A public recruiting event (career fair, webinar, campus visit)."""

    EVENT_TYPE_CHOICES = [
        ("career_fair", "Career Fair"),
        ("webinar", "Webinar"),
        ("campus_visit", "Campus Visit"),
        ("open_day", "Open Day"),
        ("networking", "Networking"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="recruiting_events")
    title = models.CharField(max_length=255)
    event_type = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES, default="other")
    description = models.TextField(blank=True, default="")
    location = models.CharField(max_length=255, blank=True, default="")
    is_virtual = models.BooleanField(default=False)
    registration_url = models.URLField(blank=True, default="")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    is_published = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="recruiting_events"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "recruiting_calendar_events"
        ordering = ["starts_at"]

    def __str__(self):
        return f"{self.title} ({self.starts_at.date()})"


# ── Feature 2 extended models ─────────────────────────────────────────────────

class EVPBlock(models.Model):
    """Employer Value Proposition content block displayed on the career site."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="evp_blocks")
    site = models.ForeignKey(CareerSite, on_delete=models.CASCADE, related_name="evp_blocks")
    icon = models.CharField(max_length=100, blank=True, default="", help_text="Icon name or URL")
    headline = models.CharField(max_length=255)
    body = models.TextField(blank=True, default="")
    display_order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "evp_blocks"
        ordering = ["site", "display_order"]

    def __str__(self):
        return f"EVP: {self.headline} ({self.site.name})"


class EmployeeTestimonial(models.Model):
    """Employee story/testimonial shown on the career site."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="employee_testimonials")
    site = models.ForeignKey(CareerSite, on_delete=models.CASCADE, related_name="testimonials")
    name = models.CharField(max_length=200)
    role = models.CharField(max_length=200, blank=True, default="")
    department = models.CharField(max_length=200, blank=True, default="")
    quote = models.TextField()
    photo_url = models.URLField(blank=True, default="")
    video_url = models.URLField(blank=True, default="")
    is_featured = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "employee_testimonials"
        ordering = ["site", "-is_featured", "display_order"]

    def __str__(self):
        return f"{self.name} — {self.role}"


class RecruiterProfile(models.Model):
    """Recruiter or hiring manager public profile page."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="recruiter_profiles")
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="recruiter_profile"
    )
    bio = models.TextField(blank=True, default="")
    photo_url = models.URLField(blank=True, default="")
    linkedin_url = models.URLField(blank=True, default="")
    specialties = models.JSONField(default=list, blank=True, help_text="List of specialty strings")
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "recruiter_profiles"
        unique_together = [("tenant", "user")]

    def __str__(self):
        return f"Recruiter: {self.user}"


class DepartmentPage(models.Model):
    """Department-specific career landing page."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="department_pages")
    site = models.ForeignKey(CareerSite, on_delete=models.CASCADE, related_name="department_pages")
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=100)
    headline = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    hero_image_url = models.URLField(blank=True, default="")
    open_roles_count = models.IntegerField(default=0)
    is_published = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "department_pages"
        ordering = ["site", "display_order"]
        unique_together = [("site", "slug")]

    def __str__(self):
        return f"{self.name} ({self.site.name})"


class OfficePage(models.Model):
    """Office/location-specific career landing page."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="office_pages")
    site = models.ForeignKey(CareerSite, on_delete=models.CASCADE, related_name="office_pages")
    city = models.CharField(max_length=200)
    country = models.CharField(max_length=200)
    address = models.CharField(max_length=500, blank=True, default="")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    description = models.TextField(blank=True, default="")
    photos = models.JSONField(default=list, blank=True, help_text="List of photo URLs")
    perks = models.JSONField(default=list, blank=True, help_text="List of office-specific perks")
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "office_pages"
        ordering = ["site", "country", "city"]

    def __str__(self):
        return f"{self.city}, {self.country} ({self.site.name})"


class JobDistributionChannel(models.Model):
    """Job board / distribution channel configuration."""

    CHANNEL_TYPE_CHOICES = [
        ("job_board", "Job Board"),
        ("social", "Social Media"),
        ("aggregator", "Aggregator"),
        ("university", "University Portal"),
        ("diversity", "Diversity Board"),
        ("internal", "Internal Portal"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="job_distribution_channels")
    name = models.CharField(max_length=255)
    channel_type = models.CharField(max_length=30, choices=CHANNEL_TYPE_CHOICES, default="job_board")
    is_active = models.BooleanField(default=True)
    api_key = models.CharField(max_length=500, blank=True, default="", help_text="Encrypted at rest in production")
    last_sync_at = models.DateTimeField(null=True, blank=True)
    auto_post = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "job_distribution_channels"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_channel_type_display()})"


class JobDistributionPost(models.Model):
    """Tracks which jobs are posted to which distribution channels."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("posted", "Posted"),
        ("failed", "Failed"),
        ("removed", "Removed"),
        ("expired", "Expired"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="job_distribution_posts")
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="distribution_posts")
    channel = models.ForeignKey(JobDistributionChannel, on_delete=models.CASCADE, related_name="posts")
    external_id = models.CharField(max_length=255, blank=True, default="", help_text="ID on the external platform")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    posted_at = models.DateTimeField(null=True, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="USD")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "job_distribution_posts"
        ordering = ["-created_at"]
        unique_together = [("job", "channel")]

    def __str__(self):
        return f"{self.job} → {self.channel.name} ({self.status})"


class MarketingCalendarEntry(models.Model):
    """Recruitment marketing calendar entry."""

    ENTRY_TYPE_CHOICES = [
        ("social_post", "Social Post"),
        ("campaign", "Campaign"),
        ("event", "Event"),
        ("job_launch", "Job Launch"),
        ("content", "Content"),
        ("email", "Email"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("planned", "Planned"),
        ("in_progress", "In Progress"),
        ("published", "Published"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="marketing_calendar_entries")
    title = models.CharField(max_length=255)
    entry_type = models.CharField(max_length=30, choices=ENTRY_TYPE_CHOICES, default="other")
    channel = models.CharField(max_length=100, blank=True, default="")
    scheduled_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="planned")
    linked_job = models.ForeignKey(
        "jobs.Job", on_delete=models.SET_NULL, null=True, blank=True, related_name="marketing_calendar_entries"
    )
    notes = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="marketing_calendar_entries"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "marketing_calendar_entries"
        ordering = ["scheduled_date"]

    def __str__(self):
        return f"{self.title} ({self.scheduled_date})"


class BrandAnalyticsSnapshot(models.Model):
    """Daily talent brand analytics snapshot."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="brand_analytics_snapshots")
    site = models.ForeignKey(CareerSite, on_delete=models.CASCADE, related_name="analytics_snapshots")
    date = models.DateField()
    career_site_views = models.IntegerField(default=0)
    unique_visitors = models.IntegerField(default=0)
    applications_started = models.IntegerField(default=0)
    applications_completed = models.IntegerField(default=0)
    top_source = models.CharField(max_length=255, blank=True, default="")
    avg_time_on_site_seconds = models.IntegerField(default=0)
    bounce_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        db_table = "brand_analytics_snapshots"
        ordering = ["-date"]
        unique_together = [("site", "date")]

    def __str__(self):
        return f"{self.site.name} analytics — {self.date}"


class ChatbotFAQFlow(models.Model):
    """Chatbot / FAQ assistant configuration for a career site."""

    FLOW_TYPE_CHOICES = [
        ("faq", "FAQ Answer"),
        ("redirect", "Redirect to Page"),
        ("apply", "Prompt to Apply"),
        ("signup", "Talent Community Signup"),
        ("contact", "Contact Recruiter"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="chatbot_faq_flows")
    site = models.ForeignKey(CareerSite, on_delete=models.CASCADE, related_name="chatbot_flows")
    trigger_keywords = models.JSONField(default=list, blank=True, help_text="List of trigger keyword strings")
    response = models.TextField()
    flow_type = models.CharField(max_length=20, choices=FLOW_TYPE_CHOICES, default="faq")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chatbot_faq_flows"
        ordering = ["site"]

    def __str__(self):
        return f"Chatbot flow ({self.flow_type}) — {self.site.name}"


class DayInLifeSection(models.Model):
    """'Day in the life' media section displayed on the career site."""

    MEDIA_TYPE_CHOICES = [
        ("image", "Image"),
        ("video", "Video"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="day_in_life_sections")
    site = models.ForeignKey(CareerSite, on_delete=models.CASCADE, related_name="day_in_life_sections")
    department = models.CharField(max_length=200, blank=True, default="")
    title = models.CharField(max_length=255)
    media_url = models.URLField()
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES, default="image")
    caption = models.TextField(blank=True, default="")
    display_order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "day_in_life_sections"
        ordering = ["site", "display_order"]

    def __str__(self):
        return f"Day in life: {self.title} ({self.site.name})"
