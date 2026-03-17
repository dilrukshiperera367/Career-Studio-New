"""Enhanced seo_indexing views — crawl health dashboard, faceted SEO data."""
import json
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Count, Q
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.jobs.models import JobListing
from apps.employers.models import EmployerAccount
from apps.taxonomy.models import JobCategory, District
from .models import SitemapEntry, IndexingAPILog, StructuredDataValidation, CrawlHealthSnapshot
from .serializers import (
    SitemapEntrySerializer, IndexingAPILogSerializer,
    StructuredDataValidationSerializer, CrawlHealthSerializer,
)


def build_job_posting_json_ld(job):
    """Build JSON-LD JobPosting structured data for Google."""
    emp_type_map = {
        "full_time": "FULL_TIME", "part_time": "PART_TIME",
        "contract": "CONTRACTOR", "temporary": "TEMPORARY",
        "internship": "INTERN", "freelance": "OTHER",
    }
    period_map = {"hourly": "HOUR", "monthly": "MONTH", "annual": "YEAR"}

    data = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": job.title,
        "description": (job.description or "")[:5000],
        "identifier": {
            "@type": "PropertyValue",
            "name": "JobFinder LK",
            "value": str(job.id),
        },
        "datePosted": job.published_at.strftime("%Y-%m-%d") if job.published_at else None,
        "validThrough": job.expires_at.strftime("%Y-%m-%dT%H:%M:%S") if job.expires_at else None,
        "employmentType": emp_type_map.get(job.job_type, "OTHER"),
        "hiringOrganization": {
            "@type": "Organization",
            "name": job.employer.company_name,
            "sameAs": job.employer.website or "",
            "logo": job.employer.logo.url if job.employer.logo else "",
        },
        "jobLocation": {
            "@type": "Place",
            "address": {
                "@type": "PostalAddress",
                "addressLocality": getattr(job.district, "name_en", "") if job.district else "",
                "addressRegion": getattr(job.province, "name_en", "") if job.province else "",
                "addressCountry": "LK",
                "streetAddress": job.address_line or "",
            },
        },
        "url": f"https://jobfinder.lk/en/jobs/{job.slug}",
    }

    if job.work_arrangement == "remote":
        data["applicantLocationRequirements"] = {"@type": "Country", "name": "Sri Lanka"}
        data["jobLocationType"] = "TELECOMMUTE"

    if job.salary_min and not job.hide_salary:
        data["baseSalary"] = {
            "@type": "MonetaryAmount",
            "currency": job.salary_currency,
            "value": {
                "@type": "QuantitativeValue",
                "minValue": float(job.salary_min),
                "maxValue": float(job.salary_max) if job.salary_max else None,
                "unitText": period_map.get(job.salary_period, "MONTH"),
            },
        }

    if job.experience_level:
        data["experienceRequirements"] = job.experience_level.replace("_", " ").title()

    if job.min_education:
        data["educationRequirements"] = {
            "@type": "EducationalOccupationalCredential",
            "credentialCategory": job.min_education.name_en,
        }

    if job.required_skills.exists():
        data["skills"] = ", ".join(job.required_skills.values_list("name_en", flat=True)[:10])

    if job.visa_sponsorship:
        data["jobBenefits"] = "Visa sponsorship available"

    return data


