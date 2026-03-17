# ATS System Backend — Comprehensive Audit Report

**Generated:** 2025  
**Scope:** `ATS System/backend/` — every `.py` file in `apps/`, `config/`, `tests/`, management commands, and configuration files.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Config / Settings](#3-config--settings)
4. [Per-App Audit](#4-per-app-audit)
   - [accounts](#41-accounts)
   - [analytics](#42-analytics)
   - [applications](#43-applications)
   - [blog](#44-blog)
   - [candidates](#45-candidates)
   - [consent](#46-consent)
   - [jobs](#47-jobs)
   - [messaging](#48-messaging)
   - [notifications](#49-notifications)
   - [parsing](#410-parsing)
   - [portal](#411-portal)
   - [scoring](#412-scoring)
   - [search](#413-search)
   - [shared](#414-shared)
   - [taxonomy](#415-taxonomy)
   - [tenants](#416-tenants)
   - [workflows](#417-workflows)
5. [Test Suite Audit](#5-test-suite-audit)
6. [Management Commands](#6-management-commands)
7. [Migration State](#7-migration-state)
8. [Cross-Cutting Concerns](#8-cross-cutting-concerns)
9. [Issues, Bugs & Risks](#9-issues-bugs--risks)
10. [Recommendations](#10-recommendations)

---

## 1. Executive Summary

| Metric | Value |
|---|---|
| **Framework** | Django 5.1 + DRF 3.15 |
| **Python** | 3.12+ |
| **Apps** | 17 Django apps |
| **Models** | ~60 models |
| **API Views/ViewSets** | ~80+ views |
| **URL patterns** | ~120+ |
| **Celery Tasks** | ~15 async tasks + 10 periodic beat tasks |
| **Test Files** | 7 (conftest + 6 test modules, ~1,500 LOC) |
| **Management Commands** | 4 (seed_demo, seed_ats, seed_demo_data, seed_taxonomy) |
| **Total Backend LOC** | ~12,000–14,000 |
| **Migrations** | 30 migration files across 11 apps |

The backend is a **multi-tenant ATS (Applicant Tracking System)** with:
- PostgreSQL + Row-Level Security for tenant isolation
- JWT auth (SimpleJWT) with custom claims embedding `tenant_id`
- Resume parsing pipeline (pdfplumber + spaCy NLP + Tesseract OCR)
- Deterministic 0–100 candidate scoring engine (no AI APIs)
- OpenSearch for full-text candidate search with hybrid BM25 + structured ranking
- Celery + Redis for async tasks (email, parsing, scoring, analytics, GDPR exports)
- Cross-system integration with an HRM system (webhooks, shared JWT)

---

## 2. Architecture Overview

### Tech Stack
| Component | Technology |
|---|---|
| Web Framework | Django 5.1, Django REST Framework 3.15 |
| Auth | `rest_framework_simplejwt` (30-min access, 7-day refresh) |
| Database | PostgreSQL (RLS), SQLite fallback for dev |
| Task Queue | Celery 5.4 + Redis |
| Cache | Redis (django-redis) |
| Search | OpenSearch (opensearch-py) |
| File Storage | S3/MinIO (boto3, django-storages) |
| NLP | spaCy, pdfplumber, python-docx, Tesseract |
| Dedup | jellyfish (fuzzy string matching) |
| Monitoring | Sentry (sentry-sdk) |
| Testing | pytest, pytest-django |

### Middleware Stack (8 layers)
1. `SecurityHeadersMiddleware` — X-Content-Type-Options, CSP, HSTS
2. `RequestLoggingMiddleware` — per-request timing + audit log
3. `LoginThrottleMiddleware` — brute-force protection (5 attempts / 5 min, 15-min lockout)
4. `AuditLogMiddleware` — write-operation audit trail (POST/PUT/PATCH/DELETE) with DB persistence
5. `CORSValidationMiddleware` — X-Frame-Options: DENY
6. `TenantMiddleware` — extracts tenant_id from JWT, sets PostgreSQL RLS context via `SET app.tenant_id`

### Multi-Tenancy Model
- Every model has a `tenant` or `tenant_id` FK → `tenants.Tenant`
- `TenantMiddleware` extracts `tenant_id` from JWT claims
- In production, PostgreSQL RLS policies enforce isolation at database level
- In dev (SQLite), isolation is enforced at ORM queryset level

---

## 3. Config / Settings

### `config/settings.py` (476 lines)
- `AUTH_USER_MODEL = "accounts.User"` — custom UUID-PK user model
- All 17 apps registered in `INSTALLED_APPS`
- `REST_FRAMEWORK` config: pagination (50/page), JWT auth, throttling (anon: 100/day, user: 1000/day)
- `RANKING_WEIGHTS` for structured + hybrid scoring
- `RESUME_PARSING` config (10MB max, PDF/DOCX only, `en_core_web_sm` spaCy model)
- `CANDIDATE_DEDUP_THRESHOLDS` (auto-link: 0.92, flag: 0.85)
- `CACHING` config (Redis, TTL: default 300s, search results 60s, analytics 600s)
- `CELERY_BEAT_SCHEDULE` with 10 periodic tasks

### `config/urls.py`
- `/health/` and `/ready/` — health probes
- `/api/v1/auth/` → accounts
- `/api/v1/candidates/` → candidates
- `/api/v1/jobs/` → jobs
- `/api/v1/applications/` → applications (+ interviews, offers, team sub-routes)
- `/api/v1/messaging/` → messaging (via shared.api)
- `/api/v1/analytics/` → analytics (via shared.api)
- `/api/v1/portal/` → portal (via shared.api)
- `/api/v1/notifications/` → notifications (via shared.api)
- `/api/v1/compliance/` → compliance (via shared.api)
- `/api/v1/search/` → search
- `/api/v1/scoring/` → scoring
- `/api/v1/workflows/` → workflows
- `/api/v1/tenants/` → tenants
- `/api/v1/taxonomy/` → taxonomy
- `/api/v1/blog/` → blog
- `/api/v1/consent/` → consent
- `/api/v1/integrations/hrm/webhook/` → HRM webhook receiver
- `/api/v1/scorecards/` → scorecard templates/submissions (via dynamic import)

### `config/celery.py`
- Broker: Redis
- 10 beat tasks: idle apps check, daily analytics, scheduled messages, bounce processing, stale candidates, search index refresh, offer expirations, weekly report, audit log partitions

### `config/asgi.py` / `config/wsgi.py`
- Standard Django ASGI/WSGI application factory

### `requirements.txt` (25+ packages)
- Django 5.1, DRF, SimpleJWT, Celery 5.4, boto3, opensearch-py, pdfplumber, python-docx, pytesseract, spacy, jellyfish, sentry-sdk, gunicorn, psycopg2-binary, django-redis, django-cors-headers, django-storages, pytest, pytest-django, PyJWT

---

## 4. Per-App Audit

---

### 4.1 accounts

**Models** (`models.py`, ~300 lines):
| Model | Purpose | Key Fields |
|---|---|---|
| `User` | Custom auth model (UUID PK) | email (unique login), tenant FK, user_type (company_admin/recruiter/hiring_manager/interviewer/candidate), MFA fields (mfa_enabled, mfa_secret, mfa_verified_at), is_active, date_joined |
| `Role` | Named role per tenant | tenant, name, slug, permissions (JSONField), is_system |
| `UserRole` | M2M: User → Role | user FK, role FK, unique_together |
| `Notification` | In-app notifications | user, tenant, notification_type, title, body, entity_type/entity_id, is_read, link, metadata (JSON) |
| `UserNotificationPreference` | Per-event notification prefs | user, event_type, email_enabled, in_app_enabled |
| `PasswordResetToken` | Password reset tokens | user, token (UUID), expires_at, used |
| `InviteToken` | User invite tokens | email, tenant, role, token (UUID), expires_at, accepted |

**PERMISSIONS dict:** 5 role templates (admin, recruiter, hiring_manager, interviewer, candidate) with granular permissions.

**Views** (`views.py`, 465 lines):
- `CompanyRegisterView` — creates tenant + admin user + default roles + TenantSettings
- `CandidateRegisterView` — standalone candidate registration
- `RegisterView` — legacy company registration (backward compat)
- `LoginView` — JWT token pair with custom claims (tenant_id, user_type, roles)
- `MeView` — GET/PUT current user profile
- `UserListView` — admin list/filter users by tenant
- `ChangePasswordView`, `ForgotPasswordView`, `ResetPasswordView` — password flows
- `InviteUserView` / `InviteAcceptView` — user invite with expiring tokens
- `UserDeactivateView` — soft deactivation
- `MFAEnableView` / `MFAVerifyView` / `MFADisableView` — TOTP MFA lifecycle

**Serializers** (`serializers.py`):
- UserSerializer, CompanyRegisterSerializer, CandidateRegisterSerializer, UserCreateSerializer, TokenObtainSerializer (custom claims), RoleSerializer, UserRoleSerializer

**Permissions** (`permissions.py`):
- `HasTenantAccess` — verifies user.tenant_id matches request.tenant_id
- `HasPermission` — checks permission string against user roles
- `IsTenantAdmin`, `IsRecruiter`, `IsHiringManager`, `IsInterviewer` — role shortcuts

**Cross-Auth** (`cross_auth.py`):
- `CrossSystemTokenObtainPairSerializer` — JWT for ATS↔HRM module switching
- `build_module_switch_url()`, `validate_cross_system_token()` — shared secret validation

**URLs** (16 patterns): register, login, me, users, password flows, invite, MFA, deactivate, roles

**Migrations:** 6 (initial → user_type → notifications → tokens → MFA → audit log partition)

**Issues:**
- ⚠️ `CompanyRegisterView` creates the Tenant + admin user in a single non-atomic request body — a failure midway could leave an orphan tenant. Should wrap in `transaction.atomic()`.
- ⚠️ `LoginThrottleMiddleware` uses in-memory dict (`_attempts`) — not shared across workers in production. Settings comment says "use Redis in production" but no Redis implementation exists.
- ⚠️ No email verification on `CompanyRegisterView` or `CandidateRegisterView` — accounts are immediately active.

---

### 4.2 analytics

**Models** (`models.py`):
| Model | Purpose |
|---|---|
| `AnalyticsDaily` | Pre-computed daily metrics per job (metric name, value, metadata JSON, computed_date) |
| `SavedReport` | Custom reports with scheduling (name, report_type, query_config JSON, schedule, recipients JSON) |

**Tasks** (`tasks.py`, `tasks_extra.py`):
- `compute_daily_analytics` — applications/day, time-in-stage, source quality
- `generate_weekly_report` — weekly summary

**Utils** (`utils.py`, 358 lines):
- `generate_trend_report()` — month-over-month hiring trends
- `rejection_analytics()` — rejection reasons by stage/job/department
- `interview_to_hire_ratio()` — interviews per hire
- `offer_comparison()` — current vs historical offers
- `voting_tally()` — hiring committee vote aggregation
- `score_comparison_across_jobs()` — candidate score comparison
- `batch_rescore()` — re-score all candidates against updated JD

**Views:** Defined in `shared/api.py` — 20+ analytics URL patterns

**URLs:** Delegates to `shared.api.analytics_urlpatterns`

**Serializers:** `AnalyticsDailySerializer`, `SavedReportSerializer` (in shared/api.py)

**Issues:**
- ⚠️ No `views.py` or `serializers.py` in this app directory — all API code lives in `shared/api.py`. This breaks the standard Django app pattern and makes the app harder to reason about independently.
- ⚠️ `KPIDashboardView` in shared/api.py iterates `hired_apps[:100]` in Python to compute `avg_time_to_hire` — this won't scale. Should use database aggregation.

---

### 4.3 applications

**Models** (`models.py`, ~500 lines):
| Model | Purpose | Key Fields |
|---|---|---|
| `Application` | Core application record | candidate FK, job FK, current_stage FK, status (active/hired/rejected/withdrawn), source, score, rejection_reason, priority, on_hold, assigned_recruiter, checklist (JSON), unique_together(tenant,job,candidate) |
| `StageHistory` | Immutable audit trail | application FK, from_stage, to_stage, moved_by, notes, timestamps |
| `Evaluation` | Interviewer scorecards | application FK, evaluator FK, rating 1-5, strengths/weaknesses/notes |
| `Interview` | Interview scheduling | application FK, candidate FK, job FK, interviewer FK, type (phone/video/onsite/panel/take_home), round_number/round_name, date/time/duration, status, feedback, rating, no_show, panel_size, location |
| `InterviewPanel` | Panel interview members | interview FK, panelist FK, role, feedback, rating |
| `InterviewScorecard` | Per-criterion scores | interview FK, panelist FK, criteria (JSON), overall_rating, recommendation |
| `Offer` | Offer management | application FK, salary_offered/currency, valid_until, status (draft/pending/accepted/declined/expired), negotiation_history (JSON), decline_reason, approval_chain (JSON), hrm_employee_id/number |
| `Employee` | Post-hire tracking | application FK, candidate FK, hire_date, department, title, 30/60/90 day goals, onboarding status |
| `OnboardingTask` | Onboarding checklist | employee FK, title, description, category, status, due_date, completed_at |

**Views** (`api.py`, 701 lines):
- `ApplicationViewSet` — full CRUD + `move_stage`, `reject`, `bulk_move_stage`, `bulk_reject`, `toggle_priority`, `toggle_hold`, `revive`
- `EvaluationViewSet` — interviewer scorecard CRUD
- `InterviewViewSet` — CRUD + `add_panel_member`, `submit_feedback`, `set_decision`, `calendar`, `workload`
- `OfferViewSet` — CRUD + `accept` (creates Employee + dispatches HRM webhook), `decline`, `negotiate`
- `EmployeeViewSet` — CRUD + `onboarding` tasks, `complete_task`
- `TeamViewSet` — team collaboration views

**URLs:** Router-based + manual patterns for interviews, offers, team

**Migrations:** 4 (initial → interviews/offers → employee/panel/scorecard → HRM fields)

**Issues:**
- ⚠️ `OfferViewSet.accept()` creates an `Employee` record and dispatches an HRM webhook in the same synchronous request — if the webhook fails, the employee is still created but HRM isn't notified. Should use Celery task for webhook dispatch (the code does call `send_webhook_task.delay()` but error handling is `try/except pass`).
- ⚠️ `move_stage` action doesn't validate that the target stage belongs to the same job's pipeline — a user could move an application to a stage from a different job.
- ⚠️ `Application` model has both `current_stage` (FK) and `current_stage_name` (CharField) — potential for data inconsistency.

---

### 4.4 blog

**Models** (`models.py`):
| Model | Purpose |
|---|---|
| `BlogCategory` | Blog categories | name, slug |
| `BlogPost` | Blog articles | title, slug, body (Markdown), category FK, author FK, status (draft/published), SEO fields (meta_title, meta_description), featured, view_count |

**Views** (`views.py`):
- Public: `PublicPostListView`, `PublicPostDetailView`, `PublicCategoryListView`
- Admin: `AdminPostListCreateView`, `AdminPostDetailView`, `admin_toggle_publish`, `AdminCategoryListCreateView`, `AdminCategoryDetailView`

**Serializers** (`serializers.py`): BlogCategorySerializer, BlogPostListSerializer, BlogPostDetailSerializer, BlogPostAdminSerializer

**URLs:** 8 patterns (3 public + 5 admin)

**Admin:** BlogCategory and BlogPost registered

**Issues:**
- ⚠️ No tenant scoping on blog models — blog posts are global. If this is intentional (company marketing blog), it should be documented. If not, posts need a `tenant` FK.
- ℹ️ No migrations directory shown — likely uses an empty migration auto-generated by Django.

---

### 4.5 candidates

**Models** (`models.py`, ~400 lines):
| Model | Purpose |
|---|---|
| `Candidate` | Core candidate record (comprehensive) | full_name, primary_email, primary_phone, headline, location, source, status, pool_status, talent_tier, availability, total_experience_years, most_recent_title/company, recency_score, extracted_skills (JSON), tags (JSON), GDPR fields (gdpr_deletion_requested_at, consent tracking), resume_completeness |
| `CandidateIdentity` | Multi-identity dedup | candidate FK, identity_type (email/phone/linkedin/github), identity_value, unique_together(tenant,identity_type,identity_value) |
| `ResumeDocument` | Resume file versions | candidate FK, version, file_url, file_type, raw_text, clean_text, parsed_json (JSON) |
| `CandidateSkill` | Extracted skills | candidate FK, skill_id (taxonomy FK), canonical_name, confidence, last_seen |
| `CandidateExperience` | Work history | candidate FK, company, title, start_date/end_date, description |
| `CandidateEducation` | Education history | candidate FK, institution, degree, field, start/end |
| `MergeAudit` | Candidate merge trail | primary/secondary candidate, merged_by, fields_merged JSON |
| `CandidateNote` | Threaded notes | candidate FK, author FK, content, parent FK (threading), mentions (JSON) |
| `CandidateCertification` | Certifications | candidate FK, name, issuer, date |

**Views** (`api.py`, 397 lines):
- `CandidateViewSet` — full CRUD + `upload_resume` (file validation + async parse trigger), `notes`, `certifications_list`, `timeline`, `export_csv`, `bulk_import`, `compare`

**Services** (`services.py`):
- `resolve_candidate()` — 3-tier dedup: exact identity match → fuzzy name/company/LinkedIn → flag/create
- `merge_candidates()` — tombstone pattern merge with `MergeAudit` trail

**Utils** (`utils.py`, 459 lines):
- `validate_email`, `validate_phone`, `validate_candidate_contacts`
- `compute_resume_completeness`
- `flag_stale_candidates`, `bulk_data_cleanup`
- `purge_candidate_data` (GDPR Article 17 — anonymizes PII, deletes identities/notes/certs, purges resume text)
- `parse_mentions` + `process_note_mentions` (@mention parsing → notifications)
- `check_interview_conflicts` (scheduling conflict detection)
- `calculate_cost_per_hire` (estimated cost metrics)
- `suggest_buddy` (mentor auto-suggestion for new hires)
- `check_early_attrition` (employees who left within 90 days)

**URLs:** Router-based CandidateViewSet

**Migrations:** 5 (initial → notes/certs → GDPR fields → RLS isolation → GIN indexes)

**Issues:**
- ⚠️ `Candidate` model has both old-style fields (`name`, `email`) and new-style fields (`full_name`, `primary_email`). The `api.py` references `first_name`/`last_name` in some places and `name` in others. This inconsistency suggests a partially-completed field migration. Several factory/test files also use mixed field names.
- ⚠️ `upload_resume` action doesn't appear to call ClamAV scanning (`shared.clamav.scan_file`) before storing files.
- ⚠️ `check_interview_conflicts` references `interview.candidate` but `Interview` model FK goes to application, not directly to candidate — may need a join.

---

### 4.6 consent

**Models** (`models.py`):
| Model | Purpose |
|---|---|
| `ConsentRecord` | GDPR consent tracking | candidate FK, consent_type (data_processing/marketing/third_party_sharing/retention), granted, granted_at, revoked_at, ip_address |
| `DataRequest` | GDPR data export/deletion requests | candidate FK, request_type (export/deletion), status (pending/processing/completed/failed), result_url, completed_at |

**Views** (`views.py`, 261 lines):
- `ConsentRecordView` — list/create consent records
- `CandidateSelfConsentView` — public self-service consent management
- `DataRequestView` — create export/deletion requests, triggers async tasks
- `DataRequestDetailView` — check request status
- `ConsentSummaryView` — aggregate consent stats for admin dashboard

**Tasks** (`tasks.py`, 241 lines):
- `process_data_export` — builds ZIP (profile JSON + applications JSON + consents JSON + resume files from S3), uploads to S3, generates presigned URL (72h)
- `process_data_deletion` — GDPR Article 17 right to erasure, anonymizes PII, revokes consents
- `auto_purge_expired_candidates` — daily task: hard-deletes candidates past 30-day grace period

**Serializers:** ConsentRecordSerializer, ConsentGrantSerializer, DataRequestSerializer, DataRequestCreateSerializer

**URLs:** 5 patterns (consent records, self-service, data requests, request detail, summary)

**Migrations:** 1 (initial)

**Issues:**
- ℹ️ Solid GDPR implementation with proper consent lifecycle, data export, right-to-erasure, and auto-purge.
- ⚠️ `auto_purge_expired_candidates` task not listed in `CELERY_BEAT_SCHEDULE` in settings.py — may not be running.

---

### 4.7 jobs

**Models** (`models.py`):
| Model | Purpose |
|---|---|
| `Job` | Job posting | title, slug, department, location, is_remote, employment_type, status (draft/open/closed/archived), description, screening_questions (JSON), priority, internal_only, application_deadline, requisition_id, headcount_target/filled, salary_min/max/currency, required_skills/optional_skills (JSON), view_count, published_at |
| `JobTemplate` | Reusable job templates | name, template_data (JSON), category |
| `PipelineStage` | Configurable hiring stages per job | job FK, name, stage_type, order, is_terminal, sla_days, checklist (JSON), notes_template |

**Views** (`api.py`):
- `JobViewSet` — full CRUD + `publish`, `close`, `clone`, `analytics`
- `PipelineStageViewSet` — CRUD for pipeline stages
- `JobTemplateViewSet` — CRUD + `create_job` from template

**URLs:** Router-based + manual patterns for templates and stages

**Migrations:** 3 (initial → template + deadline fields → GIN indexes)

**Issues:**
- ⚠️ `PipelineStage.job` FK is nullable in some tests — stages can exist without a job, which could cause issues in pipeline logic.

---

### 4.8 messaging

**Models** (`models.py`):
| Model | Purpose |
|---|---|
| `EmailTemplate` | Email templates with variable substitution | slug, name, subject, body, category, is_active |
| `Message` | Email/SMS messages | candidate FK, application FK, sender FK, channel (email/sms/in_app), direction (outbound/inbound), subject, body, status (queued/sending/sent/failed/scheduled), thread_id, tracking_id, opened_at, clicked_at, scheduled_for |
| `ActivityLog` | Messaging audit trail | actor, action, target, metadata, user_agent |

**Services** (`services.py`, 358 lines):
- `queue_email()` — create Message record + render template
- `send_email()` — per-tenant SMTP support + fallback to Django default
- `_render_template()` — `{{variable}}` replacement
- `send_bulk_email()` — batch email with thread_id tracking
- `schedule_email()` — future delivery scheduling
- `send_scheduled_emails()` — periodic task: send all due scheduled emails
- `process_bounces()` — flag candidates with 3+ failed emails
- `track_open()` / `track_click()` — email engagement tracking
- `get_email_thread()` — retrieve threaded conversation

**Tasks** (`tasks.py`): `send_email_task` — async send

**URLs:** Delegates to `shared.api.messaging_urlpatterns`

**Views:** Defined in `shared/api.py` — `MessageViewSet`, `EmailTemplateViewSet`

**Migrations:** 2 (initial → tracking/thread/scheduled fields)

**Issues:**
- ⚠️ `send_email_task` in `messaging/tasks.py` (17 lines) takes a `message_id` arg, while `shared/tasks.py` has a separate `send_email_task` that takes `to_email, subject, body`. Two different tasks with the same conceptual name — could cause confusion.
- ⚠️ Template rendering uses simple string replacement (`{{variable}}`) — no sandboxing or escaping. Malicious template content could be a security risk.

---

### 4.9 notifications

**Files:** Only `urls.py` and `compliance_urls.py` — no models, views, or serializers in this app directory.

**URLs:**
- `urls.py` → `shared.api.notification_urlpatterns`
- `compliance_urls.py` → `shared.api.compliance_urlpatterns`

**Actual implementation:** All notification views live in `shared/api.py`:
- `NotificationListView` — list/mark-read notifications
- `NotificationPreferencesView` — manage per-event preferences
- `UnifiedNotificationView` — merged ATS + HRM notifications (remote fetch from HRM API)

**Issues:**
- ⚠️ This app is essentially a URL routing stub — all logic lives in `shared`. Consider merging with shared or moving views here.
- ⚠️ Notification models (`Notification`, `UserNotificationPreference`) are defined in `accounts.models` instead of here — split responsibility.

---

### 4.10 parsing

**Services** (`services.py`, 575 lines) — Full resume parsing pipeline:
1. `extract_text()` — PDF (pdfplumber), DOCX (python-docx), OCR (Tesseract) with fallback chain
2. `clean_text()` — normalize bullets, dehyphenation, collapse whitespace, strip page numbers
3. `detect_sections()` — heading detection via `HEADING_MAP` dictionary + uppercase detection + fallback pattern-based
4. `extract_contact_info()` — regex for emails, phones, LinkedIn, GitHub
5. `extract_date_ranges()` — flexible date patterns (Jan 2020 – Present, 2019-2023)
6. `extract_experience_blocks()` — date-range anchored ±3 line window, title/company extraction
7. `extract_skills()` — n-gram (1-3 words) matching against taxonomy alias map
8. `normalize_title()`, `normalize_location()`, `parse_fuzzy_date()`
9. `compute_derived_fields()` — total_years (merged non-overlapping intervals), recent title/company, recency score (exponential decay)
10. `parse_resume_full()` — orchestrator: extract → clean → sections → entities → derived

**Tasks** (`tasks.py`):
- `parse_resume` — full pipeline: fetch file → parse → update ResumeDocument → update Candidate derived fields → persist skills/experiences → trigger OpenSearch indexing
- `index_candidate` — add/update candidate in OpenSearch

**Issues:**
- ⚠️ No `models.py`, `views.py`, `serializers.py`, or `urls.py` — this is a pure service module. Not a standard Django app pattern.
- ⚠️ `extract_text()` doesn't call ClamAV scanning before processing files. Should validate files before parsing.
- ⚠️ OCR fallback (Tesseract) is imported at call time with `try/except` — if not installed, silently returns empty text. Should log a warning.

---

### 4.11 portal

**Models** (`models.py`):
| Model | Purpose |
|---|---|
| `JobAlert` | Job alert subscriptions | tenant FK, email, name, keywords (JSON), department, location |
| `CandidateFeedback` | Post-rejection survey | tenant FK, candidate FK, application FK, overall_rating, comments, would_apply_again |
| `PortalToken` | Token-based self-service access | tenant FK, candidate FK, application FK, token (UUID), purpose (feedback/document_upload/profile_update/self_schedule/offer_review/referral), expires_at, used_at |

**Views:** All defined in `shared/api.py`:
- `PortalApplyView` — anonymous application (creates candidate via dedup + application + consent record + tracking JWT)
- `PortalStatusView` — check application status via signed token
- `PortalJobAlertView` — subscribe to job alerts
- `PortalFeedbackView` — post-rejection feedback
- `PortalCareerPageView` — public career page with config + job listings
- `PortalDocumentUploadView` — candidate uploads documents via secure link
- `PortalProfileUpdateView` — candidate updates contact info
- `PortalSelfScheduleView` — candidate self-schedules interview
- `PortalOfferReviewView` — candidate reviews/accepts/declines offer
- `PortalReferralView` — employee referral submission

**URLs:** Delegates to `shared.api.portal_urlpatterns` (10 patterns)

**Issues:**
- ⚠️ Portal tokens use `jwt.encode(payload, settings.SECRET_KEY)` with the main Django `SECRET_KEY` — should use a separate portal-specific secret for compartmentalization.
- ⚠️ `PortalApplyView` creates candidates without file upload — resume upload is a separate step. No indication to the user that this is incomplete.

---

### 4.12 scoring

**Models** (`models.py`):
| Model | Purpose |
|---|---|
| `JobScoreBatch` | Company batch scoring job | tenant FK, job_title, jd_text, jd_requirements_json (JSON), scoring_weights (JSON), status, total/parsed/scored items |
| `BatchItem` | Individual CV in a batch | batch FK, file_name, file_content (Binary), file_type, raw_text, parsed_json (JSON), candidate_name/email, status |
| `BatchItemScore` | Score per batch item | batch_item FK, score_total (0-100), content/title/experience/recency/format scores, breakdown_json (JSON) |
| `CandidateProfile` | Candidate personal scoring profile | user FK (auth user) |
| `CandidateResumeVersion` | Candidate's uploaded resume versions | user FK, file_name, file_content, file_type, raw_text, parsed_json, version_label |
| `CandidateScoreRun` | Score run for candidate | user FK, resume_version FK, jd_text, jd_title, jd_requirements_json, all score fields, breakdown_json |

**JD Parser** (`jd_parser.py`, 456 lines):
- Deterministic JD requirement extraction (no AI APIs)
- Per-line intent detection (required/preferred/neutral) using keyword cues
- Section-level context detection (Requirements → required, Nice-to-have → preferred)
- N-gram skill extraction against taxonomy
- Years extraction (range + minimum patterns)
- Education, certification, work mode, location, domain keyword extraction
- Target title extraction from JD text
- `build_taxonomy_lookup()` — builds {alias_normalized: {skill_id, canonical_name}} from database

**Scorer** (`scorer.py`, 690 lines):
- 6-feature weighted scoring:
  - A) Skill match (45%): weighted required/preferred coverage with confidence gating
  - B) Title match (20%): token overlap against JD target titles
  - C) Domain match (15%): JD domain keywords present in CV text
  - D) Experience fit (10%): years within JD range with over/under penalties
  - E) Recency (10%): exponential decay of skill freshness
- Format bonus/penalty: +5 for excellent format, -15 for poor format
- Must-have cap: missing must-have skills → score capped at 35
- Knockout rules: eligibility flags (work auth, location) → not eligible
- Full explainability payload: breakdown, reasons array, suggestions, matched/missing skills

**Tasks** (`tasks.py`, 247 lines):
- `process_batch()` → `parse_batch_item()` → `score_batch_item()` (Celery chain)
- `process_batch_sync()` — synchronous fallback for environments without Celery

**Views** (`views.py`, 444 lines):
- `BatchListCreateView` — create batch (ZIP upload or individual files, dedup by email)
- `BatchDetailView`, `BatchResultsView`, `batch_export_csv`
- `CandidateScoreView` — personal scoring (upload CV + JD → instant score)
- `CandidateScoreListView`, `CandidateScoreDetailView`
- `CandidateResumeListCreateView` — upload/list resume versions

**Admin** (`admin.py`): All 6 models registered

**URLs:** 8 patterns (4 company batch + 4 candidate personal)

**Migrations:** 1 (initial)

**Issues:**
- ℹ️ Very well-implemented deterministic scoring with full explainability — no AI API dependencies.
- ⚠️ `BatchItem.file_content` is a BinaryField storing raw file bytes in the database — this doesn't scale for large files. Should use S3/MinIO storage.
- ⚠️ `CandidateResumeVersion.file_content` also stores file bytes in DB — same concern.

---

### 4.13 search

**Models** (`models.py`):
| Model | Purpose |
|---|---|
| `SavedSearch` | Saved search queries | tenant FK, user FK, name, query, filters (JSON), sort_by |
| `ScoreHistory` | Candidate score tracking | candidate FK, job FK, score, breakdown (JSON), scored_at |
| `SkillSynonym` | Skill synonyms for search expansion | skill FK, synonym |

**Services** (`services.py`, 634 lines):
- OpenSearch client management (dev-safe: silent failures when OS unavailable)
- `CANDIDATE_INDEX_MAPPING` with proper field types (text/keyword/integer/float/date)
- `index_candidate()` — upsert candidate document to OpenSearch
- `search_candidates()` — BM25 query with configurable size + DB fallback
- `_db_fallback_search()` — full Django ORM-based search when OpenSearch is down
- `parse_boolean_query()` — AND/OR/NOT operator parsing with quoted phrases
- `boolean_search_candidates()` — Django ORM boolean search implementation
- `auto_match_candidates()` — find top matching talent pool candidates for a job
- `find_similar_candidates()` — Jaccard + title + experience similarity
- `skill_gap_analysis()` — compare candidate skills vs job requirements

**Ranking** (`ranking.py`, 361 lines):
- `skill_match()` — weighted Jaccard with required (0.75) + optional (0.25) weighting
- `title_match()` — exact (1.0), substring (0.5), no match (0.0)
- `experience_fit()` — in-range (1.0), under (penalized), over (0.5 floor for 2x+)
- `recency_score()` — exponential decay
- `domain_match()` — tag overlap
- `normalize_bm25()` — min-max normalization
- `compute_structured_score()` — 5-component weighted sum
- `compute_hybrid_score()` — BM25 + structured blend
- `build_explanation()` — human-readable scoring explanation
- `rank_candidates()` — full ranking pipeline with optional BM25 hybrid

**Tasks** (`tasks.py`): `refresh_search_index` — periodic reindex

**URLs:** Router + manual patterns for search, saved searches

**Migrations:** Not a standard app migration (no models with DB tables needing migration? Models exist but may be managed differently)

**Issues:**
- ℹ️ Excellent graceful degradation: OpenSearch → DB fallback for all search operations.
- ⚠️ `auto_match_candidates()` loads up to 500 candidates into memory and scores them all — could be slow for large tenants.

---

### 4.14 shared

This is the **largest app** (14 files) and acts as a **cross-cutting utilities module** providing middleware, API views, tasks, and validators used by all other apps.

**Files:**

| File | Lines | Purpose |
|---|---|---|
| `api.py` | 1,643 | Views for messaging, analytics (KPIs, funnel, recruiter perf, pipeline velocity, diversity, source ROI, SLA compliance, hiring forecast, export), portal (apply, status, job alerts, feedback, career page, document upload, profile update, self-schedule, offer review, referral), notifications (list, preferences, unified ATS+HRM), compliance (contact validation, GDPR purge, login audit, rate limits, buddy suggestion, job share) |
| `advanced_api.py` | ~250 | Activity feed, candidate comparison, talent pools, webhook delivery (HMAC + retry), pagination headers mixin, tenant-scoped throttle, field-level permissions |
| `bulk_api.py` | ~250 | Bulk stage transition, bulk reject, bulk tag, export candidates CSV, export jobs CSV, import candidates CSV, job clone, candidate merge |
| `scorecard_api.py` | ~170 | In-memory scorecard template CRUD, submission CRUD, aggregation |
| `middleware.py` | ~130 | SecurityHeadersMiddleware, RequestLoggingMiddleware, LoginThrottleMiddleware |
| `audit_middleware.py` | ~130 | AuditLogMiddleware (write-op audit to DB), CORSValidationMiddleware |
| `health.py` | ~45 | health_check (liveness), readiness_check (DB connectivity) |
| `hrm_webhook.py` | ~130 | HRM inbound webhook: employee.terminated → candidate status update, employee.id_assigned → Offer update |
| `tasks.py` | ~100 | send_webhook_task (retry + backoff), send_email_task, bulk_score_task, create_audit_log_partitions |
| `urls.py` | ~15 | Bulk + advanced API URL patterns |
| `validators.py` | ~100 | Email/phone/salary/date range/file upload/URL validation + text sanitization |
| `clamav.py` | ~120 | ClamAV INSTREAM protocol integration for file virus scanning (fail-open) |

**Issues:**
- ⚠️ **GOD MODULE**: `shared/api.py` at 1,643 lines is a massive single file containing views for 5+ different apps (analytics, messaging, notifications, portal, compliance). This violates separation of concerns and makes the codebase harder to maintain. Views should live in their respective app directories.
- ⚠️ `scorecard_api.py` uses **in-memory dicts** (`scorecard_templates = {}`, `scorecard_submissions = {}`) instead of database models. All data is lost on server restart. This is labeled "replace with model-backed store in production" but hasn't been.
- ⚠️ `LoginThrottleMiddleware._attempts` is an **in-memory class variable** — not shared across Gunicorn workers, Celery processes, or multi-server deployments. Brute-force protection is ineffective in production.
- ⚠️ `deliver_webhook()` in `advanced_api.py` uses `time.sleep()` for exponential backoff — this blocks the request thread. Should always use Celery for webhook delivery (the task version in `shared/tasks.py` does this correctly).
- ⚠️ `PortalReferralView` calls `resolve_candidate()` which returns a dict, then tries `candidate.tags = ...` — but `candidate` was assigned the dict result, not a Candidate object. This is a **runtime bug**.

---

### 4.15 taxonomy

**Models** (`models.py`):
| Model | Purpose |
|---|---|
| `SkillTaxonomy` | Canonical skill definitions | canonical_name, category, description, is_active |
| `SkillAlias` | Alias → canonical skill mapping | skill FK, alias_normalized (unique), confidence |
| `TitleAlias` | Job title normalization | canonical_title, alias_normalized |
| `LocationAlias` | Location normalization | canonical_name, alias_normalized, city, state, country_code, region |

**Views** (`views.py`):
- `SkillTaxonomyListView` — list/filter skills
- `SkillAliasResolveView` — resolve alias → canonical skill
- `TitleNormalizeView` — normalize raw title
- `LocationNormalizeView` — normalize raw location
- `SkillCategoryListView` — list skill categories

**URLs:** 5 patterns

**Migrations:** 1 (initial)

**Issues:**
- ℹ️ Clean, focused app. Well-designed for extensibility.

---

### 4.16 tenants

**Models** (`models.py`):
| Model | Purpose |
|---|---|
| `Tenant` | Organization record | name, slug (unique), domain, status (active/suspended/trial), plan (starter/pro/enterprise), created_at |
| `TenantSettings` | Comprehensive tenant config | idle_threshold_days, dedup config, SMTP credentials (host/port/user/password/use_tls/from_email), career page config (JSON), custom fields (JSON), GDPR settings (retention_months, auto_purge), notification defaults (JSON), rate limiting, onboarding template (JSON) |

**Middleware** (`middleware.py`): `TenantMiddleware` — extracts `tenant_id` from JWT, sets PostgreSQL RLS context via raw SQL `SET app.tenant_id`

**Views** (`views.py`): `TenantDetailView`, `TenantSettingsView`

**Serializers:** TenantSerializer, TenantSettingsSerializer

**URLs:** 2 patterns (current tenant, settings)

**Migrations:** 2 (initial → rate limit + settings fields)

**Issues:**
- ⚠️ `TenantSettings.smtp_password` stores SMTP credentials in **plaintext** in the database. Should be encrypted at rest.
- ⚠️ `TenantMiddleware` runs `cursor.execute("SET app.tenant_id = %s")` for RLS — this only works with PostgreSQL. SQLite dev fallback silently skips this (correct), but there's no dev-mode tenant isolation enforcement beyond ORM filtering.

---

### 4.17 workflows

**Models** (`models.py`):
| Model | Purpose |
|---|---|
| `AutomationRule` | Workflow trigger rules | tenant FK, name, trigger (14 types: application_created, stage_changed, offer_accepted, etc.), conditions (JSON), actions (JSON), enabled, priority |
| `WorkflowStep` | Multi-step workflow definitions | rule FK, order, action_type (11 types: send_email, move_stage, assign_tag, notify_user, update_candidate, assign_recruiter, schedule_interview, create_task, escalate, etc.), action_config (JSON), condition_json (JSON), delay_hours |
| `WorkflowExecution` | Execution audit trail | rule FK, step FK, event_id, action_type, action_target, status (pending/success/failed/skipped), error, execute_at |
| `IdempotencyKey` | Prevents duplicate execution | key (unique), created_at |

**Services** (`services.py`, 501 lines):
- `process_event()` — match event against enabled rules, evaluate conditions, execute actions (idempotent)
- `_conditions_match()` — field-based condition evaluation (equals, gt, lt, in, not_in, contains)
- `_execute_action_idempotent()` — idempotency via `IdempotencyKey` + action dispatch
- 9 action dispatchers: `_dispatch_send_email`, `_dispatch_move_stage`, `_dispatch_assign_tag`, `_dispatch_notify_user`, `_dispatch_update_candidate`, `_dispatch_assign_recruiter`, `_dispatch_schedule_interview`, `_dispatch_create_task`, `_dispatch_escalate`
- `process_multi_step_workflow()` — multi-step execution with delays and conditional branching
- `_evaluate_step_conditions()` — supports equals, not_equals, contains, gt, lt operators
- `execute_pending_workflow_steps()` — execute delayed steps past their execute_at time

**Views** (`views.py`, 82 lines):
- `WorkflowRuleListCreateView`, `WorkflowRuleDetailView`
- `toggle_rule` — enable/disable a rule
- `WorkflowExecutionListView` — execution audit log
- `trigger_workflow` — manual trigger

**Tasks** (`tasks.py`):
- `process_automation_event` — async event processing
- `check_idle_applications` — periodic: flag applications idle beyond threshold

**Serializers:** WorkflowRuleSerializer, WorkflowExecutionSerializer

**URLs:** 5 patterns

**Migrations:** 3 (initial → options → execution + idempotency)

**Issues:**
- 🐛 **BUG in `views.py` line 33**: `WorkflowRuleDetailView.get_queryset()` references `WorkflowRule.objects.all()` but the model is named `AutomationRule`. This will raise `NameError: name 'WorkflowRule' is not defined` at runtime.
- ⚠️ `trigger_workflow` view catches `Exception` and returns 500 with the raw exception string — potential information leakage in production.
- ⚠️ `execute_pending_workflow_steps()` is not registered as a Celery beat task in settings — delayed steps won't auto-execute.

---

## 5. Test Suite Audit

| File | Lines | Scope |
|---|---|---|
| `conftest.py` | 130 | pytest fixtures: api_client, user_factory, admin_user, recruiter_user, auth_client, candidate_factory, job_factory, application_factory |
| `test_applications.py` | 209 | Pipeline stage transitions (5 tests), GDPR data erasure (4 tests), unique constraint enforcement |
| `test_comprehensive.py` | 519 | Broad coverage: accounts auth (6), candidates CRUD (5), jobs CRUD (4), applications (2), messaging (2), analytics (2), search (1), workflows (2), notifications (1), scoring (1), portal (1), bulk API (4), health checks (2), validators (8), integration pipeline (2) |
| `test_parsing.py` | ~150 | Skill extraction confidence/range (4), false positives (1), case sensitivity (1), evidence structure (1), contact extraction (2), section detection (3), derived fields (2), fuzzy dates (2) |
| `test_ranking.py` | ~200 | Score range assertions for all components (8), sorted results (1), empty input (1), zero-skills (1), perfect match (1), component presence (1), skill_match bounds (1), experience_fit bounds (1) |
| `test_rls_isolation.py` | ~180 | Cross-tenant isolation: candidates (2), jobs (1), users (1), applications (1), empty queryset (1), middleware tenant attachment (1) |
| `test_services.py` | 271 | Parsing functions (10): clean_text, detect_sections, extract_contact_info, extract_date_ranges, extract_skills, parse_fuzzy_date, compute_derived_fields, interval merging. Ranking functions (11): skill_match, title_match, experience_fit, normalize_bm25, composite score, explanation, rank_candidates |

**Test Quality Assessment:**
- ✅ Good unit test coverage for parsing and ranking — core algorithmic logic is well-tested
- ✅ RLS/tenant isolation tests verify the multi-tenancy data contract
- ✅ GDPR erasure tests verify anonymization correctness
- ⚠️ **No API integration tests actually hit the full request/response cycle** — `test_comprehensive.py` tests hit URL endpoints but many use `assertIn(resp.status_code, [200, 301])` which masks redirects vs success
- ⚠️ **No tests for:** workflows (services/execution), consent tasks, messaging services, scoring pipeline, ClamAV scanning, HRM webhook handling, cross-auth
- ⚠️ **No mocking of Celery tasks** — tests that trigger async tasks (like GDPR export) may fail without a running broker
- ⚠️ **Factory inconsistencies**: `conftest.py` factories use `name`/`email` fields, while `test_applications.py` uses `first_name`/`last_name`/`primary_email` — reflects the Candidate model field name inconsistency

---

## 6. Management Commands

| Command | App | Purpose |
|---|---|---|
| `seed_demo` | accounts | Seeds: 1 tenant, 5 roles, 1 admin user, 5 jobs with pipeline stages, 8 candidates with identities, 8 applications with stage history, 4 interviews |
| `seed_ats` | shared | Seeds: 500+ skills (12 categories) into SkillTaxonomy, 4 default roles per tenant, 4 email templates, 7 automation rules |
| `seed_demo_data` | shared | Seeds: 50 random candidates, 20 jobs, ~200 applications (for stress/demo testing) |
| `seed_taxonomy` | taxonomy | Seeds: 160+ skills with aliases, title aliases, location aliases |

**Issues:**
- ⚠️ Overlapping taxonomy seeding: both `seed_ats` and `seed_taxonomy` seed skills — running both will create duplicates (though `get_or_create` is used in `seed_taxonomy`).
- ⚠️ `seed_demo_data` doesn't use tenant scoping — creates candidates/jobs without `tenant` FK, which will fail with required FK constraints.

---

## 7. Migration State

| App | Count | Latest |
|---|---|---|
| accounts | 6 | 0006_audit_log_partition |
| analytics | 2 | 0002_savedreport |
| applications | 4 | 0004_offer_hrm_employee_fields |
| candidates | 5 | 0005_gin_indexes |
| consent | 1 | 0001_initial |
| jobs | 3 | 0003_gin_indexes |
| messaging | 2 | 0002_activitylog_tracking_fields |
| scoring | 1 | 0001_initial |
| taxonomy | 1 | 0001_initial |
| tenants | 2 | 0002_settings_fields |
| workflows | 3 | 0003_workflow_execution_idempotency |
| **Total** | **30** | |

**Apps without migrations:** blog, notifications, parsing, portal, search, shared (these either have no models, their models live in other apps, or they're utility modules)

---

## 8. Cross-Cutting Concerns

### Security
- ✅ JWT auth with short-lived tokens (30-min access)
- ✅ TOTP MFA implementation
- ✅ Security headers (CSP, HSTS, X-Content-Type-Options, X-Frame-Options)
- ✅ Audit logging for all write operations with DB persistence
- ✅ ClamAV antivirus integration for file uploads (fail-open mode)
- ✅ Text sanitization (XSS prevention on input)
- ✅ HMAC signature verification on HRM webhooks
- ⚠️ SMTP passwords stored in plaintext in TenantSettings
- ⚠️ Login throttle uses in-memory dict, not Redis
- ⚠️ Portal tokens use Django SECRET_KEY directly

### Multi-Tenancy
- ✅ UUID tenant FK on all models
- ✅ TenantMiddleware sets PostgreSQL RLS context
- ✅ JWT claims carry tenant_id
- ✅ All querysets filtered by tenant_id
- ✅ Comprehensive RLS isolation tests
- ⚠️ Blog app is not tenant-scoped

### GDPR Compliance
- ✅ Consent record tracking (data_processing, marketing, third_party_sharing, retention)
- ✅ Data export (ZIP with profile + applications + consents + resumes)
- ✅ Right to erasure with soft-delete + 30-day grace period + auto-purge
- ✅ Candidate self-service consent management
- ✅ Consent summary dashboard
- ⚠️ `auto_purge_expired_candidates` task not in beat schedule

### Performance
- ✅ Redis caching layer configured
- ✅ GIN indexes on JSONB fields (candidates, jobs)
- ✅ OpenSearch for full-text search with DB fallback
- ✅ Celery for async processing
- ⚠️ `BatchItem.file_content` stores binary in DB instead of S3
- ⚠️ Several views iterate Python-side instead of using DB aggregation

### Observability
- ✅ Structured request logging (method, path, status, duration, IP)
- ✅ Correlation IDs (X-Correlation-ID) on all responses
- ✅ Health + readiness probes
- ✅ Sentry integration configured
- ✅ Audit log with partitioned table (monthly auto-creation)

---

## 9. Issues, Bugs & Risks

### Confirmed Bugs 🐛
1. **`workflows/views.py` line 33**: References `WorkflowRule.objects.all()` but model is `AutomationRule` — will raise `NameError` at runtime.
2. **`shared/api.py` PortalReferralView**: `resolve_candidate()` returns a dict, but code then calls `candidate.tags` on it — will raise `AttributeError`.

### High-Priority Issues ⚠️
3. **In-memory scorecard store** (`shared/scorecard_api.py`): All scorecard data lost on server restart.
4. **In-memory login throttle** (`shared/middleware.py`): Brute-force protection ineffective in multi-worker production.
5. **SMTP plaintext credentials** (`tenants/models.py`): TenantSettings stores SMTP password unencrypted.
6. **File bytes in DB** (`scoring/models.py`): `BatchItem.file_content` and `CandidateResumeVersion.file_content` store raw bytes — won't scale.
7. **Candidate model field name inconsistency**: Mismatch between `name`/`email` and `full_name`/`primary_email` and `first_name`/`last_name` across models, views, tests, and factories.
8. **`shared/api.py` God Module**: 1,643-line single file containing views for 5+ different apps — major maintainability concern.

### Medium-Priority Issues
9. `CompanyRegisterView` — non-atomic tenant+user creation
10. `move_stage` doesn't validate stage belongs to same job's pipeline
11. `Application.current_stage` (FK) vs `current_stage_name` (CharField) — dual-source of truth
12. Two different `send_email_task` implementations (messaging/tasks.py vs shared/tasks.py)
13. `auto_purge_expired_candidates` not in Celery beat schedule
14. `execute_pending_workflow_steps()` not in beat schedule
15. `deliver_webhook()` uses blocking `time.sleep()` in synchronous context
16. No email verification on registration endpoints
17. Blog app not tenant-scoped
18. Template rendering uses unsandboxed string replacement

---

## 10. Recommendations

### Immediate Fixes (P0)
1. Fix `WorkflowRuleDetailView` to use `AutomationRule.objects.all()` instead of `WorkflowRule`
2. Fix `PortalReferralView` to properly handle `resolve_candidate()` return value
3. Move scorecard storage from in-memory dicts to proper Django models
4. Replace in-memory login throttle with Redis-backed implementation

### Short-Term (P1, 1-2 weeks)
5. Split `shared/api.py` into per-app view files (move analytics views to `analytics/views.py`, etc.)
6. Standardize Candidate field names (choose `full_name`/`primary_email` and migrate everywhere)
7. Encrypt SMTP credentials in TenantSettings (use `django-fernet-fields` or similar)
8. Move `BatchItem.file_content` to S3 storage (store path, not bytes)
9. Wrap `CompanyRegisterView` in `transaction.atomic()`
10. Add `auto_purge_expired_candidates` and `execute_pending_workflow_steps` to Celery beat schedule

### Medium-Term (P2, 1-2 months)
11. Add ClamAV scanning to candidate `upload_resume` and portal document upload flows
12. Add email verification to registration endpoints
13. Add stage validation to `move_stage` (verify stage belongs to job)
14. Remove `current_stage_name` CharField (use `current_stage` FK as single source of truth)
15. Add comprehensive test coverage for: workflow execution, consent tasks, messaging services, HRM webhooks, scoring pipeline
16. Add tenant FK to Blog models
17. Use separate signing key for portal tokens
18. Replace blocking `deliver_webhook()` with async-only Celery task

### Long-Term (P3, 2-3 months)
19. Extract `shared` app into focused apps (middleware, validators, health as separate modules)
20. Add OpenTelemetry tracing for distributed request tracking
21. Add database-level audit triggers in addition to middleware-level auditing
22. Implement read-replica routing for analytics queries
23. Add API versioning strategy beyond `/api/v1/`
24. Implement WebSocket support for real-time notifications (replace polling)

---

*End of Audit Report*
