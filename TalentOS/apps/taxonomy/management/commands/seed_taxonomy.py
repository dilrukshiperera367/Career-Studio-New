"""
Management command: Seed the taxonomy tables with skills, title aliases, and location aliases.

Usage: python manage.py seed_taxonomy
"""

from django.core.management.base import BaseCommand

from apps.taxonomy.models import SkillTaxonomy, TitleAlias, LocationAlias


# ─── 200+ Technology / Professional Skills ────────────────────────────────

SKILLS = [
    # Programming Languages
    {"name": "Python", "category": "programming_language", "aliases": ["python", "python3", "py"]},
    {"name": "JavaScript", "category": "programming_language", "aliases": ["javascript", "js", "ecmascript"]},
    {"name": "TypeScript", "category": "programming_language", "aliases": ["typescript", "ts"]},
    {"name": "Java", "category": "programming_language", "aliases": ["java", "java8", "java11", "java17"]},
    {"name": "C#", "category": "programming_language", "aliases": ["c#", "csharp", "c sharp"]},
    {"name": "C++", "category": "programming_language", "aliases": ["c++", "cpp"]},
    {"name": "C", "category": "programming_language", "aliases": ["c programming", "c language"]},
    {"name": "Go", "category": "programming_language", "aliases": ["go", "golang"]},
    {"name": "Rust", "category": "programming_language", "aliases": ["rust", "rust language"]},
    {"name": "Ruby", "category": "programming_language", "aliases": ["ruby"]},
    {"name": "PHP", "category": "programming_language", "aliases": ["php", "php7", "php8"]},
    {"name": "Swift", "category": "programming_language", "aliases": ["swift"]},
    {"name": "Kotlin", "category": "programming_language", "aliases": ["kotlin"]},
    {"name": "Scala", "category": "programming_language", "aliases": ["scala"]},
    {"name": "R", "category": "programming_language", "aliases": ["r programming", "r language"]},
    {"name": "MATLAB", "category": "programming_language", "aliases": ["matlab"]},
    {"name": "Dart", "category": "programming_language", "aliases": ["dart"]},
    {"name": "Elixir", "category": "programming_language", "aliases": ["elixir"]},
    {"name": "Haskell", "category": "programming_language", "aliases": ["haskell"]},
    {"name": "Lua", "category": "programming_language", "aliases": ["lua"]},
    {"name": "Perl", "category": "programming_language", "aliases": ["perl"]},
    {"name": "Shell Scripting", "category": "programming_language", "aliases": ["bash", "shell", "shell scripting", "zsh"]},

    # Web Frameworks
    {"name": "Django", "category": "framework", "aliases": ["django", "django framework"]},
    {"name": "Flask", "category": "framework", "aliases": ["flask"]},
    {"name": "FastAPI", "category": "framework", "aliases": ["fastapi", "fast api"]},
    {"name": "React", "category": "framework", "aliases": ["react", "reactjs", "react.js"]},
    {"name": "Angular", "category": "framework", "aliases": ["angular", "angularjs", "angular.js"]},
    {"name": "Vue.js", "category": "framework", "aliases": ["vue", "vuejs", "vue.js"]},
    {"name": "Next.js", "category": "framework", "aliases": ["next.js", "nextjs", "next"]},
    {"name": "Nuxt.js", "category": "framework", "aliases": ["nuxt", "nuxtjs", "nuxt.js"]},
    {"name": "Svelte", "category": "framework", "aliases": ["svelte", "sveltekit"]},
    {"name": "Express.js", "category": "framework", "aliases": ["express", "expressjs", "express.js"]},
    {"name": "Node.js", "category": "framework", "aliases": ["node", "nodejs", "node.js"]},
    {"name": "Spring Boot", "category": "framework", "aliases": ["spring boot", "spring", "spring framework"]},
    {"name": "Ruby on Rails", "category": "framework", "aliases": ["rails", "ruby on rails", "ror"]},
    {"name": "Laravel", "category": "framework", "aliases": ["laravel"]},
    {"name": "ASP.NET", "category": "framework", "aliases": ["asp.net", "aspnet", "asp.net core", ".net core"]},
    {"name": ".NET", "category": "framework", "aliases": [".net", "dotnet", "dot net"]},
    {"name": "Flutter", "category": "framework", "aliases": ["flutter"]},
    {"name": "React Native", "category": "framework", "aliases": ["react native"]},
    {"name": "Tailwind CSS", "category": "framework", "aliases": ["tailwind", "tailwindcss", "tailwind css"]},
    {"name": "Bootstrap", "category": "framework", "aliases": ["bootstrap"]},

    # Databases
    {"name": "PostgreSQL", "category": "database", "aliases": ["postgresql", "postgres", "psql"]},
    {"name": "MySQL", "category": "database", "aliases": ["mysql"]},
    {"name": "MongoDB", "category": "database", "aliases": ["mongodb", "mongo"]},
    {"name": "Redis", "category": "database", "aliases": ["redis"]},
    {"name": "Elasticsearch", "category": "database", "aliases": ["elasticsearch", "elastic search", "elastic"]},
    {"name": "OpenSearch", "category": "database", "aliases": ["opensearch", "open search"]},
    {"name": "SQLite", "category": "database", "aliases": ["sqlite", "sqlite3"]},
    {"name": "Oracle Database", "category": "database", "aliases": ["oracle", "oracle db", "oracle database"]},
    {"name": "Microsoft SQL Server", "category": "database", "aliases": ["sql server", "mssql", "ms sql"]},
    {"name": "DynamoDB", "category": "database", "aliases": ["dynamodb", "dynamo db", "dynamo"]},
    {"name": "Cassandra", "category": "database", "aliases": ["cassandra", "apache cassandra"]},
    {"name": "Neo4j", "category": "database", "aliases": ["neo4j", "neo 4j"]},
    {"name": "Firebase", "category": "database", "aliases": ["firebase", "firestore"]},
    {"name": "Supabase", "category": "database", "aliases": ["supabase"]},

    # Cloud & DevOps
    {"name": "AWS", "category": "cloud", "aliases": ["aws", "amazon web services"]},
    {"name": "Azure", "category": "cloud", "aliases": ["azure", "microsoft azure"]},
    {"name": "Google Cloud", "category": "cloud", "aliases": ["gcp", "google cloud", "google cloud platform"]},
    {"name": "Docker", "category": "devops", "aliases": ["docker"]},
    {"name": "Kubernetes", "category": "devops", "aliases": ["kubernetes", "k8s"]},
    {"name": "Terraform", "category": "devops", "aliases": ["terraform"]},
    {"name": "Ansible", "category": "devops", "aliases": ["ansible"]},
    {"name": "Jenkins", "category": "devops", "aliases": ["jenkins"]},
    {"name": "GitHub Actions", "category": "devops", "aliases": ["github actions"]},
    {"name": "GitLab CI", "category": "devops", "aliases": ["gitlab ci", "gitlab ci/cd"]},
    {"name": "CircleCI", "category": "devops", "aliases": ["circleci", "circle ci"]},
    {"name": "Nginx", "category": "devops", "aliases": ["nginx"]},
    {"name": "Apache", "category": "devops", "aliases": ["apache", "apache http"]},
    {"name": "Linux", "category": "devops", "aliases": ["linux", "ubuntu", "centos", "debian"]},
    {"name": "Git", "category": "devops", "aliases": ["git", "version control"]},
    {"name": "CI/CD", "category": "devops", "aliases": ["ci/cd", "cicd", "continuous integration", "continuous deployment"]},
    {"name": "Helm", "category": "devops", "aliases": ["helm", "helm charts"]},
    {"name": "Prometheus", "category": "devops", "aliases": ["prometheus"]},
    {"name": "Grafana", "category": "devops", "aliases": ["grafana"]},
    {"name": "Datadog", "category": "devops", "aliases": ["datadog"]},

    # Data & ML
    {"name": "Machine Learning", "category": "data_science", "aliases": ["machine learning", "ml"]},
    {"name": "Deep Learning", "category": "data_science", "aliases": ["deep learning", "dl"]},
    {"name": "Natural Language Processing", "category": "data_science", "aliases": ["nlp", "natural language processing"]},
    {"name": "Computer Vision", "category": "data_science", "aliases": ["computer vision", "cv", "image recognition"]},
    {"name": "TensorFlow", "category": "data_science", "aliases": ["tensorflow", "tf"]},
    {"name": "PyTorch", "category": "data_science", "aliases": ["pytorch"]},
    {"name": "Scikit-learn", "category": "data_science", "aliases": ["scikit-learn", "sklearn", "scikit learn"]},
    {"name": "Pandas", "category": "data_science", "aliases": ["pandas"]},
    {"name": "NumPy", "category": "data_science", "aliases": ["numpy"]},
    {"name": "Apache Spark", "category": "data_science", "aliases": ["spark", "apache spark", "pyspark"]},
    {"name": "Apache Kafka", "category": "data_science", "aliases": ["kafka", "apache kafka"]},
    {"name": "Airflow", "category": "data_science", "aliases": ["airflow", "apache airflow"]},
    {"name": "dbt", "category": "data_science", "aliases": ["dbt", "data build tool"]},
    {"name": "Tableau", "category": "data_science", "aliases": ["tableau"]},
    {"name": "Power BI", "category": "data_science", "aliases": ["power bi", "powerbi"]},
    {"name": "SQL", "category": "data_science", "aliases": ["sql", "structured query language"]},
    {"name": "ETL", "category": "data_science", "aliases": ["etl", "extract transform load"]},
    {"name": "Data Warehousing", "category": "data_science", "aliases": ["data warehousing", "data warehouse", "dwh"]},
    {"name": "Snowflake", "category": "data_science", "aliases": ["snowflake"]},
    {"name": "BigQuery", "category": "data_science", "aliases": ["bigquery", "big query"]},
    {"name": "Hadoop", "category": "data_science", "aliases": ["hadoop", "apache hadoop"]},
    {"name": "LLM", "category": "data_science", "aliases": ["llm", "large language model", "large language models"]},

    # Testing
    {"name": "Unit Testing", "category": "testing", "aliases": ["unit testing", "unit tests"]},
    {"name": "Pytest", "category": "testing", "aliases": ["pytest"]},
    {"name": "Jest", "category": "testing", "aliases": ["jest"]},
    {"name": "Selenium", "category": "testing", "aliases": ["selenium"]},
    {"name": "Cypress", "category": "testing", "aliases": ["cypress"]},
    {"name": "Playwright", "category": "testing", "aliases": ["playwright"]},
    {"name": "JUnit", "category": "testing", "aliases": ["junit"]},
    {"name": "Test-Driven Development", "category": "testing", "aliases": ["tdd", "test driven development"]},

    # API & Integration
    {"name": "REST API", "category": "api", "aliases": ["rest api", "rest", "restful api", "restful"]},
    {"name": "GraphQL", "category": "api", "aliases": ["graphql"]},
    {"name": "gRPC", "category": "api", "aliases": ["grpc"]},
    {"name": "WebSocket", "category": "api", "aliases": ["websocket", "websockets"]},
    {"name": "OAuth", "category": "api", "aliases": ["oauth", "oauth2", "oauth 2.0"]},
    {"name": "JWT", "category": "api", "aliases": ["jwt", "json web token"]},
    {"name": "Swagger", "category": "api", "aliases": ["swagger", "openapi", "open api"]},
    {"name": "Postman", "category": "api", "aliases": ["postman"]},
    {"name": "RabbitMQ", "category": "api", "aliases": ["rabbitmq", "rabbit mq"]},
    {"name": "Celery", "category": "api", "aliases": ["celery"]},

    # Security
    {"name": "Cybersecurity", "category": "security", "aliases": ["cybersecurity", "cyber security"]},
    {"name": "Penetration Testing", "category": "security", "aliases": ["penetration testing", "pen testing", "pentest"]},
    {"name": "OWASP", "category": "security", "aliases": ["owasp"]},
    {"name": "Encryption", "category": "security", "aliases": ["encryption", "cryptography"]},
    {"name": "Security Compliance", "category": "security", "aliases": ["soc2", "soc 2", "iso 27001", "gdpr compliance"]},

    # Project Management & Methodologies
    {"name": "Agile", "category": "methodology", "aliases": ["agile", "agile methodology"]},
    {"name": "Scrum", "category": "methodology", "aliases": ["scrum"]},
    {"name": "Kanban", "category": "methodology", "aliases": ["kanban"]},
    {"name": "Jira", "category": "tool", "aliases": ["jira"]},
    {"name": "Confluence", "category": "tool", "aliases": ["confluence"]},
    {"name": "Figma", "category": "tool", "aliases": ["figma"]},
    {"name": "Sketch", "category": "tool", "aliases": ["sketch"]},

    # Architecture
    {"name": "Microservices", "category": "architecture", "aliases": ["microservices", "microservice architecture"]},
    {"name": "Event-Driven Architecture", "category": "architecture", "aliases": ["event driven architecture", "eda", "event driven"]},
    {"name": "Domain-Driven Design", "category": "architecture", "aliases": ["ddd", "domain driven design"]},
    {"name": "System Design", "category": "architecture", "aliases": ["system design"]},
    {"name": "Design Patterns", "category": "architecture", "aliases": ["design patterns"]},
    {"name": "SOLID Principles", "category": "architecture", "aliases": ["solid", "solid principles"]},

    # Soft Skills & Business
    {"name": "Leadership", "category": "soft_skill", "aliases": ["leadership", "team leadership"]},
    {"name": "Communication", "category": "soft_skill", "aliases": ["communication", "communication skills"]},
    {"name": "Problem Solving", "category": "soft_skill", "aliases": ["problem solving"]},
    {"name": "Teamwork", "category": "soft_skill", "aliases": ["teamwork", "team collaboration"]},
    {"name": "Project Management", "category": "soft_skill", "aliases": ["project management"]},
    {"name": "Stakeholder Management", "category": "soft_skill", "aliases": ["stakeholder management"]},
    {"name": "Technical Writing", "category": "soft_skill", "aliases": ["technical writing"]},
    {"name": "Data Analysis", "category": "business", "aliases": ["data analysis", "data analytics"]},
    {"name": "Business Intelligence", "category": "business", "aliases": ["business intelligence", "bi"]},
    {"name": "CRM", "category": "business", "aliases": ["crm", "salesforce", "hubspot"]},
    {"name": "SAP", "category": "business", "aliases": ["sap", "sap erp"]},
    {"name": "Financial Modeling", "category": "business", "aliases": ["financial modeling", "financial modelling"]},
    {"name": "Product Management", "category": "business", "aliases": ["product management"]},
    {"name": "UX Design", "category": "design", "aliases": ["ux", "ux design", "user experience"]},
    {"name": "UI Design", "category": "design", "aliases": ["ui", "ui design", "user interface"]},
    {"name": "Wireframing", "category": "design", "aliases": ["wireframing", "wireframes"]},
    {"name": "Adobe Creative Suite", "category": "design", "aliases": ["photoshop", "illustrator", "adobe creative suite", "adobe xd"]},
]