class JobStructuredDataView(APIView):
    """Return JSON-LD JobPosting structured data for a job slug."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        try:
            job = JobListing.objects.select_related(
                "employer", "district", "province", "min_education"
            ).prefetch_related("required_skills").get(slug=slug)
        except JobListing.DoesNotExist:
            return Response({"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(build_job_posting_json_ld(job))


class CompanyStructuredDataView(APIView):
    """Return JSON-LD Organization structured data for a company slug."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        try:
            employer = EmployerAccount.objects.select_related("industry", "headquarters").get(slug=slug)
        except EmployerAccount.DoesNotExist:
            return Response({"detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

        data = {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": employer.company_name,
            "url": employer.website or "",
            "logo": employer.logo.url if employer.logo else "",
            "description": employer.description or "",
            "foundingDate": str(employer.founded_year) if employer.founded_year else None,
            "numberOfEmployees": {
                "@type": "QuantitativeValue",
                "value": employer.company_size or ""
            },
            "address": {
                "@type": "PostalAddress",
                "addressLocality": getattr(employer.headquarters, "name_en", "") if employer.headquarters else "",
                "addressCountry": "LK",
            },
            "sameAs": employer.website or "",
        }
        if employer.industry:
            data["industry"] = employer.industry.name_en
        return Response(data)


class SitemapHealthView(APIView):
    """Crawl health + sitemap health dashboard for admins."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        snapshots = CrawlHealthSnapshot.objects.all()[:30]
        total_entries = SitemapEntry.objects.count()
        active_entries = SitemapEntry.objects.filter(is_indexable=True, is_expired=False).count()
        expired_entries = SitemapEntry.objects.filter(is_expired=True).count()

        # Validation summary
        sd_summary = StructuredDataValidation.objects.values("status").annotate(count=Count("id"))
        sd_by_status = {s["status"]: s["count"] for s in sd_summary}

        # Indexing API summary
        api_logs = IndexingAPILog.objects.all().values("action", "success").annotate(count=Count("id"))
        api_summary = {
            "url_updated_ok": 0, "url_updated_fail": 0,
            "url_deleted_ok": 0, "url_deleted_fail": 0,
        }
        for row in api_logs:
            key = f"{'url_updated' if row['action'] == 'URL_UPDATED' else 'url_deleted'}_{'ok' if row['success'] else 'fail'}"
            api_summary[key] = row["count"]

        return Response({
            "sitemap": {
                "total": total_entries,
                "active": active_entries,
                "expired": expired_entries,
            },
            "structured_data_validation": sd_by_status,
            "indexing_api": api_summary,
            "recent_snapshots": CrawlHealthSerializer(snapshots, many=True).data,
        })


class IndexingAPILogListView(APIView):
    """List Google Indexing API call logs."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        logs = IndexingAPILog.objects.all()[:100]
        return Response(IndexingAPILogSerializer(logs, many=True).data)


class StructuredDataValidationView(APIView):
    """Submit and retrieve structured data validation results for a page."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, slug):
        page_type = request.query_params.get("type", "job")
        try:
            validation = StructuredDataValidation.objects.get(page_type=page_type, slug=slug)
        except StructuredDataValidation.DoesNotExist:
            return Response({"detail": "Not validated yet."}, status=status.HTTP_404_NOT_FOUND)
        return Response(StructuredDataValidationSerializer(validation).data)


class FacetedSEODataView(APIView):
    """
    Returns live SEO data for faceted landing pages:
    /jobs/category/<slug>, /jobs/city/<slug>, /salary-guide/<slug>

    Used by Next.js faceted pages for generateMetadata and page content.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, facet_type, slug):
        cache_key = f"seo_facet:{facet_type}:{slug}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        base_qs = JobListing.objects.filter(status="active")

        if facet_type == "category":
            try:
                cat = JobCategory.objects.get(slug=slug)
            except JobCategory.DoesNotExist:
                return Response({"detail": "Category not found."}, status=status.HTTP_404_NOT_FOUND)

            jobs = base_qs.filter(category=cat)
            salary_data = jobs.filter(salary_min__isnull=False).aggregate(
                avg_min=__import__("django.db.models", fromlist=["Avg"]).Avg("salary_min"),
            )
            data = {
                "type": "category",
                "slug": slug,
                "name": cat.name_en,
                "job_count": jobs.count(),
                "avg_salary_min": salary_data.get("avg_min"),
                "meta_title": f"{cat.name_en} Jobs in Sri Lanka | JobFinder LK",
                "meta_description": (
                    f"Find {jobs.count():,} {cat.name_en} jobs in Sri Lanka. "
                    f"Browse full-time, part-time, and remote positions with salary details."
                ),
                "canonical_url": f"https://jobfinder.lk/en/jobs/category/{slug}",
                "top_districts": list(
                    jobs.filter(district__isnull=False)
                    .values("district__slug", "district__name_en")
                    .annotate(count=Count("id"))
                    .order_by("-count")[:6]
                ),
            }

        elif facet_type == "city":
            try:
                district = District.objects.get(slug=slug)
            except District.DoesNotExist:
                return Response({"detail": "City not found."}, status=status.HTTP_404_NOT_FOUND)

            jobs = base_qs.filter(district=district)
            data = {
                "type": "city",
                "slug": slug,
                "name": district.name_en,
                "job_count": jobs.count(),
                "meta_title": f"Jobs in {district.name_en}, Sri Lanka | JobFinder LK",
                "meta_description": (
                    f"Browse {jobs.count():,} jobs in {district.name_en}. "
                    f"Find local jobs across all industries with salary info and easy apply."
                ),
                "canonical_url": f"https://jobfinder.lk/en/jobs/city/{slug}",
                "top_categories": list(
                    jobs.filter(category__isnull=False)
                    .values("category__slug", "category__name_en")
                    .annotate(count=Count("id"))
                    .order_by("-count")[:8]
                ),
            }

        elif facet_type == "salary":
            # Salary guide page for a role category
            try:
                cat = JobCategory.objects.get(slug=slug)
            except JobCategory.DoesNotExist:
                return Response({"detail": "Category not found."}, status=status.HTTP_404_NOT_FOUND)

            from django.db.models import Avg, Min, Max
            jobs = base_qs.filter(category=cat, salary_min__isnull=False, hide_salary=False)
            agg = jobs.aggregate(
                avg_min=Avg("salary_min"), avg_max=Avg("salary_max"),
                min_salary=Min("salary_min"), max_salary=Max("salary_max"),
            )
            data = {
                "type": "salary",
                "slug": slug,
                "name": cat.name_en,
                "job_count": jobs.count(),
                "avg_salary_min": round(agg["avg_min"] or 0),
                "avg_salary_max": round(agg["avg_max"] or 0),
                "min_salary": round(agg["min_salary"] or 0),
                "max_salary": round(agg["max_salary"] or 0),
                "meta_title": f"{cat.name_en} Salary in Sri Lanka 2026 | JobFinder LK",
                "meta_description": (
                    f"Average {cat.name_en} salary in Sri Lanka is "
                    f"LKR {round((agg['avg_min'] or 0)/1000)}k–{round((agg['avg_max'] or 0)/1000)}k/month. "
                    f"See salary ranges by experience level and location."
                ),
                "canonical_url": f"https://jobfinder.lk/en/salary-guide/{slug}",
                "by_experience": list(
                    jobs.values("experience_level")
                    .annotate(avg_min=Avg("salary_min"), avg_max=Avg("salary_max"), count=Count("id"))
                    .order_by("experience_level")
                ),
            }
        else:
            return Response({"detail": "Unknown facet type."}, status=status.HTTP_400_BAD_REQUEST)

        cache.set(cache_key, data, 3600)
        return Response(data)


class InternalLinkGraphView(APIView):
    """
    Returns the internal link graph for a given page to support
    related category/city/company cross-linking in page templates.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        cache_key = "seo_internal_link_graph"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        # Top categories with job counts
        categories = list(
            JobCategory.objects.annotate(
                job_count=Count("jobs", filter=Q(jobs__status="active"))
            ).filter(job_count__gt=0).order_by("-job_count")[:20]
            .values("slug", "name_en", "job_count")
        )

        # Top districts with job counts
        cities = list(
            District.objects.annotate(
                job_count=Count("joblisting", filter=Q(joblisting__status="active"))
            ).filter(job_count__gt=0).order_by("-job_count")[:20]
            .values("slug", "name_en", "job_count")
        )

        # Top employers with job counts
        employers = list(
            EmployerAccount.objects.annotate(
                job_count=Count("jobs", filter=Q(jobs__status="active"))
            ).filter(job_count__gt=0).order_by("-job_count")[:15]
            .values("slug", "company_name", "job_count")
        )

        data = {
            "categories": categories,
            "cities": cities,
            "employers": employers,
            "generated_at": timezone.now().isoformat(),
        }
        cache.set(cache_key, data, 3600)
        return Response(data)
