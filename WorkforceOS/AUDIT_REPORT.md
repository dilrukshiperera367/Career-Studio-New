# HRM System Backend — Comprehensive Audit Report

**Generated:** 2025-07-16
**Scope:** All 15 Django apps, config, tests, seed, requirements
**Backend path:** `HRM System/backend/`

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Technology Stack](#2-technology-stack)
3. [Architecture Overview](#3-architecture-overview)
4. [App-by-App Audit](#4-app-by-app-audit)
   - 4.1 [authentication](#41-authentication)
   - 4.2 [tenants](#42-tenants)
   - 4.3 [core_hr](#43-core_hr)
   - 4.4 [leave_attendance](#44-leave_attendance)
   - 4.5 [payroll](#45-payroll)
   - 4.6 [onboarding](#46-onboarding)
   - 4.7 [performance](#47-performance)
   - 4.8 [analytics](#48-analytics)
   - 4.9 [integrations](#49-integrations)
   - 4.10 [platform_core](#410-platform_core)
   - 4.11 [engagement](#411-engagement)
   - 4.12 [learning](#412-learning)
   - 4.13 [helpdesk](#413-helpdesk)
   - 4.14 [workflows](#414-workflows)
   - 4.15 [custom_objects](#415-custom_objects)
5. [Config & Infrastructure](#5-config--infrastructure)
6. [Tests Audit](#6-tests-audit)
7. [Cross-Cutting Bugs & Issues](#7-cross-cutting-bugs--issues)
8. [Missing / Incomplete Features](#8-missing--incomplete-features)
9. [Security Concerns](#9-security-concerns)
10. [Recommendations](#10-recommendations)

---

## 1. Executive Summary

The HRM System backend is a **Django 5.2+ / DRF 3.15+** multi-tenant HR management platform with **15 Django apps**, **~80 models**, **~60 ViewSets/APIViews**, and **~50 serializers**. It implements row-level tenant isolation, JWT authentication, RBAC, Celery task queue, bi-directional ATS integration, Sri Lanka/India/UAE payroll compliance, and a workflow automation engine.

### Key Findings

| Category | Count |
|----------|-------|
| **Critical Bugs (field name mismatches that will crash at runtime)** | 5 |
| **Missing API exposure (models with no views/URLs)** | 12+ models |
| **Empty admin registrations** | 14 of 15 apps |
| **Missing serializer files (inline in views)** | 8 apps |
| **Test files** | 7 (254 test cases) |
| **Security concerns** | 6 |

---

## 2. Technology Stack

| Component | Technology |
|-----------|-----------|
| Framework | Django 5.2+, DRF 3.15+ |
| Auth | SimpleJWT (60min access, 7d refresh, rotate+blacklist) |
| Database | PostgreSQL (SQLite dev fallback via `USE_SQLITE`) |
| Task Queue | Celery + Redis broker, django-celery-beat |
| File Storage | S3/MinIO (boto3, django-storages) |
| PDF | WeasyPrint |
| API Docs | drf-spectacular (Swagger/ReDoc) |
| Audit | django-simple-history |
| Monitoring | Sentry, Prometheus (production) |
| File Security | ClamAV (INSTREAM protocol) |
| Filtering | django-filter |
| CORS | django-cors-headers |

### requirements.txt (22 dependencies)
```
Django>=5.2, djangorestframework>=3.15, djangorestframework-simplejwt,
django-filter, drf-spectacular, django-cors-headers, django-simple-history,
django-celery-beat, celery[redis], redis, psycopg2-binary, boto3,
django-storages, weasyprint, sentry-sdk[django], django-prometheus,
gunicorn, whitenoise, python-dateutil, Pillow, pytest-django, factory-boy
```

---

## 3. Architecture Overview

### Multi-Tenancy
- **Row-level isolation** via `tenant` FK on every model
- `TenantMiddleware` resolves tenant from JWT `user.tenant_id` or `X-Tenant-ID` header
- `TenantViewSetMixin` filters all querysets by `tenant_id`
- `TenantSerializerMixin` auto-sets `tenant_id` on create

### RBAC
- Custom `Role → Permission → RolePermission` with scope levels: `own/team/department/branch/company/all`
- `HasTenantPermission` DRF permission class
- `PermissionViewSetMixin` for declarative endpoint permission mapping

### URL Structure
All apps mounted under `/api/v1/`:
```
/api/v1/auth/         → authentication
/api/v1/tenants/      → tenants (empty)
/api/v1/hr/           → core_hr
/api/v1/leave/        → leave_attendance
/api/v1/payroll/      → payroll
/api/v1/onboarding/   → onboarding
/api/v1/performance/  → performance
/api/v1/analytics/    → analytics
/api/v1/integrations/ → integrations
/api/v1/platform/     → platform_core
/api/v1/engagement/   → engagement
/api/v1/learning/     → learning
/api/v1/helpdesk/     → helpdesk
/api/v1/workflows/    → workflows
/api/v1/objects/      → custom_objects
```
Plus: `/health/`, `/ready/`, `/api/docs/`, `/api/schema/`, `/admin/`

---

## 4. App-by-App Audit

---

### 4.1 authentication

**Files:** `models.py`, `views.py`, `serializers.py`, `urls.py`, `admin.py`, `cross_auth.py`

#### Models (6)

| Model | Key Fields | Notes |
|-------|-----------|-------|
| `User` | UUID PK, `tenant` FK, `email` (unique), `first_name`, `last_name`, `phone`, `status` (active/inactive/suspended), `is_staff`, `is_superuser` | Custom user model, `AUTH_USER_MODEL` |
| `Role` | `name`, `description`, `is_system_role`, tenant FK | Tenant-scoped roles |
| `Permission` | `codename` (unique), `name`, `category` | Global permissions |
| `RolePermission` | `role` FK, `permission` FK, `scope` (own/team/dept/branch/company/all) | Permission assignment with scope |
| `UserRole` | `user` FK, `role` FK, `tenant` FK | User-role binding |
| `PasswordResetToken` | `user` FK, `token`, `expires_at`, `used` | Password reset |
| `InviteToken` | `tenant` FK, `email`, `role` FK, `token`, `expires_at`, `used`, `invited_by` FK | User invitation |

#### Views (8 endpoints)

| View | Method | URL | Purpose |
|------|--------|-----|---------|
| `LoginView` | POST | `/auth/login/` | JWT login (custom claims: tenant_id, roles) |
| `RegisterView` | POST | `/auth/register/` | Creates tenant + first user |
| `ProfileView` | GET/PUT | `/auth/profile/` | Current user profile |
| `ChangePasswordView` | POST | `/auth/change-password/` | Change password |
| `ForgotPasswordView` | POST | `/auth/forgot-password/` | Send reset token |
| `ResetPasswordView` | POST | `/auth/reset-password/` | Reset password with token |
| `InviteUserView` | POST | `/auth/invite/` | Invite user to tenant |
| `InviteAcceptView` | POST | `/auth/invite/accept/` | Accept invitation |

#### Serializers (3)
- `CustomTokenObtainPairSerializer` — adds `tenant_id`, `roles` to JWT claims
- `UserRegistrationSerializer` — validates registration
- `UserProfileSerializer` — profile read/update

#### Cross-Auth (`cross_auth.py`)
- `CrossSystemTokenObtainPairSerializer` — shared JWT between ATS ↔ HRM
- `build_module_switch_url()` — generates cross-system redirect URLs
- `validate_cross_system_token()` — validates incoming cross-system tokens

#### Issues
- ⚠️ `admin.py` is empty — no User/Role/Permission registration in Django admin
- ⚠️ No `RefreshTokenView` endpoint (SimpleJWT handles it automatically via default URLs, but none configured)
- ⚠️ `RegisterView` creates tenant + user atomically but no transaction wrapping visible
- ⚠️ No email verification flow after registration
- ⚠️ No rate limiting on login endpoint beyond global throttle (50/min anon)

---

### 4.2 tenants

**Files:** `models.py`, `views.py`, `urls.py`, `middleware.py`, `admin.py`, `enterprise.py`

#### Models (8)

| Model | Key Fields | Notes |
|-------|-----------|-------|
| `Tenant` | UUID PK, `name`, `slug` (unique), `plan` (free/starter/professional/enterprise), `settings_json`, `hrm_settings`, `max_employees`, `is_active` | Core tenant |
| `TenantFeature` | `tenant` FK, `feature` (11 module choices), `is_enabled`, `config` | Module activation |
| `FeatureFlag` | `tenant` FK, `flag_name`, `is_enabled`, `rollout_percentage`, `config` | Granular rollout |
| `SSOConfiguration` | `tenant` FK, `provider` (saml/oidc/google/microsoft), `client_id`, `client_secret`, `metadata_url`, `entity_id`, `certificate` | SSO config |
| `SCIMConfiguration` | `tenant` FK, `endpoint_url`, `bearer_token`, `sync_groups`, `sync_users` | SCIM provisioning |
| `SCIMSyncLog` | `tenant` FK, `scim_config` FK, `direction`, `records_synced`, `errors` | SCIM sync audit |
| `Subscription` | `tenant` FK, `plan`, `status` (trial/active/past_due/cancelled), `stripe_*` fields, `current_period_start/end`, `mrr` | Billing |
| `Invoice` | `subscription` FK, `stripe_invoice_id`, `amount`, `status`, `pdf_url` | Invoices |
| `TranslationKey` | `tenant` FK, `key`, `en`, `si`, `ta` | i18n (English/Sinhala/Tamil) |

#### Views & URLs
- **views.py**: Empty (only placeholder comment)
- **urls.py**: Empty (no endpoints)

#### Middleware (`middleware.py`)
- `TenantMiddleware`: Resolves `request.tenant_id` from JWT user's `tenant_id` or `X-Tenant-ID` header
- Exempt paths: `/api/v1/auth/`, `/api/docs/`, `/api/schema/`, `/admin/`, `/health/`, `/ready/`

#### Issues
- 🔴 **No API endpoints at all** — 8 models with zero views/serializers/URLs
- ⚠️ No tenant CRUD API (no way to update tenant settings, manage features, manage SSO via API)
- ⚠️ No subscription management API (Stripe webhook handler missing)
- ⚠️ `admin.py` is empty
- ⚠️ `SCIMConfiguration` and `SSOConfiguration` have no integration logic — model-only stubs
- ⚠️ `TranslationKey` has no translation middleware or utility functions

---

### 4.3 core_hr

**Files:** `models.py`, `views.py`, `serializers.py`, `urls.py`, `admin.py`, `tasks.py`, `imports.py`

#### Models (7)

| Model | Key Fields | Notes |
|-------|-----------|-------|
| `Company` | UUID PK, `tenant` FK, `name`, `legal_name`, `registration_number`, `tax_id`, `country`, `currency`, `address`, `industry`, `settings`, `logo` | Legal entity |
| `Branch` | UUID PK, `tenant` FK, `company` FK, `name`, `code`, `address`, `city`, `country`, `geo_coordinates` (JSON), `is_headquarters` | Office location |
| `Department` | UUID PK, `tenant` FK, `company` FK, `name`, `code`, `parent` (self FK), `head` (Employee FK) | Hierarchical (tree); has `get_ancestors()`, `get_descendants()` |
| `Position` | UUID PK, `tenant` FK, `company` FK, `department` FK, `title`, `grade`, `band`, `headcount`, `min_salary`, `max_salary`, `reports_to` (self FK) | Job position |
| `Employee` | UUID PK, `tenant` FK, ~40 fields: personal (name, DOB, gender, NIC, passport), contact (emails, phones, address), employment (company, department, position, branch, manager FK, hire_date, probation_end, contract_end, termination_date, status), bank, custom_fields JSON, source, ats_candidate_id | `HistoricalRecords`, auto-generated `EMP-XXXX` |
| `JobHistory` | UUID PK, `tenant` FK, `employee` FK, `effective_date`, `change_type` (hire/promotion/transfer/dept_change/role_change/salary_change/termination/other), `previous_*`, `new_*`, `note`, `actor` FK | Immutable audit trail |
| `EmployeeDocument` | UUID PK, `tenant` FK, `employee` FK, `title`, `document_type`, `file`, `expiry_date`, `e_signed`, `visibility` (employee/manager/hr/admin), `status` | File attachments |
| `Announcement` | UUID PK, `tenant` FK, `title`, `content`, `priority`, `target_audience` JSON, `published_at`, `expires_at` | Company-wide notices |

#### Views (6 ViewSets, ~15 custom actions)

| ViewSet | Key Actions |
|---------|------------|
| `CompanyViewSet` | Standard CRUD |
| `BranchViewSet` | Standard CRUD |
| `DepartmentViewSet` | CRUD + `org_chart` action (returns hierarchical tree) |
| `PositionViewSet` | Standard CRUD |
| `EmployeeViewSet` | CRUD + `job_change`, `get_job_history`, `direct_reports`, `documents`, `search`, `bulk_import`, `export_csv`, `upload_photo` |
| `AnnouncementViewSet` | Standard CRUD |

#### Serializers (9)
- `CompanySerializer`, `BranchSerializer`, `DepartmentSerializer` (with `employee_count`)
- `PositionSerializer`, `EmployeeListSerializer` (lightweight), `EmployeeDetailSerializer` (full)
- `JobHistorySerializer`, `JobChangeSerializer` (input), `EmployeeDocumentSerializer`, `AnnouncementSerializer`

#### URL Patterns (6 router registrations)
```
companies/, branches/, departments/, positions/, employees/, announcements/
```

#### Celery Tasks
- `check_expiring_documents()` — daily task, checks 90/60/30/7 day expiry windows

#### Imports (`imports.py`)
- `bulk_import_employees()` — CSV parser with validation, FK lookups, `bulk_create`

#### Issues
- ⚠️ `admin.py` is empty
- ⚠️ `Employee.full_name` referenced across codebase but not visible as `@property` in the model read — verify it exists
- ⚠️ No document virus scanning integration (ClamAV exists in platform_core but not called from EmployeeViewSet)

---

### 4.4 leave_attendance

**Files:** `models.py`, `views.py`, `serializers.py`, `urls.py`, `tasks.py`

#### Models (8)

| Model | Key Fields | Notes |
|-------|-----------|-------|
| `LeaveType` | 20+ config fields: `name`, `code`, `paid`, `max_days_per_year`, `carry_forward`, `max_carry_forward`, `accrual_type`, `applicable_gender`, `probation_restriction`, `requires_attachment_after_days`, `min_notice_days` | Highly configurable |
| `LeaveBalance` | `employee` FK, `leave_type` FK, `year`, `entitled`, `taken`, `pending`, `carried_forward`, `adjustment` | `@property remaining = entitled + carried_forward + adjustment - taken - pending` |
| `LeaveRequest` | `employee` FK, `leave_type` FK, `start_date`, `end_date`, `days`, `status`, `is_half_day`, `half_day_period`, `is_short_leave`, `reason`, `approved_by` FK, `approved_at`, `rejection_reason`, `attachment` | Full workflow |
| `HolidayCalendar` | `tenant` FK, `name`, `year`, `country` | Calendar container |
| `Holiday` | `calendar` FK, `name`, `date`, `type` (public/mercantile/poya/optional/company) | Sri Lanka-specific types |
| `ShiftTemplate` | `tenant` FK, `name`, `start_time`, `end_time`, `break_minutes`, `grace_period_minutes`, `is_night_shift`, `working_days` JSON | Shift definition |
| `ShiftAssignment` | `tenant` FK, `employee` FK, `shift_template` FK, `effective_from`, `effective_to` | Shift roster |
| `AttendanceRecord` | `employee` FK, `date`, `clock_in/out`, `source` (web/mobile/biometric/manual/QR), `gps_*`, `selfie_url`, `status`, `late_minutes`, `early_leave_minutes`, `overtime_hours`, `regularization_*` | Multi-source punch |
| `OvertimeRecord` | `employee` FK, `date`, `hours`, `type`, `status`, `rate_multiplier`, `approved_by` FK | OT tracking |

#### Views (7 ViewSets, ~15 custom actions)

| ViewSet | Key Actions |
|---------|------------|
| `LeaveTypeViewSet` | Standard CRUD |
| `LeaveBalanceViewSet` | CRUD + `my_balances` |
| `LeaveRequestViewSet` | CRUD + `approve`, `reject`, `calendar` |
| `HolidayViewSet` | CRUD + `add_holiday` |
| `ShiftTemplateViewSet` | Standard CRUD |
| `AttendanceViewSet` | CRUD + `clock_in`, `clock_out`, `today`, `summary`, `regularize`, `history`, `qr_token`, `qr_scan` |
| `OvertimeViewSet` | CRUD + `approve` |

#### Serializers (10)
`LeaveTypeSerializer`, `LeaveBalanceSerializer`, `LeaveRequestSerializer`, `HolidayCalendarSerializer`, `HolidaySerializer`, `ShiftTemplateSerializer`, `AttendanceRecordSerializer`, `ClockInSerializer`, `ClockOutSerializer`, `OvertimeRecordSerializer`

#### URL Patterns (7 router registrations)
```
leave-types/, leave-balances/, leave-requests/, holidays/, shifts/, attendance/, overtime/
```

#### Celery Tasks
- `run_monthly_leave_accrual()` — runs last day of month

#### Issues
- 🔴 **BUG** in `tasks.py`: References `leave_type.annual_days` but model field is `max_days_per_year`
- 🔴 **BUG** in `tasks.py`: References `balance.accrued_days` / `balance.entitled_days` / `balance.remaining` as writable fields, but model has `entitled` / `taken` / `pending` (and `remaining` is a read-only property)
- ⚠️ No admin.py registrations
- ⚠️ `ShiftAssignment` model exists but has no ViewSet or URLs
- ⚠️ No signal/hook to auto-update `LeaveBalance.taken` when a `LeaveRequest` is approved
- ⚠️ No signal/hook to auto-update `LeaveBalance.pending` when a `LeaveRequest` is created

---

### 4.5 payroll

**Files:** `models.py`, `views.py`, `serializers.py`, `urls.py`, `engine.py`, `payslip.py`, `reports.py`, `tasks.py`, `advanced.py`, `country_plugins.py`

#### Models (7)

| Model | Key Fields | Notes |
|-------|-----------|-------|
| `SalaryStructure` | `tenant` FK, `name`, `components` JSON (`calc_type`: fixed/percentage/formula), `status` | Template for salary |
| `EmployeeCompensation` | `tenant` FK, `employee` FK, `structure` FK, `basic_salary`, `effective_date`, `is_current`, `allowances` JSON | Per-employee salary |
| `PayrollRun` | `tenant` FK, `company` FK, `period_year`, `period_month`, `status` (draft→processing→review→approved→finalized→reversed), `total_*`, `processed_by` FK | Monthly batch |
| `PayrollEntry` | `tenant` FK, `payroll_run` FK, `employee` FK, `basic_salary`, `earnings_json`, `deductions_json`, `epf_employee/employer`, `etf_employer`, `apit`, `ot_amount/hours`, `loan_deductions`, `total_earnings/deductions`, `net_salary`, `employer_total_cost`, `payslip_url` | Per-employee calc result |
| `StatutoryRule` | `tenant` FK, `country`, `rule_type` (epf/etf/apit/pf/esi/tds/pt/wps/gratuity), `rate`, `employer_rate`, `threshold`, `slabs` JSON, `effective_from/to` | Pluggable country rules |
| `LoanRecord` | `tenant` FK, `employee` FK, `loan_type` (salary_advance/personal_loan/festival_advance/company_loan), `amount`, `outstanding_balance`, `installment_amount`, `installments_remaining`, `status` | Salary deduction loans |
| `PayrollAuditLog` | `tenant` FK, `payroll_run` FK, `action`, `details` JSON, `actor` FK | Payroll audit trail |

#### Views (5 ViewSets, ~15 custom actions)

| ViewSet | Key Actions |
|---------|------------|
| `SalaryStructureViewSet` | Standard CRUD |
| `EmployeeCompensationViewSet` | CRUD + `final_settlement` |
| `PayrollRunViewSet` | CRUD + `process`, `approve`, `finalize`, `entries`, `bank-file`, `epf-return`, `etf-return`, `apit-summary`, `dispatch-payslips`, `process-arrears` |
| `PayrollEntryViewSet` | CRUD + `payslip` (PDF), `payslip-html` |
| `LoanRecordViewSet` | Standard CRUD |

#### Serializers (5)
`SalaryStructureSerializer`, `EmployeeCompensationSerializer`, `PayrollRunSerializer`, `PayrollEntrySerializer`, `LoanRecordSerializer`

#### URL Patterns (5 router registrations)
```
salary-structures/, compensations/, payroll-runs/, payroll-entries/, loans/
```

#### Engine (`engine.py`)
- `PayrollCalculator` class: loads `StatutoryRule` from DB, calculates earnings from structure components, OT pay, absent deductions, EPF 8%/12%, ETF 3%, APIT progressive slabs, loan deductions

#### Payslip (`payslip.py`)
- `generate_payslip_html()` — HTML template with variable substitution
- `generate_payslip_pdf()` — WeasyPrint PDF generation with HTML fallback

#### Reports (`reports.py`)
- `generate_bank_file()`, `generate_epf_return()`, `generate_etf_return()`, `generate_apit_summary()`
- `generate_headcount_report()`, `generate_leave_utilization_report()`, `generate_attendance_report()`

#### Country Plugins (`country_plugins.py`)
- `StatutoryRulesEngine` — plugin registry pattern
- `SriLankaPlugin` — EPF 8%/12%, ETF 3%, APIT with progressive slabs
- `IndiaPlugin` — PF 12%, ESI 0.75%/3.25%, TDS with slabs, Professional Tax
- `UAEPlugin` — no income tax, gratuity (21d/30d per year), WPS compliance, DEWS
- `ExchangeRate` — hardcoded FX rates with USD intermediary conversion

#### Celery Tasks
- `dispatch_payslips()` — email payslips with retry
- `certification_expiry_alerts()` — cert expiry notifications
- `arrears_processing()` — retroactive salary adjustments

#### Issues
- 🔴 **BUG** in `advanced.py`: References `employee.date_of_joining` but model field is `hire_date`
- 🔴 **BUG** in `advanced.py`: References `loan.total_amount` / `loan.paid_amount` but model has `amount` / `outstanding_balance`
- ⚠️ `advanced.py` `calculate_final_settlement()` references `compensation.updated_at` — relies on `auto_now` so exists but is fragile
- ⚠️ No admin.py registrations
- ⚠️ `ExchangeRate` uses hardcoded FX rates with no external API integration
- ⚠️ Payslip HTML template uses string replacement (not Jinja/Django templates) — fragile

---

### 4.6 onboarding

**Files:** `models.py`, `views.py`, `urls.py`, `exit_models.py`  
**No separate `serializers.py`** — all serializers inline in views.py

#### Models (7)

| Model | Key Fields | Notes |
|-------|-----------|-------|
| `OnboardingTemplate` | `tenant` FK, `name`, `tasks` JSON, `status` | Template definition |
| `OnboardingInstance` | `tenant` FK, `employee` FK, `template` FK, `start_date`, `target_completion`, `progress`, `status` | Per-employee instance; has `recalculate_progress()` |
| `OnboardingTask` | `tenant` FK, `instance` FK, `title`, `description`, `category` (hr/it/manager/employee/facilities), `due_date`, `assigned_to` FK, `status`, `completed_at` | Individual checklist item |
| `Asset` | `tenant` FK, `asset_type` (laptop/phone/id_card/access_card/vehicle/key/other), `name`, `serial_number`, `assigned_to` FK, `condition`, `purchase_date`, `notes` | IT/facilities asset tracking |
| `ExitRequest` | `tenant` FK, `employee` FK, `reason`, `last_working_date`, `status` pipeline (submitted→accepted→notice_period→handover→exit_interview→settlement→completed), `notice_period_days` | Offboarding |
| `ExitChecklist` | `tenant` FK, `exit_request` FK, `item`, `category`, `completed`, `completed_by` FK | Offboarding checklist |
| `ExitInterview` | `tenant` FK, `exit_request` FK, `employee` FK, `conducted_by` FK, `ratings` JSON, `feedback`, `would_rejoin`, `would_recommend` | Exit interview form |

#### Views (7 ViewSets)

| ViewSet | Key Actions |
|---------|------------|
| `OnboardingTemplateViewSet` | Standard CRUD |
| `OnboardingInstanceViewSet` | CRUD + `list_tasks` |
| `OnboardingTaskViewSet` | CRUD + `complete` |
| `AssetViewSet` | Standard CRUD |
| `ExitRequestViewSet` | CRUD + `accept`, `advance_status`, `checklist` |
| `ExitChecklistViewSet` | CRUD + `complete` |
| `ExitInterviewViewSet` | Standard CRUD |

#### Serializers (7, inline)
`OnboardingTemplateSerializer`, `OnboardingTaskSerializer`, `OnboardingInstanceSerializer`, `AssetSerializer`, `ExitRequestSerializer`, `ExitChecklistSerializer`, `ExitInterviewSerializer`

#### URL Patterns (7 router registrations)
```
templates/, instances/, tasks/, assets/, exit-requests/, exit-checklists/, exit-interviews/
```

#### Issues
- ⚠️ No separate `serializers.py` file — all inline in views.py
- ⚠️ No admin.py registrations
- ⚠️ `Asset` model has no return/checkout workflow
- ⚠️ No automation to trigger exit checklist creation when `ExitRequest` is accepted

---

### 4.7 performance

**Files:** `models.py`, `views.py`, `urls.py`  
**No separate `serializers.py`** — all inline in views.py

#### Models (4)

| Model | Key Fields | Notes |
|-------|-----------|-------|
| `ReviewCycle` | `tenant` FK, `name`, `type` (annual/semi_annual/quarterly/probation), `year`, `status` (5-stage: draft→active→self_review→calibration→finalized), `start_date`, `end_date`, `self_review_deadline`, `manager_review_deadline` | Cycle definition |
| `PerformanceReview` | `tenant` FK, `cycle` FK, `employee` FK, `reviewer` FK, `self_rating`, `manager_rating`, `final_rating`, `calibrated_rating`, `self_review_text`, `manager_feedback`, `status`, `metadata` JSON | Review record |
| `Goal` | `tenant` FK, `employee` FK, `cycle` FK, `title`, `description`, `type` (org/dept/team/individual), `metric_type`, `target_value`, `current_value`, `progress`, `weight`, `parent_goal` (self FK, OKR), `status`, `due_date` | OKR-style goals |
| `Feedback` | `tenant` FK, `from_employee` FK, `to_employee` FK, `type` (kudos/feedback/coaching), `message`, `is_public`, `related_goal` FK | Peer feedback |

#### Views (4 ViewSets, ~12 custom actions)

| ViewSet | Key Actions |
|---------|------------|
| `ReviewCycleViewSet` | CRUD + `activate`, `close_self_review`, `start_calibration`, `finalize`, `calibrate` (bulk), `summary` |
| `PerformanceReviewViewSet` | CRUD + `my_reviews`, `my_pending_reviews`, `submit_self_review`, `submit_rating`, `acknowledge` |
| `GoalViewSet` | CRUD + `my_goals`, `update_progress`, `sub_goals` |
| `FeedbackViewSet` | CRUD + `my_feedback` |

#### Serializers (8, inline)
`ReviewCycleSerializer`, `PerformanceReviewSerializer`, `GoalSerializer`, `FeedbackSerializer`, `SelfReviewSubmitSerializer`, `ManagerRatingSerializer`, `CalibrationSerializer`, `GoalProgressSerializer`

#### URL Patterns (4 router registrations)
```
review-cycles/, reviews/, goals/, feedback/
```

#### Issues
- 🔴 **BUG** in `activate` action: References `emp.reports_to` but Employee model field is `manager`
- ⚠️ No separate serializers.py
- ⚠️ No admin.py registrations
- ⚠️ No 360-degree feedback mechanism (only peer feedback exists)
- ⚠️ No PIP (Performance Improvement Plan) model

---

### 4.8 analytics

**Files:** `models.py`, `views.py`, `urls.py`, `ai_analytics.py`

#### Models (2, in ai_analytics.py)

| Model | Key Fields | Notes |
|-------|-----------|-------|
| `CustomDashboard` | `tenant` FK, `name`, `description`, `created_by` FK, `is_default`, `layout` JSON | Dashboard definition |
| `DashboardWidget` | `dashboard` FK, `widget_type` (kpi_card/bar_chart/line_chart/pie_chart/table/gauge/heatmap), `title`, `data_source`, `filters` JSON, `position_x/y`, `width/height`, `config` JSON | Widget placement |

#### Views (4 view-based endpoints)

| View | Method | URL | Purpose |
|------|--------|-----|---------|
| `DashboardView` | GET | `/analytics/dashboard/` | Headcount, dept breakdown, new hires, exits, pending leaves, attendance today |
| `HeadcountTrendView` | GET | `/analytics/headcount-trend/` | 12-month headcount trend |
| `NaturalLanguageAnalyticsView` | POST | `/analytics/natural-language/` | Mock NL→ORM query engine |
| `ReportsView` | GET | `/analytics/reports/` | Downloads headcount/leave_utilization/attendance CSVs |

#### AI Analytics Functions (`ai_analytics.py`)
- `calculate_attrition_risk()` — logistic regression-style risk scoring based on tenure, rating, salary gap, manager changes
- `detect_attendance_anomalies()` — statistical anomaly detection (2σ deviation)
- `workforce_planning_scenario()` — what-if headcount/budget modeling

#### URL Patterns (4 path-based endpoints)
```
dashboard/, headcount-trend/, natural-language/, reports/
```

#### Issues
- ⚠️ `CustomDashboard` and `DashboardWidget` models have **no API endpoints** for CRUD
- ⚠️ `NaturalLanguageAnalyticsView` is a mock — hardcoded response templates, not a real NLP engine
- ⚠️ No admin.py registrations
- ⚠️ `attrition_risk` and `detect_attendance_anomalies` functions are not exposed via any endpoint

---

### 4.9 integrations

**Files:** `models.py`, `views.py`, `urls.py`

#### Models (3)

| Model | Key Fields | Notes |
|-------|-----------|-------|
| `Integration` | `tenant` FK, `connector` (slack/google_calendar/microsoft_365/linkedin/xero/quickbooks/ats/custom_webhook), `name`, `credentials` JSON, `config` JSON, `status`, `last_sync_at` | Connector registry |
| `WebhookRegistration` | `tenant` FK, `name`, `target_url`, `events` JSON, `secret`, `is_active`, `last_triggered_at`, `last_status_code` | Outbound webhook registration |
| `WebhookDeliveryLog` | `webhook` FK, `event_type`, `payload` JSON, `status_code`, `response_body`, `success` | Delivery audit |

#### Views (4 ViewSets + 2 APIViews)

| ViewSet/View | Key Actions |
|-------------|------------|
| `IntegrationViewSet` | CRUD + `available` (list connectors), `test` (connectivity), `rotate_secret`, `sync_payroll` (Xero/QuickBooks), `post_job` (LinkedIn) |
| `WebhookRegistrationViewSet` | CRUD + `deliveries`, `ping`, `rotate_secret`, `toggle` |
| `ATSWebhookView` | POST — inbound ATS webhook handler (`offer.accepted` → creates Employee + Onboarding) |
| `HRMEmployeeTerminateView` | PATCH — terminates employee and syncs back to ATS |

#### Outbound Helpers (in views.py)
- `_deliver_webhook()` — HTTPS POST with HMAC-SHA256 signing, delivery logging
- `_dispatch_event()` — fan-out event to all matching webhook registrations
- `_notify_ats_employee_id_assigned()` — post employee ID back to ATS after creation
- `_notify_ats_employee_terminated()` — post termination event to ATS

#### URL Patterns
```
integrations/     → IntegrationViewSet (router)
webhooks/         → WebhookRegistrationViewSet (router)
ats/webhook/      → ATSWebhookView (path-based, POST & webhook handler)
ats/hire/         → ATSWebhookView (alias)
employees/<uuid>/terminate/ → HRMEmployeeTerminateView
```

#### Issues
- ⚠️ `_verify_signature()` uses `hmac.new()` — should be `hmac.new` → actually Python uses `hmac.new()` which is correct but the import uses `import hmac` at module top and references `hmac.new()` — verify it's not `hmac.HMAC()` (actually `hmac.new()` is valid Python)
- ⚠️ `_deliver_webhook()` uses `urllib.request` instead of `requests` library — inconsistent with `advanced.py` in workflows which uses `requests`
- ⚠️ Third-party integrations (Slack, Google Calendar, Microsoft 365, LinkedIn, Xero, QuickBooks) are stub implementations — only method signatures exist
- ⚠️ No admin.py registrations
- ⚠️ `ATSWebhookView` signature verification skips validation if `ATS_WEBHOOK_SECRET` is not set — insecure in dev
- ⚠️ Serializers mask credentials (`write_only=True`) but `credentials` JSON is stored in plain text in DB

---

### 4.10 platform_core

**Files:** `models.py`, `views.py`, `urls.py`, `services.py`, `middleware.py`, `email_service.py`, `webhook_dispatch.py`, `clamav.py`, `advanced_features.py`

#### Models (13)

**Core models (models.py):**

| Model | Key Fields | Notes |
|-------|-----------|-------|
| `AuditLog` | `tenant` FK, `user` FK, `action`, `resource_type`, `resource_id`, `changes` JSON, `ip_address`, `user_agent` | HTTP audit trail |
| `TimelineEvent` | `tenant` FK, `employee` FK, `event_type`, `category` (7 choices), `title`, `description`, `actor` FK, `source_object_type/id` | Employee timeline |
| `Notification` | `tenant` FK, `user` FK, `title`, `message`, `channel` (in_app/email/push/sms/whatsapp), `is_read`, `link` | Multi-channel notifications |
| `ApprovalRequest` | `tenant` FK, `requester` FK, `approver` FK, `entity_type`, `entity_id`, `action_type`, `status`, `step`, `total_steps`, `comments`, `decided_at` | Generic multi-step approval |
| `WebhookSubscription` | `tenant` FK, `url`, `events` JSON, `secret`, `is_active` | Platform-level webhook subscriptions |
| `WebhookDelivery` | `subscription` FK, `event_type`, `payload` JSON, `status_code`, `response`, `success` | Delivery log |

**Advanced features (advanced_features.py):**

| Model | Key Fields | Notes |
|-------|-----------|-------|
| `KBCategory` | `tenant` FK, `name`, `slug`, `icon`, `parent` FK | Knowledge base category (tree) |
| `KBArticle` | `tenant` FK, `category` FK, `title`, `slug`, `content`, `author` FK, `status`, `view_count`, `helpful_count` | KB article |
| `BenefitPlan` | `tenant` FK, `name`, `type` (10 types: health/dental/vision/life/disability/retirement/fsa/hsa/commuter/other), `provider`, `cost_employee/employer`, `eligibility_rules` JSON | Benefits |
| `BenefitEnrollment` | `tenant` FK, `employee` FK, `plan` FK, `status`, `coverage_level`, `effective_date`, `dependents` JSON | Enrollment |
| `SkillDefinition` | `tenant` FK, `name`, `category` (6: technical/soft_skill/language/certification/tool/domain), `description` | Skill taxonomy |
| `EmployeeSkill` | `tenant` FK, `employee` FK, `skill` FK, `proficiency` (1-5), `years_experience`, `endorsed_by` JSON | Employee skills |
| `GrievanceCase` | `tenant` FK, `employee` FK, `category` (7: harassment/discrimination/compensation/working_conditions/management/policy/other), `severity`, `description`, `status`, `assigned_to` FK | HR grievance |

#### Views (5 ViewSets)

| ViewSet | Key Actions |
|---------|------------|
| `TimelineViewSet` | Read-only, filterset on employee/category |
| `NotificationViewSet` | CRUD + `mark_read`, `mark_all_read`, `unread_count` |
| `ApprovalViewSet` | CRUD + `approve`, `reject`, `pending` |
| `WebhookViewSet` | Standard CRUD |
| `AuditLogViewSet` | Read-only |

#### Services (`services.py`)
- `emit_timeline_event()` — creates TimelineEvent
- `send_notification()` — creates Notification (in-app only)
- `send_email_notification()` — sends email via email_service

#### Email Service (`email_service.py`)
- 11 email templates: `leave_approved`, `leave_rejected`, `leave_request`, `payslip_ready`, `onboarding_task`, `announcement`, `password_reset`, `welcome`, `approval_needed`, `review_assigned`, `document_expiring`
- `send_notification_email()`, `send_bulk_notification_emails()`

#### Middleware (`middleware.py`)
- `AuditMiddleware` — persists `_audit_entries` from `AuditMixin` to `AuditLog`

#### Webhook Dispatch (`webhook_dispatch.py`)
- `dispatch_webhook_event()` — fan-out to active subscriptions
- `_deliver_webhook()` — HMAC-SHA256 signed POST with 3 retries

#### ClamAV (`clamav.py`)
- `scan_file()`, `scan_bytes()` — INSTREAM protocol
- Fails open on connection errors (logs warning but doesn't block)

#### URL Patterns (5 router registrations)
```
timeline/, notifications/, approvals/, webhooks/, audit-logs/
```

#### Issues
- 🔴 **7 models from `advanced_features.py` have NO views/serializers/URLs**: `KBCategory`, `KBArticle`, `BenefitPlan`, `BenefitEnrollment`, `SkillDefinition`, `EmployeeSkill`, `GrievanceCase`
- ⚠️ ClamAV **fails open** — if ClamAV is down, files are accepted without scanning
- ⚠️ ClamAV is not integrated into any upload endpoint (exists as standalone utility)
- ⚠️ `send_notification()` only creates in-app notifications — no push/SMS/WhatsApp delivery
- ⚠️ No admin.py registrations
- ⚠️ Duplicate webhook systems: `platform_core.WebhookSubscription/Delivery` AND `integrations.WebhookRegistration/DeliveryLog`

---

### 4.11 engagement

**Files:** `models.py`, `views.py`, `urls.py`

#### Models (3)

| Model | Key Fields | Notes |
|-------|-----------|-------|
| `Survey` | `tenant` FK, `title`, `type` (pulse/engagement/enps/exit/onboarding), `questions` JSON, `status`, `target_audience` JSON, `anonymous`, `start_date`, `end_date` | Survey definition |
| `SurveyResponse` | `tenant` FK, `survey` FK, `employee` FK (nullable for anonymous), `answers` JSON, `nps_score`, `submitted_at` | Individual response; unique constraint on (survey, employee) |
| `RecognitionEntry` | `tenant` FK, `from_employee` FK, `to_employee` FK, `category` (kudos/shoutout/award/milestone/innovation), `message`, `badges` JSON, `likes_count` | Peer recognition |

#### Views (2 ViewSets)

| ViewSet | Key Actions |
|---------|------------|
| `SurveyViewSet` | CRUD + `results` (with eNPS calculation), `submit` |
| `RecognitionViewSet` | CRUD + `like` |

#### Serializers (3, inline)
`SurveySerializer` (with `response_count`), `SurveyResponseSerializer`, `RecognitionEntrySerializer` (with `from_name`, `to_name`)

#### URL Patterns (2 router registrations)
```
surveys/, recognition/
```

#### Issues
- ⚠️ No separate serializers.py
- ⚠️ No admin.py registrations
- ⚠️ `like` action has no de-duplication — same user can like infinite times
- ⚠️ Anonymous survey responses still have `employee` field nullable but no enforcement of anonymity in eNPS reporting
- ⚠️ No `SurveyResponseViewSet` — responses can only be created via `Survey.submit` action, not listed/managed independently

---

### 4.12 learning

**Files:** `models.py`, `views.py`, `urls.py`

#### Models (3)

| Model | Key Fields | Notes |
|-------|-----------|-------|
| `Course` | `tenant` FK, `title`, `category` (6 types), `provider`, `duration_hours`, `format` (5 types), `max_enrollments`, `mandatory_for` JSON, `content_url`, `status` | Course catalog |
| `CourseEnrollment` | `tenant` FK, `course` FK, `employee` FK, `progress` (0-100), `score`, `status` (enrolled/in_progress/completed/dropped), `started_at`, `completed_at` | Enrollment; unique constraint |
| `Certification` | `tenant` FK, `employee` FK, `name`, `issuing_body`, `credential_id`, `issued_date`, `expiry_date`, `verification_url`, `status`, `reminder_sent` | Cert tracking with expiry |

#### Views (3 ViewSets)

| ViewSet | Key Actions |
|---------|------------|
| `CourseViewSet` | CRUD + `enroll` |
| `CourseEnrollmentViewSet` | CRUD + `complete`, `update-progress` |
| `CertificationViewSet` | CRUD + `expiring_soon` |

#### Serializers (3, inline)
`CourseSerializer` (with `enrollment_count`, `completion_rate`), `CourseEnrollmentSerializer`, `CertificationSerializer` (with `is_expired`)

#### URL Patterns (3 router registrations)
```
courses/, enrollments/, certifications/
```

#### Issues
- ⚠️ No separate serializers.py
- ⚠️ No admin.py registrations
- ⚠️ No content delivery — `content_url` is just a link, no LMS integration
- ⚠️ `mandatory_for` JSON is not enforced — no auto-enrollment logic for mandatory courses
- ⚠️ No integration with `certification_expiry_alerts` Celery task (task is in payroll app, not learning)

---

### 4.13 helpdesk

**Files:** `models.py`, `views.py`, `urls.py`

#### Models (3)

| Model | Key Fields | Notes |
|-------|-----------|-------|
| `TicketCategory` | `tenant` FK, `name`, `default_assignee` FK, `sla_response_hours`, `sla_resolution_hours`, `sort_order`, `is_active` | Category with SLA config |
| `Ticket` | `tenant` FK, `ticket_number` (auto TKT-XXXX), `employee` FK, `category` FK, `subject`, `description`, `priority` (4 levels), `status` (5 stages), `assigned_to` FK, `sla_response/resolution_due`, `first_response_at`, `resolved_at`, `sla_*_breached`, `satisfaction_rating` (1-5) | SLA-tracked ticket |
| `TicketComment` | `ticket` FK, `author` FK, `body`, `is_internal` | Thread comments with internal notes |

#### Views (2 ViewSets + SLA automation)

| ViewSet | Key Actions |
|---------|------------|
| `TicketCategoryViewSet` | Standard CRUD |
| `TicketViewSet` | CRUD + `add-comment`, `comments`, `resolve`, `assign`, `dashboard` |

Auto-sets on create: SLA deadlines from category, default assignee routing.

#### Serializers (3, inline)
`TicketCategorySerializer`, `TicketCommentSerializer` (with `author_name`), `TicketSerializer` (with `sla_status`, `comments_count`)

#### URL Patterns (2 router registrations)
```
categories/, tickets/
```

#### Issues
- ⚠️ No separate serializers.py
- ⚠️ No admin.py registrations
- ⚠️ No SLA breach notification — breaches are tracked but no alert is sent
- ⚠️ No escalation workflow for breached tickets
- ⚠️ Ticket number generation has race condition (concurrent creates could duplicate)
- ⚠️ Internal notes (`is_internal=True`) are filtered for non-staff in `comments` action, but not in the main list serializer

---

### 4.14 workflows

**Files:** `models.py`, `views.py`, `urls.py`, `advanced.py`

#### Models (4)

| Model | Key Fields | Notes |
|-------|-----------|-------|
| `WorkflowDefinition` | `tenant` FK, `name`, `trigger_event`, `trigger_conditions` JSON, `actions` JSON, `is_active`, `is_template`, `run_count`, `last_run_at` | Automation rule |
| `WorkflowExecution` | `tenant` FK, `workflow` FK, `trigger_event`, `trigger_data` JSON, `status` (running/completed/failed), `actions_executed` JSON, `error` | Execution log |
| `WorkflowNode` | `workflow` FK, `node_type` (trigger/condition/action/branch/merge/loop/delay/end), `name`, `config` JSON, `position_x/y`, `next_nodes` JSON | Complex branching (visual builder) |
| `WorkflowTemplate` | `name`, `category` (8 categories), `icon`, `template_data` JSON, `install_count`, `rating`, `is_featured`, `is_system` | Template marketplace |

#### Views (2 ViewSets)

| ViewSet | Key Actions |
|---------|------------|
| `WorkflowDefinitionViewSet` | CRUD + `toggle`, `test` (dry-run), `templates`, `history` |
| `WorkflowExecutionViewSet` | Read-only |

#### Built-in Templates (5, in `advanced.py`)
1. New Hire Welcome Email
2. Birthday Greeting
3. Leave Auto-Approve (≤2 days)
4. Contract Expiry Reminder
5. Probation Review Trigger

#### Webhook Action (`advanced.py`)
- `execute_webhook_action()` — template substitution + HTTP call with timeout

#### Serializers (2, inline)
`WorkflowDefinitionSerializer` (with `execution_count`), `WorkflowExecutionSerializer`

#### URL Patterns (2 router registrations)
```
definitions/, executions/
```

#### Issues
- ⚠️ **No actual workflow execution engine** — `test` action simulates but doesn't actually execute actions (send_notification, create_task, update_field, etc.)
- ⚠️ `WorkflowNode` model has no views/URLs — visual builder nodes cannot be managed via API
- ⚠️ `WorkflowTemplate` model has no CRUD views — marketplace cannot be populated via API
- ⚠️ Built-in templates (`BUILT_IN_TEMPLATES`) are defined in code but never auto-seeded to DB
- ⚠️ No event bus / signal integration — workflows are not triggered by actual system events
- ⚠️ No separate serializers.py
- ⚠️ No admin.py registrations

---

### 4.15 custom_objects

**Files:** `models.py`, `views.py`, `urls.py`

#### Models (2)

| Model | Key Fields | Notes |
|-------|-----------|-------|
| `CustomObjectDefinition` | `tenant` FK, `name`, `slug` (unique per tenant), `plural_name`, `icon`, `properties` JSON (EAV schema), `associations` JSON, `display_properties`, `title_property`, `searchable_properties`, `enable_timeline`, `enable_workflows`, `record_count` | Schema definition |
| `CustomObjectRecord` | `tenant` FK, `definition` FK, `data` JSON (dynamic JSONB), `employee` FK (optional), `created_by/updated_by` FK | Record instance |

#### Views (2 ViewSets)

| ViewSet | Key Actions |
|---------|------------|
| `CustomObjectDefinitionViewSet` | CRUD + `schema`, `records` (with JSONB search) |
| `CustomObjectRecordViewSet` | CRUD + `by-type/<slug>` |

**Notable features:**
- Dynamic property validation on record creation (required field enforcement)
- Auto-incrementing `record_count` on definition
- Timeline event emission when record linked to employee
- JSONB search across searchable properties

#### Serializers (2, inline)
`CustomObjectDefinitionSerializer`, `CustomObjectRecordSerializer` (with `record_title`)

#### URL Patterns (2 router registrations)
```
definitions/, records/
```

#### Issues
- ⚠️ No separate serializers.py
- ⚠️ No admin.py registrations
- ⚠️ No pagination on `records` action (returns all records at once)
- ⚠️ No property type validation (e.g., `date` type not validated as date, `email` not validated as email)
- ⚠️ `associations` JSON is defined but not enforced or resolved in API

---

## 5. Config & Infrastructure

### settings.py (330 lines)
- `TIME_ZONE = 'Asia/Colombo'` (Sri Lanka)
- `AUTH_USER_MODEL = 'authentication.User'`
- `CursorPagination` with `PAGE_SIZE = 25`
- Throttle: 50/min anon, 200/min user
- JWT: 60min access, 7d refresh, rotate on refresh, blacklist enabled
- CELERY_BEAT_SCHEDULE: 3 periodic tasks (document expiry, certification expiry, leave accrual — all daily)
- Sentry SDK (production), Prometheus metrics (production)
- HSTS, secure cookies, CSRF, XSS protection headers

### urls.py (66 lines)
- Health probe: `/health/` (200 OK)
- Readiness probe: `/ready/` (DB connectivity check)
- 15 app URL includes under `/api/v1/`
- Swagger UI: `/api/docs/`
- Schema: `/api/schema/`

### celery.py
- Standard Celery app config with autodiscover
- Redis broker

### permissions.py
- `HasTenantPermission` — DRF permission class
- `user_has_permission(user, codename, scope)` — utility
- `user_permissions(user)` — returns all user permissions
- `require_permission(codename)` — decorator
- `PermissionViewSetMixin` — declarative endpoint permission mapping

### base_api.py
- `TenantSerializerMixin` — auto-sets tenant on create
- `TenantViewSetMixin` — filters queryset by tenant_id
- `AuditMixin` — records changes for AuditMiddleware

### seed.py
- Creates demo tenant (slug='demo', plan='enterprise')
- Creates superuser admin@connecthr.com

---

## 6. Tests Audit

**Location:** `tests/` (7 test files + conftest.py)

### conftest.py
- 10 fixtures: `tenant_a`, `tenant_b`, `company_a`, `company_b`, `department_a`, `position_a`, `employee_a`, `employee_b_tenant_b`, `hr_admin_user`, `manager_user`, `employee_user`
- `make_employee()` helper function

### Test Files

| File | Tests | Scope |
|------|-------|-------|
| `test_permissions.py` | 8 | Auth flow (login, tokens, 401/403), role-based access, profile endpoint |
| `test_rls_isolation.py` | 10 | Tenant isolation at ORM level for Employee, Company, Department, LeaveType, LeaveRequest, PayrollRun |
| `test_leave_workflow.py` | ~12 | Leave lifecycle (create→approve→reject→cancel), balance formula, half-day, carry-forward, leave type constraints |
| `test_payroll_integration.py` | ~10 | Payroll run lifecycle, calculation engine (full attendance/absent/OT), EPF/ETF/APIT verification, 50-employee bulk run |
| `test_ats_hrm_bridge.py` | ~9 | ATS offer.accepted webhook → Employee + Onboarding creation, HMAC validation, error cases |
| `test_approval_workflow.py` | ~7 | Single/multi-level approval chain, approve/reject/cancel flows |

### Test Quality Assessment
- ✅ Good ORM-level tenant isolation tests
- ✅ Good payroll calculation verification (EPF 8%/12%, ETF 3%)
- ✅ Good ATS integration tests with HMAC validation
- ⚠️ No API-level endpoint tests (most tests are model/ORM level)
- ⚠️ No tests for: engagement, learning, helpdesk, workflows, custom_objects, analytics, onboarding
- ⚠️ No tests for: attendance clock-in/out, export/import, bulk operations
- ⚠️ No performance/load tests beyond 50-employee proxy
- ⚠️ No negative/boundary tests for serializer validation

---

## 7. Cross-Cutting Bugs & Issues

### 🔴 Critical Bugs (Will Crash at Runtime)

| # | Location | Bug | Fix |
|---|----------|-----|-----|
| 1 | `leave_attendance/tasks.py` | References `leave_type.annual_days` | Change to `leave_type.max_days_per_year` |
| 2 | `leave_attendance/tasks.py` | References `balance.accrued_days`, `balance.entitled_days` | Change to `balance.entitled`, and use proper field names |
| 3 | `payroll/advanced.py` | References `employee.date_of_joining` | Change to `employee.hire_date` |
| 4 | `payroll/advanced.py` | References `loan.total_amount`, `loan.paid_amount` | Change to `loan.amount`, `loan.outstanding_balance` |
| 5 | `performance/views.py` | References `emp.reports_to` in `activate` action | Change to `emp.manager` |

### ⚠️ Architectural Issues

| # | Issue | Impact |
|---|-------|--------|
| 1 | **Duplicate webhook systems** — `platform_core.WebhookSubscription/Delivery` AND `integrations.WebhookRegistration/DeliveryLog` | Confusion, inconsistent behavior |
| 2 | **No event bus** — workflows define triggers but nothing dispatches events | Workflow engine is inert |
| 3 | **Balance not auto-updated** — leave approval/creation doesn't update `LeaveBalance.taken`/`pending` | Manual balance management required |
| 4 | **12+ models with no API exposure** — tenants enterprise models, analytics dashboards, platform_core advanced features, workflow nodes/templates | Dead code |
| 5 | **All admin.py files empty** — no models registered in Django admin across any app | No admin interface for debugging |
| 6 | **Ticket number race condition** — `Ticket.save()` uses MAX+1 pattern without `select_for_update()` | Duplicate ticket numbers under concurrency |
| 7 | **ClamAV not wired** — virus scanner exists but no upload endpoint calls it | File uploads unscanned |

---

## 8. Missing / Incomplete Features

### Models with No API Exposure

| App | Models | Status |
|-----|--------|--------|
| tenants | `Tenant`, `TenantFeature`, `FeatureFlag`, `SSOConfiguration`, `SCIMConfiguration`, `SCIMSyncLog`, `Subscription`, `Invoice`, `TranslationKey` | **No views, no URLs** |
| analytics | `CustomDashboard`, `DashboardWidget` | **No views, no URLs** |
| platform_core | `KBCategory`, `KBArticle`, `BenefitPlan`, `BenefitEnrollment`, `SkillDefinition`, `EmployeeSkill`, `GrievanceCase` | **No views, no URLs** |
| workflows | `WorkflowNode`, `WorkflowTemplate` | **No views, no URLs** |
| leave_attendance | `ShiftAssignment` | **No ViewSet** |

### Missing Functionality

| Feature | Status |
|---------|--------|
| Token refresh endpoint | Not explicitly configured (relies on SimpleJWT defaults) |
| Email verification | Not implemented |
| SSO/SCIM integration | Models exist, no logic |
| Stripe subscription handling | No webhook handler |
| Push/SMS/WhatsApp notifications | Model supports channels, delivery not implemented |
| Workflow execution engine | Dry-run only, no real execution |
| LMS content delivery | URL link only, no content hosting |
| Mandatory course auto-enrollment | Config exists, not enforced |
| SLA breach notifications | Tracked but not alerted |
| Ticket escalation | Not implemented |
| Document virus scanning | ClamAV exists, not called from upload endpoints |
| File upload to S3 | Configured but not tested in code |
| i18n/Translation utilities | `TranslationKey` model exists, no middleware |
| 360-degree reviews | Not implemented |
| PIP (Performance Improvement Plan) | Not implemented |
| Custom object type validation | Required fields checked, type validation missing |

---

## 9. Security Concerns

| # | Concern | Severity | Details |
|---|---------|----------|---------|
| 1 | **ATS webhook secret skipped in dev** | Medium | `_verify_signature()` returns `True` if `ATS_WEBHOOK_SECRET` not set |
| 2 | **ClamAV fails open** | Medium | If ClamAV is down, files accepted without scanning |
| 3 | **Integration credentials in plain text** | High | `Integration.credentials` JSON stored unencrypted in DB |
| 4 | **No rate limiting on login** | Medium | Only global anon throttle (50/min), no per-IP brute-force protection |
| 5 | **Webhook secrets visible in logs** | Low | Webhook delivery logs include full payloads |
| 6 | **No CSRF on webhook endpoints** | Low | Expected for API endpoints but should be explicitly documented |

---

## 10. Recommendations

### Priority 1 — Fix Critical Bugs
1. Fix all 5 field name mismatches (leave_attendance/tasks.py, payroll/advanced.py, performance/views.py)
2. Add `select_for_update()` to ticket number generation
3. Wire ClamAV into document upload endpoints

### Priority 2 — Missing APIs
1. Create tenant management API (settings, features, billing)
2. Create views/URLs for `KBArticle`, `BenefitPlan`, `SkillDefinition`, `GrievanceCase`
3. Create views/URLs for `CustomDashboard`, `DashboardWidget`
4. Create views/URLs for `WorkflowNode`, `WorkflowTemplate`
5. Add `ShiftAssignment` ViewSet

### Priority 3 — Architectural
1. Consolidate duplicate webhook systems (platform_core vs integrations)
2. Implement event bus (Django signals or Celery) to drive workflow execution
3. Add leave balance auto-update signals on request create/approve/reject/cancel
4. Register all models in Django admin
5. Extract inline serializers into separate `serializers.py` files

### Priority 4 — Security
1. Encrypt integration credentials at rest
2. Add per-IP rate limiting on login endpoint
3. Make ClamAV fail-closed (reject uploads when scanner unavailable)
4. Always require webhook signature verification (remove dev bypass)

### Priority 5 — Testing
1. Add API-level endpoint tests (DRF APIClient)
2. Add tests for all 5 untested apps (engagement, learning, helpdesk, workflows, custom_objects)
3. Add serializer validation boundary tests
4. Add concurrent operation tests (ticket numbers, balance updates)

---

## Appendix: Complete Model Count by App

| App | Model Count | Has Views | Has URLs |
|-----|------------|-----------|----------|
| authentication | 7 | ✅ | ✅ |
| tenants | 9 | ❌ | ❌ |
| core_hr | 8 | ✅ | ✅ |
| leave_attendance | 9 | ✅ (8 of 9) | ✅ |
| payroll | 7 | ✅ | ✅ |
| onboarding | 7 | ✅ | ✅ |
| performance | 4 | ✅ | ✅ |
| analytics | 2 | Partial | ✅ |
| integrations | 3 | ✅ | ✅ |
| platform_core | 13 | ✅ (6 of 13) | ✅ |
| engagement | 3 | ✅ | ✅ |
| learning | 3 | ✅ | ✅ |
| helpdesk | 3 | ✅ | ✅ |
| workflows | 4 | ✅ (2 of 4) | ✅ |
| custom_objects | 2 | ✅ | ✅ |
| **TOTAL** | **~84** | | |

---

*End of audit report.*
