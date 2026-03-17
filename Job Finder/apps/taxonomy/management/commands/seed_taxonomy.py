import random
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from apps.taxonomy.models import (
    Province, District, JobCategory, JobSubCategory, Industry, Skill, EducationLevel,
)


PROVINCES_DISTRICTS = {
    'Western': ['Colombo', 'Gampaha', 'Kalutara'],
    'Central': ['Kandy', 'Matale', 'Nuwara Eliya'],
    'Southern': ['Galle', 'Matara', 'Hambantota'],
    'Northern': ['Jaffna', 'Kilinochchi', 'Mannar', 'Mullaitivu', 'Vavuniya'],
    'Eastern': ['Batticaloa', 'Ampara', 'Trincomalee'],
    'North Western': ['Kurunegala', 'Puttalam'],
    'North Central': ['Anuradhapura', 'Polonnaruwa'],
    'Uva': ['Badulla', 'Monaragala'],
    'Sabaragamuwa': ['Ratnapura', 'Kegalle'],
}

CATEGORIES = {
    'Information Technology': ['Software Development', 'DevOps & Cloud', 'Data Science & AI', 'Cybersecurity', 'IT Support', 'QA & Testing', 'UI/UX Design', 'Database Administration'],
    'Finance & Accounting': ['Accounting', 'Auditing', 'Banking', 'Financial Analysis', 'Tax', 'Insurance'],
    'Marketing & Sales': ['Digital Marketing', 'SEO/SEM', 'Content Marketing', 'Sales', 'Brand Management', 'Market Research'],
    'Engineering': ['Civil Engineering', 'Mechanical Engineering', 'Electrical Engineering', 'Chemical Engineering', 'Automotive'],
    'Healthcare': ['Nursing', 'Pharmacy', 'Medical Technology', 'Dental', 'Public Health'],
    'Education': ['Teaching', 'Tutoring', 'Academic Research', 'Training & Development', 'Administration'],
    'Human Resources': ['Recruitment', 'Employee Relations', 'Compensation & Benefits', 'Training', 'HR Admin'],
    'Legal': ['Corporate Law', 'Criminal Law', 'Intellectual Property', 'Compliance', 'Paralegal'],
    'Hospitality & Tourism': ['Hotel Management', 'Travel Agency', 'Event Management', 'Food & Beverage', 'Tour Guide'],
    'Manufacturing': ['Production', 'Quality Control', 'Supply Chain', 'Warehouse', 'Logistics'],
    'Construction': ['Architecture', 'Project Management', 'Quantity Surveying', 'Site Management'],
    'Media & Communications': ['Journalism', 'Public Relations', 'Broadcasting', 'Copywriting', 'Photography'],
    'Government & NGO': ['Public Administration', 'Non-Profit', 'International Development', 'Social Work'],
    'Agriculture': ['Farming', 'Agribusiness', 'Plantation', 'Fisheries', 'Veterinary'],
    'Retail': ['Store Management', 'Merchandising', 'Customer Service', 'E-Commerce'],
}

INDUSTRIES = [
    'Information Technology', 'Financial Services', 'Healthcare', 'Education',
    'Manufacturing', 'Construction', 'Retail', 'Hospitality & Tourism',
    'Agriculture', 'Telecommunications', 'Energy', 'Transportation',
    'Real Estate', 'Media & Entertainment', 'Non-Profit', 'Government',
    'Apparel & Textiles', 'Automotive', 'Pharmaceuticals', 'Legal Services',
]

SKILLS = [
    'Python', 'JavaScript', 'TypeScript', 'React', 'Angular', 'Vue.js', 'Node.js', 'Django',
    'Java', 'C#', '.NET', 'PHP', 'Laravel', 'Ruby on Rails', 'Go', 'Rust', 'Swift', 'Kotlin',
    'SQL', 'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'Elasticsearch', 'Docker', 'Kubernetes',
    'AWS', 'Azure', 'GCP', 'Git', 'CI/CD', 'Agile', 'Scrum', 'JIRA',
    'Microsoft Office', 'Excel', 'Power BI', 'Tableau', 'SAP', 'Salesforce',
    'Digital Marketing', 'SEO', 'Google Analytics', 'Social Media Marketing',
    'Project Management', 'Communication', 'Leadership', 'Problem Solving',
    'Accounting', 'Financial Analysis', 'Budgeting', 'Auditing', 'Tax Planning',
    'AutoCAD', 'SolidWorks', 'MATLAB', 'Photoshop', 'Illustrator', 'Figma',
    'English', 'Sinhala', 'Tamil', 'Hindi', 'Mandarin', 'Japanese', 'Korean',
    'Customer Service', 'Sales', 'Negotiation', 'Presentation', 'Time Management',
]

