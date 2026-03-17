"""Seed the database with demo data (tenant, user, roles, jobs, candidates, applications)."""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from apps.tenants.models import Tenant, TenantSettings
from apps.accounts.models import User, Role, UserRole, PERMISSIONS
from apps.jobs.models import Job, PipelineStage
from apps.candidates.models import Candidate, CandidateIdentity
from apps.applications.models import Application, StageHistory


class Command(BaseCommand):
    help = "Seed demo data: tenant, user, roles, jobs, candidates, applications"

    def handle(self, *args, **options):
        self.stdout.write("=== Seeding Demo Data ===\n")

        # ── 1. Tenant ──
        tenant, created = Tenant.objects.get_or_create(
            slug="demo-corp",
            defaults={
                "name": "Demo Corp",
                "domain": "democorp.com",
                "status": "active",
                "plan": "pro",
            },
        )
        if created:
            TenantSettings.objects.create(tenant=tenant)
            self.stdout.write(self.style.SUCCESS(f"  Created tenant: {tenant.name}"))
        else:
            self.stdout.write(f"  Tenant exists: {tenant.name}")

        # ── 2. Roles ──
        roles = {}
        for role_name, perms in PERMISSIONS.items():
            role, _ = Role.objects.get_or_create(
                tenant=tenant,
                name=role_name,
                defaults={"permissions": perms},
            )
            roles[role_name] = role
        self.stdout.write(self.style.SUCCESS(f"  Roles: {', '.join(roles.keys())}"))

        # ── 3. Admin User ──
        user, created = User.objects.get_or_create(
            email="demo@company.com",
            defaults={
                "tenant": tenant,
                "first_name": "Alex",
                "last_name": "Demo",
                "user_type": "company_admin",
                "is_staff": True,
            },
        )
        if created:
            user.set_password("demo1234")
            user.save()
            self.stdout.write(self.style.SUCCESS(f"  Created user: {user.email} (password: demo1234)"))
        else:
            self.stdout.write(f"  User exists: {user.email}")

        # Always ensure roles are assigned (even if user pre-existed)
        for rname in ["admin", "recruiter"]:
            UserRole.objects.get_or_create(user=user, role=roles[rname])

        # ── 4. Jobs ──
        job_data = [
            {"title": "Senior Frontend Engineer", "department": "Engineering", "location": "San Francisco, CA", "status": "open", "employment_type": "full_time", "description": "Build amazing React/Next.js interfaces for our SaaS platform.", "salary_min": 130000, "salary_max": 180000},
            {"title": "Backend Developer (Python)", "department": "Engineering", "location": "Remote", "status": "open", "is_remote": True, "employment_type": "full_time", "description": "Design and build scalable Django APIs and microservices.", "salary_min": 120000, "salary_max": 170000},
            {"title": "Product Designer", "department": "Design", "location": "New York, NY", "status": "open", "employment_type": "full_time", "description": "Create beautiful, data-driven product designs for our platform.", "salary_min": 110000, "salary_max": 150000},
            {"title": "DevOps Engineer", "department": "Infrastructure", "location": "Remote", "status": "open", "is_remote": True, "employment_type": "full_time", "description": "Manage cloud infrastructure, CI/CD pipelines, and monitoring.", "salary_min": 125000, "salary_max": 175000},
            {"title": "Data Scientist", "department": "Data", "location": "Austin, TX", "status": "open", "employment_type": "full_time", "description": "Apply ML and statistical methods to recruiting data.", "salary_min": 135000, "salary_max": 185000},
        ]

        default_stages = [
            ("Applied", "applied", 0, False),
            ("Screening", "screening", 1, False),
            ("Interview", "interview", 2, False),
            ("Offer", "offer", 3, False),
            ("Hired", "hired", 4, True),
            ("Rejected", "rejected", 5, True),
        ]

        jobs = []
        for jd in job_data:
            slug = slugify(jd["title"])
            job, created = Job.objects.get_or_create(
                tenant=tenant,
                slug=slug,
                defaults={
                    **jd,
                    "slug": slug,
                    "created_by": user,
                    "published_at": timezone.now() if jd["status"] == "open" else None,
                },
            )
            if created:
                for name, stype, order, terminal in default_stages:
                    PipelineStage.objects.create(
                        tenant=tenant, job=job, name=name,
                        stage_type=stype, order=order, is_terminal=terminal,
                    )
                self.stdout.write(self.style.SUCCESS(f"  Created job: {job.title}"))
            else:
                self.stdout.write(f"  Job exists: {job.title}")
            jobs.append(job)

        # ── 5. Candidates ──
        candidate_data = [
            {"full_name": "Sarah Chen", "primary_email": "sarah.chen@email.com", "primary_phone": "+1-555-0101", "headline": "Full Stack Developer | React + Python", "location": "San Francisco, CA", "source": "linkedin", "total_experience_years": 6},
            {"full_name": "Marcus Johnson", "primary_email": "marcus.j@email.com", "primary_phone": "+1-555-0102", "headline": "Senior Backend Engineer | Django Expert", "location": "Austin, TX", "source": "referral", "total_experience_years": 8},
            {"full_name": "Emily Park", "primary_email": "emily.park@email.com", "primary_phone": "+1-555-0103", "headline": "UX/UI Designer | Figma & Sketch", "location": "New York, NY", "source": "indeed", "total_experience_years": 5},
            {"full_name": "David Kim", "primary_email": "david.kim@email.com", "primary_phone": "+1-555-0104", "headline": "Cloud Infrastructure Engineer | AWS & K8s", "location": "Seattle, WA", "source": "linkedin", "total_experience_years": 7},
            {"full_name": "Lisa Wang", "primary_email": "lisa.wang@email.com", "primary_phone": "+1-555-0105", "headline": "ML Engineer | Python & TensorFlow", "location": "Remote", "source": "career_page", "total_experience_years": 4},
            {"full_name": "James Rodriguez", "primary_email": "james.r@email.com", "primary_phone": "+1-555-0106", "headline": "React Native Developer | Mobile Expert", "location": "Los Angeles, CA", "source": "linkedin", "total_experience_years": 5},
            {"full_name": "Aisha Patel", "primary_email": "aisha.p@email.com", "primary_phone": "+1-555-0107", "headline": "Product Manager to Designer Transition", "location": "Chicago, IL", "source": "referral", "total_experience_years": 9},
            {"full_name": "Tom Wilson", "primary_email": "tom.w@email.com", "primary_phone": "+1-555-0108", "headline": "DevOps & SRE Lead | Terraform Expert", "location": "Denver, CO", "source": "indeed", "total_experience_years": 10},
        ]

        candidates = []
        for cd in candidate_data:
            candidate, created = Candidate.objects.get_or_create(
                tenant=tenant,
                primary_email=cd["primary_email"],
                defaults=cd,
            )
            if created:
                CandidateIdentity.objects.create(
                    tenant=tenant, candidate=candidate,
                    identity_type="email",
                    identity_value=cd["primary_email"].lower(),
                )
                self.stdout.write(self.style.SUCCESS(f"  Created candidate: {candidate.full_name}"))
            else:
                self.stdout.write(f"  Candidate exists: {candidate.full_name}")
            candidates.append(candidate)

        # ── 6. Applications ──
        app_map = [
            (0, 0), (1, 1), (2, 2), (3, 3), (4, 4),
            (5, 0), (6, 2), (7, 3),
        ]

        for cand_idx, job_idx in app_map:
            job = jobs[job_idx]
            candidate = candidates[cand_idx]

            first_stage = PipelineStage.objects.filter(
                job=job, tenant=tenant
            ).order_by("order").first()

            if not first_stage:
                continue

            app, created = Application.objects.get_or_create(
                tenant=tenant,
                job=job,
                candidate=candidate,
                defaults={
                    "current_stage": first_stage,
                    "status": "active",
                    "source": candidate.source,
                },
            )

            if created:
                StageHistory.objects.create(
                    tenant=tenant,
                    application=app,
                    to_stage=first_stage,
                    notes="Application created via seed",
                )
                self.stdout.write(self.style.SUCCESS(
                    f"  Created application: {candidate.full_name} -> {job.title}"
                ))
            else:
                self.stdout.write(f"  Application exists: {candidate.full_name} -> {job.title}")

        # ── 7. Interviews ──
        from apps.applications.models import Interview
        from datetime import date, time

        interview_data = [
            {"candidate": candidates[0], "job": jobs[0], "interview_type": "video", "date": date(2026, 3, 5), "time": time(10, 0), "duration": 45, "interviewer_name": "Alex Demo", "location": "Google Meet", "status": "scheduled", "notes": "Focus on React architecture and system design"},
            {"candidate": candidates[1], "job": jobs[1], "interview_type": "video", "date": date(2026, 3, 4), "time": time(14, 0), "duration": 60, "interviewer_name": "Alex Demo", "location": "Zoom", "status": "completed", "notes": "Technical assessment", "feedback": "Excellent Django skills. Recommend for offer.", "rating": 5},
            {"candidate": candidates[2], "job": jobs[2], "interview_type": "phone", "date": date(2026, 3, 3), "time": time(11, 0), "duration": 30, "interviewer_name": "Alex Demo", "location": "Phone", "status": "completed", "notes": "Initial screening call", "feedback": "Good portfolio. Move to next round.", "rating": 4},
            {"candidate": candidates[4], "job": jobs[4], "interview_type": "video", "date": date(2026, 3, 6), "time": time(13, 0), "duration": 60, "interviewer_name": "Alex Demo", "location": "Microsoft Teams", "status": "scheduled", "notes": "ML case study discussion"},
        ]

        for idata in interview_data:
            Interview.objects.get_or_create(
                tenant=tenant,
                candidate=idata["candidate"],
                job=idata["job"],
                date=idata["date"],
                defaults={**{k: v for k, v in idata.items()}, "tenant": tenant, "interviewer": user},
            )
        self.stdout.write(self.style.SUCCESS(f"  Seeded {len(interview_data)} interviews"))

        # ── 8. Offers ──
        from apps.applications.models import Offer

        # Create offer for Marcus Johnson (Backend Developer)
        app_for_offer = Application.objects.filter(
            tenant=tenant, candidate=candidates[1], job=jobs[1]
        ).first()

        if app_for_offer:
            Offer.objects.get_or_create(
                tenant=tenant,
                candidate=candidates[1],
                job=jobs[1],
                defaults={
                    "application": app_for_offer,
                    "salary": "$155,000",
                    "start_date": date(2026, 4, 1),
                    "benefits": "Health, dental, vision, 401k match, unlimited PTO",
                    "equity": "0.05% stock options",
                    "signing_bonus": "$10,000",
                    "status": "pending",
                    "approval_status": "approved",
                    "approver": user,
                    "notes": "Strong candidate — fast track",
                },
            )
            self.stdout.write(self.style.SUCCESS("  Seeded 1 offer"))

        # ── 9. Automation Rules ──
        from apps.workflows.models import AutomationRule

        rules_data = [
            {
                "name": "Auto-email on rejection",
                "trigger_type": "stage_changed",
                "conditions_json": {"to_stage_type": "rejected"},
                "actions_json": [{"type": "send_email", "template_id": "rejection_email"}],
            },
            {
                "name": "Auto-tag screening candidates",
                "trigger_type": "stage_changed",
                "conditions_json": {"to_stage_type": "screening"},
                "actions_json": [{"type": "assign_tag", "tag": "in-review"}],
            },
        ]

        for rd in rules_data:
            AutomationRule.objects.get_or_create(
                tenant=tenant,
                name=rd["name"],
                defaults={**rd, "enabled": True},
            )
        self.stdout.write(self.style.SUCCESS(f"  Seeded {len(rules_data)} automation rules"))

        self.stdout.write("\n" + self.style.SUCCESS("=== Seed complete ==="))
        self.stdout.write(f"\n  Login: demo@company.com / demo1234")
        self.stdout.write(f"  Backend: http://localhost:8000/api/v1/")
        self.stdout.write(f"  Frontend: http://localhost:3000/")

