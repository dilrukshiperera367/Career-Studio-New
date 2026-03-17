"""Django management command to seed demo data (50+ candidates, 20+ jobs, interviews, offers)."""

import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Seed the database with realistic demo data"

    def add_arguments(self, parser):
        parser.add_argument("--candidates", type=int, default=50, help="Number of candidates")
        parser.add_argument("--jobs", type=int, default=20, help="Number of jobs")
        parser.add_argument("--clear", action="store_true", help="Clear existing seed data first")

    def handle(self, *args, **options):
        from apps.candidates.models import Candidate
        from apps.jobs.models import Job
        from apps.applications.models import Application

        if options["clear"]:
            Candidate.objects.filter(source="seed").delete()
            Job.objects.filter(description__contains="[SEED]").delete()
            self.stdout.write(self.style.WARNING("Cleared existing seed data"))

        # ── Candidates ────────────────────────────────────────────────────
        first_names = ["James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
                       "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
                       "Thomas", "Sarah", "Charles", "Karen", "Daniel", "Lisa", "Matthew", "Nancy",
                       "Anthony", "Betty", "Mark", "Margaret", "Donald", "Sandra", "Steven", "Ashley",
                       "Andrew", "Emily", "Paul", "Donna", "Joshua", "Michelle", "Kenneth", "Carol",
                       "Kevin", "Amanda", "Brian", "Dorothy", "George", "Melissa", "Timothy", "Deborah",
                       "Priya", "Wei", "Fatima", "Carlos", "Yuki", "Olga"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
                      "Rodriguez", "Martinez", "Hernandez", "Lopez", "Wilson", "Anderson", "Thomas",
                      "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White",
                      "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
                      "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill",
                      "Flores", "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell",
                      "Mitchell", "Patel", "Chen", "Kim"]
        sources = ["linkedin", "referral", "website", "indeed", "glassdoor", "angellist", "recruiter", "career_fair"]
        tags_pool = ["python", "javascript", "react", "django", "aws", "devops", "ml", "senior",
                     "java", "go", "rust", "typescript", "node", "sql", "nosql", "product",
                     "design", "figma", "agile", "scrum", "leadership", "remote", "manager"]

        count_candidates = 0
        for i in range(options["candidates"]):
            fname = random.choice(first_names)
            lname = random.choice(last_names)
            email = f"{fname.lower()}.{lname.lower()}{random.randint(1,999)}@demo.com"
            if Candidate.objects.filter(email=email).exists():
                continue
            Candidate.objects.create(
                name=f"{fname} {lname}",
                email=email,
                phone=f"+1-555-{random.randint(100,999)}-{random.randint(1000,9999)}",
                source=random.choice(sources),
                rating=random.randint(1, 5),
                tags=random.sample(tags_pool, min(random.randint(1, 5), len(tags_pool))),
            )
            count_candidates += 1

        # ── Jobs ──────────────────────────────────────────────────────────
        job_data = [
            ("Senior Frontend Engineer", "Engineering", "Remote"),
            ("Backend Developer", "Engineering", "San Francisco"),
            ("Data Scientist", "Data", "New York"),
            ("Product Manager", "Product", "Remote"),
            ("DevOps Engineer", "Engineering", "Seattle"),
            ("UX Designer", "Design", "Austin"),
            ("Marketing Manager", "Marketing", "Chicago"),
            ("Sales Representative", "Sales", "Los Angeles"),
            ("HR Coordinator", "People", "Boston"),
            ("QA Engineer", "Engineering", "Remote"),
            ("Mobile Developer", "Engineering", "San Jose"),
            ("Content Writer", "Marketing", "Remote"),
            ("Customer Success Manager", "Support", "Denver"),
            ("Financial Analyst", "Finance", "New York"),
            ("Machine Learning Engineer", "Data", "Remote"),
            ("Project Manager", "Operations", "Portland"),
            ("Security Engineer", "Engineering", "Washington DC"),
            ("Business Analyst", "Product", "Atlanta"),
            ("Full Stack Developer", "Engineering", "Remote"),
            ("Solutions Architect", "Engineering", "Seattle"),
        ]

        count_jobs = 0
        for title, dept, location in job_data[:options["jobs"]]:
            if Job.objects.filter(title=title).exists():
                continue
            Job.objects.create(
                title=title,
                department=dept,
                location=location,
                employment_type=random.choice(["full_time", "contract", "part_time"]),
                status=random.choice(["open", "open", "open", "draft"]),
                description=f"[SEED] Exciting {title} opportunity in {dept}. Join our team in {location}.",
            )
            count_jobs += 1

        # ── Applications ──────────────────────────────────────────────────
        candidates = list(Candidate.objects.all()[:100])
        jobs = list(Job.objects.all()[:20])
        stages = ["applied", "screening", "interview", "final_round", "offer", "hired"]
        count_apps = 0
        for _ in range(min(len(candidates) * 2, 200)):
            cand = random.choice(candidates)
            job = random.choice(jobs)
            if Application.objects.filter(candidate=cand, job=job).exists():
                continue
            Application.objects.create(
                candidate=cand,
                job=job,
                status=random.choice(["active", "active", "active", "rejected"]),
                current_stage_name=random.choice(stages),
                created_at=timezone.now() - timedelta(days=random.randint(0, 90)),
            )
            count_apps += 1

        self.stdout.write(self.style.SUCCESS(
            f"✅ Seeded: {count_candidates} candidates, {count_jobs} jobs, {count_apps} applications"
        ))
