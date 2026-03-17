"""Salary Intelligence — salary estimates, benchmarks, trends, cost-of-living, submissions."""
import uuid
from django.db import models
from django.conf import settings


class SalaryEstimate(models.Model):
    """Aggregated salary estimate by title + district, derived from reports and job listings."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    normalized_title = models.CharField(max_length=200, help_text="Normalized/canonical job title")
    district = models.ForeignKey("taxonomy.District", on_delete=models.SET_NULL, null=True, blank=True)
    industry = models.ForeignKey("taxonomy.Industry", on_delete=models.SET_NULL, null=True, blank=True)
    experience_level = models.CharField(max_length=10, blank=True, default="")

    salary_p10_lkr = models.IntegerField(null=True, blank=True)
    salary_p25_lkr = models.IntegerField(null=True, blank=True)
    salary_median_lkr = models.IntegerField(null=True, blank=True)
    salary_p75_lkr = models.IntegerField(null=True, blank=True)
    salary_p90_lkr = models.IntegerField(null=True, blank=True)

    sample_size = models.IntegerField(default=0, help_text="Number of data points")
    confidence_score = models.FloatField(default=0.0, help_text="0.0–1.0 data confidence")
    currency = models.CharField(max_length=5, default="LKR")
    salary_period = models.CharField(max_length=10, default="monthly")
    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jf_salary_estimates"
        ordering = ["normalized_title", "district"]
        indexes = [
            models.Index(fields=["normalized_title", "district"], name="idx_sal_title_dist"),
        ]

    def __str__(self):
        return f"Salary: {self.normalized_title} / {self.district} — LKR {self.salary_median_lkr}"


class SalaryBenchmark(models.Model):
    """Market benchmark comparison for a salary query."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    district = models.ForeignKey("taxonomy.District", on_delete=models.SET_NULL, null=True, blank=True)
    user_salary = models.IntegerField(help_text="Salary entered by user for comparison")
    market_median = models.IntegerField(null=True, blank=True)
    percentile_rank = models.FloatField(null=True, blank=True, help_text="User's salary percentile vs market")
    below_market = models.BooleanField(default=False)
    above_market = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "jf_salary_benchmarks"
        ordering = ["-created_at"]


class SalaryTrend(models.Model):
    """Monthly salary trend per title (for chart data)."""
    normalized_title = models.CharField(max_length=200)
    district = models.ForeignKey("taxonomy.District", on_delete=models.SET_NULL, null=True, blank=True)
    month = models.DateField(help_text="First day of the month")
    median_salary_lkr = models.IntegerField(null=True, blank=True)
    sample_size = models.IntegerField(default=0)

    class Meta:
        db_table = "jf_salary_trends"
        unique_together = ["normalized_title", "district", "month"]
        ordering = ["normalized_title", "-month"]

    def __str__(self):
        return f"Trend: {self.normalized_title} {self.month} — LKR {self.median_salary_lkr}"


class CostOfLivingIndex(models.Model):
    """District-level cost-of-living index for salary overlay."""
    district = models.OneToOneField("taxonomy.District", on_delete=models.CASCADE,
                                    related_name="cost_of_living")
    index_value = models.FloatField(default=100.0, help_text="100 = national average")
    housing_index = models.FloatField(default=100.0)
    transport_index = models.FloatField(default=100.0)
    food_index = models.FloatField(default=100.0)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "jf_cost_of_living_index"

    def __str__(self):
        return f"COL: {self.district} — {self.index_value}"


class SalarySubmission(models.Model):
    """Verified anonymous salary submission from a user."""
    class VerificationStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employer = models.ForeignKey("employers.EmployerAccount", on_delete=models.SET_NULL, null=True, blank=True)
    normalized_title = models.CharField(max_length=200)
    district = models.ForeignKey("taxonomy.District", on_delete=models.SET_NULL, null=True, blank=True)
    experience_years = models.IntegerField(null=True, blank=True)
    experience_level = models.CharField(max_length=10, blank=True, default="")
    base_salary_lkr = models.IntegerField()
    total_comp_lkr = models.IntegerField(null=True, blank=True)
    has_bonus = models.BooleanField(default=False)
    has_medical = models.BooleanField(default=False)
    job_type = models.CharField(max_length=15, blank=True, default="")
    gender = models.CharField(max_length=20, blank=True, default="")
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    verification_status = models.CharField(max_length=10, choices=VerificationStatus.choices,
                                           default=VerificationStatus.PENDING)
    confidence_boost = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "jf_salary_submissions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Submission: {self.normalized_title} LKR {self.base_salary_lkr}"
