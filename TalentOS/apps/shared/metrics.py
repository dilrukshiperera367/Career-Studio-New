"""Custom Prometheus metrics for ATS."""
try:
    from prometheus_client import Counter, Histogram, Gauge, Info

    # API request metrics
    api_requests_total = Counter(
        'ats_api_requests_total',
        'Total API requests',
        ['method', 'endpoint', 'status_code', 'tenant_id']
    )

    # Business metrics
    candidates_created_total = Counter(
        'ats_candidates_created_total',
        'Total candidates created',
        ['tenant_id', 'source']
    )

    jobs_published_total = Counter(
        'ats_jobs_published_total',
        'Total jobs published',
        ['tenant_id']
    )

    applications_submitted_total = Counter(
        'ats_applications_submitted_total',
        'Total applications submitted',
        ['tenant_id']
    )

    active_tenants_gauge = Gauge(
        'ats_active_tenants',
        'Number of active tenants'
    )

    trial_tenants_gauge = Gauge(
        'ats_trial_tenants',
        'Number of tenants in trial'
    )

    # Task processing
    celery_tasks_processed = Counter(
        'ats_celery_tasks_total',
        'Total Celery tasks processed',
        ['task_name', 'status']
    )

    def record_candidate_created(tenant_id: str, source: str = 'manual'):
        try:
            candidates_created_total.labels(tenant_id=str(tenant_id), source=source).inc()
        except Exception:
            pass

    def record_job_published(tenant_id: str):
        try:
            jobs_published_total.labels(tenant_id=str(tenant_id)).inc()
        except Exception:
            pass

    def record_application_submitted(tenant_id: str):
        try:
            applications_submitted_total.labels(tenant_id=str(tenant_id)).inc()
        except Exception:
            pass

    def update_tenant_gauges():
        """Update tenant count gauges - call from a periodic task."""
        try:
            from apps.tenants.models import Tenant
            active_tenants_gauge.set(Tenant.objects.filter(status='active').count())
            trial_tenants_gauge.set(Tenant.objects.filter(status='trial').count())
        except Exception:
            pass

    METRICS_AVAILABLE = True

except ImportError:
    METRICS_AVAILABLE = False

    def record_candidate_created(*args, **kwargs): pass
    def record_job_published(*args, **kwargs): pass
    def record_application_submitted(*args, **kwargs): pass
    def update_tenant_gauges(): pass
