import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify
from django.contrib.auth import get_user_model
from apps.taxonomy.models import JobCategory, District, Skill, Industry
from apps.employers.models import EmployerAccount
from apps.jobs.models import JobListing

User = get_user_model()

COMPANIES = [
    ('WSO2', 'wso2', 'Leading open-source middleware company', 'Information Technology', '501-1000'),
    ('Virtusa', 'virtusa', 'Global IT consulting and outsourcing company', 'Information Technology', '1001+'),
    ('IFS', 'ifs', 'Enterprise software solutions provider', 'Information Technology', '1001+'),
    ('Dialog Axiata', 'dialog-axiata', 'Sri Lanka\'s largest mobile operator', 'Telecommunications', '1001+'),
    ('MAS Holdings', 'mas-holdings', 'Apparel and textile manufacturing', 'Manufacturing', '1001+'),
    ('John Keells Holdings', 'john-keells', 'Diversified conglomerate', 'Retail', '1001+'),
    ('Hayleys', 'hayleys', 'Diversified multinational conglomerate', 'Manufacturing', '1001+'),
    ('LSEG Technology', 'lseg-technology', 'Financial technology services', 'Financial Services', '501-1000'),
    ('Cargills', 'cargills', 'Retail and food manufacturing', 'Retail', '1001+'),
    ('Brandix', 'brandix', 'Apparel manufacturing', 'Manufacturing', '1001+'),
    ('CodeGen', 'codegen', 'Travel technology solutions', 'Information Technology', '201-500'),
    ('Sysco LABS', 'sysco-labs', 'Technology innovation center', 'Information Technology', '201-500'),
    ('Creative Software', 'creative-software', 'IT development services', 'Information Technology', '51-200'),
    ('Calcey Technologies', 'calcey', 'Software product engineering', 'Information Technology', '51-200'),
    ('Pearson Lanka', 'pearson-lanka', 'Education publishing', 'Education', '51-200'),
]

JOB_TEMPLATES = [
    ('Senior Software Engineer', 'full_time', 'senior', 150000, 350000),
    ('Junior Frontend Developer', 'full_time', 'entry', 60000, 120000),
    ('DevOps Engineer', 'full_time', 'mid', 120000, 250000),
    ('Data Analyst', 'full_time', 'mid', 100000, 200000),
    ('Product Manager', 'full_time', 'senior', 200000, 400000),
    ('UI/UX Designer', 'full_time', 'mid', 80000, 180000),
    ('Marketing Executive', 'full_time', 'entry', 50000, 100000),
    ('Accountant', 'full_time', 'mid', 70000, 150000),
    ('HR Coordinator', 'full_time', 'entry', 50000, 90000),
    ('Sales Manager', 'full_time', 'senior', 100000, 250000),
    ('QA Engineer', 'full_time', 'mid', 90000, 180000),
    ('Business Analyst', 'full_time', 'mid', 100000, 200000),
    ('Intern - Software Development', 'internship', 'internship', 25000, 50000),
    ('Part-time Content Writer', 'part_time', 'entry', 30000, 60000),
    ('Project Manager', 'full_time', 'senior', 150000, 300000),
    ('Customer Support Agent', 'full_time', 'entry', 40000, 70000),
    ('Network Administrator', 'full_time', 'mid', 80000, 160000),
    ('Mobile App Developer', 'full_time', 'mid', 120000, 250000),
    ('Financial Analyst', 'full_time', 'mid', 100000, 200000),
    ('Graphic Designer', 'contract', 'mid', 60000, 130000),
]


class Command(BaseCommand):
    help = 'Seed sample employers and job listings'

    def handle(self, *args, **options):
        self.stdout.write('Seeding sample data...')

        categories = list(JobCategory.objects.all())
        districts = list(District.objects.all())
        skills = list(Skill.objects.all())
        industries = list(Industry.objects.all())

        if not categories or not districts:
            self.stdout.write(self.style.ERROR('Run seed_taxonomy first!'))
            return

        # Create employer users & accounts
        employers = []
        for name, slug, desc, ind, size in COMPANIES:
            email = f'hr@{slug}.lk'
            user, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': name,
                    'last_name': 'HR',
                    'role': 'employer',
                    'is_email_verified': True,
                },
            )
            if user.has_usable_password() is False:
                user.set_password('demo1234')
                user.save()

            industry_obj = next((i for i in industries if i.name_en == ind), industries[0] if industries else None)
            employer, _ = EmployerAccount.objects.get_or_create(
                slug=slug,
                defaults={
                    'user': user,
                    'company_name': name,
                    'company_name_si': name,
                    'company_name_ta': name,
                    'description_en': desc,
                    'industry': industry_obj,
                    'company_size': size,
                    'website': f'https://{slug}.lk',
                    'email': email,
                    'city': 'Colombo',
                    'district': random.choice(districts),
                    'is_verified': True,
                    'is_active': True,
                },
            )
            employers.append(employer)
        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(employers)} employers'))

        # Create job listings
        job_count = 0
        now = timezone.now()
        for employer in employers:
            num_jobs = random.randint(2, 6)
            templates = random.sample(JOB_TEMPLATES, min(num_jobs, len(JOB_TEMPLATES)))
            for title, jtype, exp, sal_min, sal_max in templates:
                slug_val = slugify(f'{title}-{employer.slug}-{random.randint(100, 999)}')
                district = random.choice(districts)
                category = random.choice(categories)

                job, created = JobListing.objects.get_or_create(
                    slug=slug_val,
                    defaults={
                        'employer': employer,
                        'title_en': title,
                        'title_si': title,
                        'title_ta': title,
                        'slug': slug_val,
                        'description_en': f'<p>We are looking for a {title} to join our team at {employer.company_name}. This is an exciting opportunity for growth and innovation.</p><p>You will work with cutting-edge technologies and collaborate with talented teams.</p>',
                        'requirements_en': f'<ul><li>Relevant degree or equivalent experience</li><li>Strong communication skills</li><li>Team player with initiative</li></ul>',
                        'benefits_en': '<ul><li>Competitive salary</li><li>Health insurance</li><li>Professional development</li><li>Flexible hours</li></ul>',
                        'category': category,
                        'job_type': jtype,
                        'work_arrangement': random.choice(['on_site', 'remote', 'hybrid']),
                        'experience_level': exp,
                        'salary_min': sal_min,
                        'salary_max': sal_max,
                        'salary_currency': 'LKR',
                        'is_salary_visible': random.choice([True, True, False]),
                        'location_text': f'{district.name_en}',
                        'district': district,
                        'vacancies': random.randint(1, 5),
                        'deadline': now + timedelta(days=random.randint(14, 60)),
                        'status': 'published',
                        'is_featured': random.random() < 0.2,
                        'view_count': random.randint(10, 500),
                    },
                )
                if created and skills:
                    job_skills = random.sample(skills, min(random.randint(3, 6), len(skills)))
                    job.skills.set(job_skills)
                    job_count += 1

        self.stdout.write(self.style.SUCCESS(f'  ✓ {job_count} jobs created'))
        self.stdout.write(self.style.SUCCESS('\nSample data seeding completed!'))
