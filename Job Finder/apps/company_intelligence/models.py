"""Company Intelligence — rich company profiles, offices, benefits, Q&A, hiring activity, comparison."""
import uuid
from django.db import models
from django.conf import settings


class CompanyOfficeLocation(models.Model):
    """Physical office / location of an employer."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE,
                                 related_name="office_locations")
    name = models.CharField(max_length=200, help_text="e.g. Colombo HQ, Kandy Branch")
    address = models.TextField(blank=True, default="")
    district = models.ForeignKey("taxonomy.District", on_delete=models.SET_NULL, null=True, blank=True)
    city = models.CharField(max_length=100, blank=True, default="")
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    is_headquarters = models.BooleanField(default=False)
    employee_count = models.IntegerField(null=True, blank=True)
    active_job_count = models.IntegerField(default=0)
    photos = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_company_office_locations"
        ordering = ["-is_headquarters", "name"]

    def __str__(self):
        return f"{self.employer} — {self.name}"


class CompanyBenefit(models.Model):
    """Structured company benefits listing."""
    class BenefitCategory(models.TextChoices):
        HEALTH = "health", "Health & Wellness"
        FINANCIAL = "financial", "Financial"
        WORK_LIFE = "work_life", "Work-Life Balance"
        LEARNING = "learning", "Learning & Development"
        PERKS = "perks", "Perks & Extras"
        LEAVE = "leave", "Leave & Time Off"
        TRANSPORT = "transport", "Transport"
        FOOD = "food", "Food & Meals"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE,
                                 related_name="structured_benefits")
    category = models.CharField(max_length=15, choices=BenefitCategory.choices)
    label = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    is_highlighted = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "jf_company_benefits"
        ordering = ["-is_highlighted", "sort_order"]

    def __str__(self):
        return f"{self.employer} — {self.label}"


class CompanyQnA(models.Model):
    """Community Q&A on a company page."""
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE, related_name="qna_items")
    asked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                 related_name="company_questions")
    question = models.TextField()
    answer = models.TextField(blank=True, default="")
    answered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="company_answers")
    answered_at = models.DateTimeField(null=True, blank=True)
    is_employer_answer = models.BooleanField(default=False)
    helpful_count = models.IntegerField(default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_company_qna"
        ordering = ["-helpful_count", "-created_at"]

    def __str__(self):
        return f"Q&A: {self.employer} — {self.question[:60]}"


class HiringActivityIndicator(models.Model):
    """Weekly snapshot of employer hiring activity signals."""
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE,
                                 related_name="hiring_activity")
    week_start = models.DateField()
    new_jobs_posted = models.IntegerField(default=0)
    jobs_filled = models.IntegerField(default=0)
    avg_response_hours = models.FloatField(null=True, blank=True)
    avg_time_to_hire_days = models.FloatField(null=True, blank=True)
    open_positions = models.IntegerField(default=0)
    is_actively_hiring = models.BooleanField(default=False)

    class Meta:
        db_table = "jf_hiring_activity_indicators"
        unique_together = ["employer", "week_start"]
        ordering = ["-week_start"]

    def __str__(self):
        return f"{self.employer} hiring activity week {self.week_start}"


class EmployerComparison(models.Model):
    """Pre-computed comparison metadata between two employers (for compare tool)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer_a = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE,
                                   related_name="comparisons_as_a")
    employer_b = models.ForeignKey("employers.EmployerAccount", on_delete=models.CASCADE,
                                   related_name="comparisons_as_b")
    similarity_score = models.FloatField(default=0.0)
    comparison_data = models.JSONField(default=dict)
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_employer_comparisons"
        unique_together = ["employer_a", "employer_b"]

    def __str__(self):
        return f"Compare: {self.employer_a} vs {self.employer_b}"
