"""Content app — Blog posts, career advice, FAQs, pages."""
import uuid
from django.db import models
from django.conf import settings


class BlogPost(models.Model):
    """Trilingual blog / career advice articles."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="blog_posts")
    slug = models.SlugField(max_length=300, unique=True)

    title = models.CharField(max_length=200)
    title_si = models.CharField(max_length=200, blank=True, default="")
    title_ta = models.CharField(max_length=200, blank=True, default="")
    excerpt = models.TextField(blank=True, default="")
    excerpt_si = models.TextField(blank=True, default="")
    excerpt_ta = models.TextField(blank=True, default="")
    body = models.TextField()
    body_si = models.TextField(blank=True, default="")
    body_ta = models.TextField(blank=True, default="")

    cover_image = models.ImageField(upload_to="blog_covers/", null=True, blank=True)
    category = models.CharField(max_length=50, choices=[
        ("career_advice", "Career Advice"),
        ("interview_tips", "Interview Tips"),
        ("salary_guide", "Salary Guide"),
        ("industry_news", "Industry News"),
        ("resume_guide", "Resume Guide"),
        ("foreign_employment", "Foreign Employment"),
    ])
    tags = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    view_count = models.IntegerField(default=0)

    meta_title = models.CharField(max_length=70, blank=True, default="")
    meta_description = models.CharField(max_length=160, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_blog_posts"
        ordering = ["-published_at"]


class FAQ(models.Model):
    """Frequently asked questions — trilingual."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.CharField(max_length=30, choices=[
        ("seekers", "For Seekers"), ("employers", "For Employers"),
        ("account", "Account"), ("payments", "Payments"), ("general", "General"),
    ])
    question = models.TextField()
    question_si = models.TextField(blank=True, default="")
    question_ta = models.TextField(blank=True, default="")
    answer = models.TextField()
    answer_si = models.TextField(blank=True, default="")
    answer_ta = models.TextField(blank=True, default="")
    sort_order = models.IntegerField(default=0)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_faqs"
        ordering = ["category", "sort_order"]


class StaticPage(models.Model):
    """CMS-managed static pages (about, terms, privacy, etc.)."""
    slug = models.SlugField(max_length=100, unique=True, primary_key=True)
    title = models.CharField(max_length=200)
    title_si = models.CharField(max_length=200, blank=True, default="")
    title_ta = models.CharField(max_length=200, blank=True, default="")
    body = models.TextField()
    body_si = models.TextField(blank=True, default="")
    body_ta = models.TextField(blank=True, default="")
    is_published = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_static_pages"