# ─── Title Aliases ────────────────────────────────────────────────────────

TITLE_ALIASES = {
    # Software Engineering
    "Software Engineer": [
        "software engineer", "software developer", "swe", "sde",
        "software dev", "programmer", "coder", "application developer",
    ],
    "Senior Software Engineer": [
        "senior software engineer", "sr software engineer", "senior swe",
        "sr. software engineer", "senior developer", "sr developer",
        "senior software developer", "lead developer",
    ],
    "Staff Software Engineer": [
        "staff software engineer", "staff engineer", "staff swe",
        "principal engineer",
    ],
    "Frontend Developer": [
        "frontend developer", "front end developer", "front-end developer",
        "frontend engineer", "front end engineer", "ui developer",
    ],
    "Backend Developer": [
        "backend developer", "back end developer", "back-end developer",
        "backend engineer", "server side developer",
    ],
    "Full Stack Developer": [
        "full stack developer", "fullstack developer", "full-stack developer",
        "full stack engineer", "fullstack engineer",
    ],
    "DevOps Engineer": [
        "devops engineer", "devops", "site reliability engineer", "sre",
        "platform engineer", "infrastructure engineer",
    ],
    "QA Engineer": [
        "qa engineer", "quality assurance engineer", "test engineer",
        "sdet", "qa analyst", "quality analyst",
    ],
    "Mobile Developer": [
        "mobile developer", "ios developer", "android developer",
        "mobile engineer", "mobile application developer",
    ],

    # Data
    "Data Scientist": [
        "data scientist", "ml engineer", "machine learning engineer",
        "ai engineer", "applied scientist",
    ],
    "Data Engineer": [
        "data engineer", "etl developer", "data pipeline engineer",
        "big data engineer",
    ],
    "Data Analyst": [
        "data analyst", "business analyst", "analytics analyst",
        "reporting analyst", "insights analyst",
    ],

    # Management
    "Engineering Manager": [
        "engineering manager", "em", "software engineering manager",
        "dev manager", "development manager",
    ],
    "Product Manager": [
        "product manager", "pm", "product owner", "po",
        "associate product manager", "apm",
    ],
    "Project Manager": [
        "project manager", "program manager", "pmo",
        "technical project manager", "tpm",
    ],
    "CTO": [
        "cto", "chief technology officer", "vp engineering",
        "vp of engineering", "vice president engineering",
    ],

    # Design
    "UX Designer": [
        "ux designer", "user experience designer", "ux/ui designer",
        "ui/ux designer", "product designer", "interaction designer",
    ],
    "UI Designer": [
        "ui designer", "user interface designer", "visual designer",
        "graphic designer",
    ],

    # Other
    "Solutions Architect": [
        "solutions architect", "cloud architect", "enterprise architect",
        "technical architect", "system architect",
    ],
    "Security Engineer": [
        "security engineer", "information security engineer",
        "cybersecurity engineer", "appsec engineer",
    ],
    "Database Administrator": [
        "database administrator", "dba", "database engineer",
    ],
    "Technical Writer": [
        "technical writer", "documentation engineer", "content developer",
    ],
    "Scrum Master": [
        "scrum master", "agile coach", "agile lead",
    ],
}


