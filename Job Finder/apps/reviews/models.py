"""Reviews app — Company reviews and ratings by employees/applicants."""
import uuid
from django.db import models
from django.conf import settings


class CompanyReview(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        FLAGGED = "flagged", "Flagged"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE, related_name="reviews")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="reviews_given")
    is_anonymous = models.BooleanField(default=True)
    relationship = models.CharField(max_length=20, choices=[
        ("current_employee", "Current Employee"),
        ("former_employee", "Former Employee"),
        ("applicant", "Applicant"),
        ("intern", "Intern"),
    ])

    overall_rating = models.IntegerField()
    work_life_balance = models.IntegerField(null=True, blank=True)
    career_growth = models.IntegerField(null=True, blank=True)
    compensation = models.IntegerField(null=True, blank=True)
    management = models.IntegerField(null=True, blank=True)
    culture = models.IntegerField(null=True, blank=True)

    title = models.CharField(max_length=200)
    pros = models.TextField()
    cons = models.TextField()
    advice_to_management = models.TextField(blank=True, default="")

    job_title = models.CharField(max_length=100, blank=True, default="")
    employment_duration_months = models.IntegerField(null=True, blank=True)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    helpful_count = models.IntegerField(default=0)
    report_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_company_reviews"
        ordering = ["-created_at"]
        unique_together = ["employer", "reviewer"]


class ReviewHelpful(models.Model):
    review = models.ForeignKey(CompanyReview, on_delete=models.CASCADE, related_name="helpful_votes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_review_helpful"
        unique_together = ["review", "user"]


class EmployerReviewResponse(models.Model):
    """Official employer response to a review. #316"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    review = models.OneToOneField(CompanyReview, on_delete=models.CASCADE, related_name="employer_response")
    responder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    response_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_review_responses"


# ── Marketplace Enhancements ────────────────────────────────────────────────

class InterviewReview(models.Model):
    """Interview experience review by an applicant."""
    class ExperienceType(models.TextChoices):
        POSITIVE = "positive", "Positive"
        NEUTRAL = "neutral", "Neutral"
        NEGATIVE = "negative", "Negative"

    class InterviewType(models.TextChoices):
        PHONE = "phone", "Phone Screen"
        VIDEO = "video", "Video Interview"
        IN_PERSON = "in_person", "In Person"
        TECHNICAL = "technical", "Technical Test"
        PANEL = "panel", "Panel Interview"
        GROUP = "group", "Group Assessment"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE,
                                 related_name="interview_reviews")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    job_title = models.CharField(max_length=200, blank=True, default="")
    is_anonymous = models.BooleanField(default=True)
    experience = models.CharField(max_length=10, choices=ExperienceType.choices)
    difficulty = models.IntegerField(default=3, help_text="1=Very Easy to 5=Very Hard")
    interview_type = models.CharField(max_length=15, choices=InterviewType.choices, blank=True, default="")
    num_rounds = models.IntegerField(null=True, blank=True)
    duration_days = models.IntegerField(null=True, blank=True, help_text="Process length in days")
    got_offer = models.BooleanField(null=True, blank=True)
    description = models.TextField(blank=True, default="")
    questions_asked = models.JSONField(default=list, help_text="List of interview questions remembered")
    status = models.CharField(max_length=10, choices=[("pending", "Pending"), ("approved", "Approved"),
                                                       ("rejected", "Rejected")], default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_interview_reviews"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Interview Review: {self.employer} by {self.reviewer}"


class BenefitsReview(models.Model):
    """Benefits and perks rating by employee."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE,
                                 related_name="benefits_reviews")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    is_anonymous = models.BooleanField(default=True)
    overall_benefits_rating = models.IntegerField(default=3, help_text="1-5 star rating")
    health_insurance = models.BooleanField(null=True, blank=True)
    annual_leave_days = models.IntegerField(null=True, blank=True)
    remote_work_option = models.BooleanField(null=True, blank=True)
    performance_bonus = models.BooleanField(null=True, blank=True)
    training_allowance = models.BooleanField(null=True, blank=True)
    transport_allowance = models.BooleanField(null=True, blank=True)
    meal_allowance = models.BooleanField(null=True, blank=True)
    pros = models.TextField(blank=True, default="")
    cons = models.TextField(blank=True, default="")
    status = models.CharField(max_length=10, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_benefits_reviews"
        ordering = ["-created_at"]


class SalaryReview(models.Model):
    """Verified salary review submission by an employee."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE,
                                 related_name="salary_reviews")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    is_anonymous = models.BooleanField(default=True)
    job_title = models.CharField(max_length=200)
    experience_years = models.IntegerField(null=True, blank=True)
    base_salary_lkr = models.IntegerField(help_text="Monthly base salary in LKR")
    total_comp_lkr = models.IntegerField(null=True, blank=True, help_text="Total compensation incl. bonus/allowances")
    satisfaction_rating = models.IntegerField(default=3, help_text="1=Very Dissatisfied to 5=Very Satisfied")
    notes = models.TextField(blank=True, default="")
    is_verified = models.BooleanField(default=False)
    status = models.CharField(max_length=10, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_salary_reviews"
        ordering = ["-created_at"]

    def __str__(self):
        return f"SalaryReview: {self.employer} — {self.job_title} LKR {self.base_salary_lkr}"