EDUCATION_LEVELS = [
    ('primary', 'Primary Education', 'ප්\u200dරාථමික අධ්\u200dයාපනය', 'ஆரம்பக் கல்வி'),
    ('ol', 'O/L (Ordinary Level)', 'සාමාන්\u200dය පෙළ', 'சாதாரண தரம்'),
    ('al', 'A/L (Advanced Level)', 'උසස් පෙළ', 'உயர் தரம்'),
    ('diploma', 'Diploma', 'ඩිප්ලෝමා', 'டிப்ளோமா'),
    ('hnd', 'Higher National Diploma', 'උසස් ජාතික ඩිප්ලෝමා', 'உயர் தேசிய டிப்ளோமா'),
    ('bachelors', "Bachelor's Degree", 'උපාධිය', 'இளங்கலைப் பட்டம்'),
    ('masters', "Master's Degree", 'ශාස්ත්\u200dරපති උපාධිය', 'முதுகலைப் பட்டம்'),
    ('phd', 'PhD / Doctorate', 'ආචාර්ය උපාධිය', 'முனைவர் பட்டம்'),
    ('professional', 'Professional Qualification', 'වෘත්තීය සුදුසුකම', 'தொழில்முறை தகுதி'),
]


class Command(BaseCommand):
    help = 'Seed taxonomy data (provinces, districts, categories, skills, etc.)'

    def handle(self, *args, **options):
        self.stdout.write('Seeding taxonomy data...')

        # Provinces & Districts
        for prov_name, districts in PROVINCES_DISTRICTS.items():
            prov, _ = Province.objects.get_or_create(
                name_en=prov_name,
                defaults={'name_si': prov_name, 'name_ta': prov_name, 'slug': slugify(prov_name)},
            )
            for dist_name in districts:
                District.objects.get_or_create(
                    name_en=dist_name,
                    province=prov,
                    defaults={'name_si': dist_name, 'name_ta': dist_name, 'slug': slugify(dist_name)},
                )
        self.stdout.write(self.style.SUCCESS(f'  ✓ {Province.objects.count()} provinces, {District.objects.count()} districts'))

        # Categories & Subcategories
        order = 1
        for cat_name, subcats in CATEGORIES.items():
            cat, _ = JobCategory.objects.get_or_create(
                name_en=cat_name,
                defaults={
                    'name_si': cat_name, 'name_ta': cat_name,
                    'slug': slugify(cat_name),
                    'icon': 'briefcase',
                    'is_featured': order <= 8,
                    'order': order,
                },
            )
            for sub_order, sub_name in enumerate(subcats, 1):
                JobSubCategory.objects.get_or_create(
                    name_en=sub_name,
                    category=cat,
                    defaults={
                        'name_si': sub_name, 'name_ta': sub_name,
                        'slug': slugify(sub_name),
                        'order': sub_order,
                    },
                )
            order += 1
        self.stdout.write(self.style.SUCCESS(f'  ✓ {JobCategory.objects.count()} categories, {JobSubCategory.objects.count()} subcategories'))

        # Industries
        for ind_name in INDUSTRIES:
            Industry.objects.get_or_create(
                name_en=ind_name,
                defaults={'name_si': ind_name, 'name_ta': ind_name, 'slug': slugify(ind_name)},
            )
        self.stdout.write(self.style.SUCCESS(f'  ✓ {Industry.objects.count()} industries'))

        # Skills
        for skill_name in SKILLS:
            Skill.objects.get_or_create(
                name_en=skill_name,
                defaults={'slug': slugify(skill_name)},
            )
        self.stdout.write(self.style.SUCCESS(f'  ✓ {Skill.objects.count()} skills'))

        # Education Levels
        for code, en, si, ta in EDUCATION_LEVELS:
            EducationLevel.objects.get_or_create(
                code=code,
                defaults={'name_en': en, 'name_si': si, 'name_ta': ta, 'order': EDUCATION_LEVELS.index((code, en, si, ta)) + 1},
            )
        self.stdout.write(self.style.SUCCESS(f'  ✓ {EducationLevel.objects.count()} education levels'))

        self.stdout.write(self.style.SUCCESS('\nTaxonomy seed data completed!'))