# ─── Location Aliases ─────────────────────────────────────────────────────

LOCATION_ALIASES = {
    # US Cities
    "San Francisco, CA, US": ["san francisco", "sf", "san francisco bay area", "bay area"],
    "New York, NY, US": ["new york", "nyc", "new york city", "manhattan"],
    "Seattle, WA, US": ["seattle"],
    "Austin, TX, US": ["austin"],
    "Chicago, IL, US": ["chicago"],
    "Los Angeles, CA, US": ["los angeles", "la"],
    "Boston, MA, US": ["boston"],
    "Denver, CO, US": ["denver"],
    "Atlanta, GA, US": ["atlanta"],
    "Portland, OR, US": ["portland"],
    "San Jose, CA, US": ["san jose"],
    "Miami, FL, US": ["miami"],
    "Dallas, TX, US": ["dallas"],
    "Washington, DC, US": ["washington dc", "dc"],
    "Philadelphia, PA, US": ["philadelphia", "philly"],
    "San Diego, CA, US": ["san diego"],
    "Minneapolis, MN, US": ["minneapolis"],
    "Raleigh, NC, US": ["raleigh", "raleigh-durham"],
    "Nashville, TN, US": ["nashville"],
    "Salt Lake City, UT, US": ["salt lake city", "slc"],

    # International
    "London, UK": ["london"],
    "Berlin, DE": ["berlin"],
    "Amsterdam, NL": ["amsterdam"],
    "Paris, FR": ["paris"],
    "Dublin, IE": ["dublin"],
    "Toronto, CA": ["toronto"],
    "Vancouver, CA": ["vancouver"],
    "Sydney, AU": ["sydney"],
    "Melbourne, AU": ["melbourne"],
    "Singapore, SG": ["singapore"],
    "Bangalore, IN": ["bangalore", "bengaluru"],
    "Mumbai, IN": ["mumbai"],
    "Hyderabad, IN": ["hyderabad"],
    "Tokyo, JP": ["tokyo"],
    "Tel Aviv, IL": ["tel aviv"],
    "São Paulo, BR": ["sao paulo", "são paulo"],
    "Stockholm, SE": ["stockholm"],
    "Zurich, CH": ["zurich", "zürich"],
    "Remote": ["remote", "work from home", "wfh", "anywhere"],
}


class Command(BaseCommand):
    help = "Seed taxonomy tables with skills, title aliases, and location aliases"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing taxonomy data before seeding",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing taxonomy data...")
            SkillTaxonomy.objects.all().delete()
            TitleAlias.objects.all().delete()
            LocationAlias.objects.all().delete()

        # ─── Skills ───────────────────────────────────────────────────
        skill_count = 0
        alias_count = 0
        for skill_data in SKILLS:
            skill, created = SkillTaxonomy.objects.update_or_create(
                canonical_name=skill_data["name"],
                defaults={
                    "category": skill_data["category"],
                },
            )
            if created:
                skill_count += 1

            # Create SkillAlias records for fast lookup
            from apps.taxonomy.models import SkillAlias
            for alias_text in skill_data["aliases"]:
                _, alias_created = SkillAlias.objects.update_or_create(
                    skill=skill,
                    alias_normalized=alias_text.lower().strip(),
                )
                if alias_created:
                    alias_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Skills: {skill_count} created, {alias_count} aliases"
        ))

        # ─── Title Aliases ────────────────────────────────────────────
        title_count = 0
        for canonical, aliases in TITLE_ALIASES.items():
            for alias_text in aliases:
                _, created = TitleAlias.objects.update_or_create(
                    alias_normalized=alias_text.lower().strip(),
                    defaults={"canonical_title": canonical},
                )
                if created:
                    title_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Title aliases: {title_count} created"
        ))

        # ─── Location Aliases ─────────────────────────────────────────
        loc_count = 0
        for canonical, aliases in LOCATION_ALIASES.items():
            # Parse canonical into city, country_code
            parts = canonical.split(", ")
            city = parts[0]
            country_code = parts[-1] if len(parts) > 1 else ""

            for alias_text in aliases:
                _, created = LocationAlias.objects.update_or_create(
                    alias_normalized=alias_text.lower().strip(),
                    defaults={
                        "city": city,
                        "country_code": country_code,
                    },
                )
                if created:
                    loc_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Location aliases: {loc_count} created"
        ))

        self.stdout.write(self.style.SUCCESS(
            "\nTaxonomy seeding complete!"
        ))
