"""Custom Prometheus metrics for HRM."""
try:
    from prometheus_client import Counter, Histogram, Gauge

    employees_created_total = Counter(
        'hrm_employees_created_total',
        'Total employees created',
        ['tenant_id']
    )

    leave_requests_total = Counter(
        'hrm_leave_requests_total',
        'Total leave requests',
        ['tenant_id', 'status']
    )

    payroll_runs_total = Counter(
        'hrm_payroll_runs_total',
        'Total payroll runs',
        ['tenant_id', 'status']
    )

    active_employees_gauge = Gauge(
        'hrm_active_employees',
        'Number of active employees across all tenants'
    )

    active_tenants_gauge = Gauge(
        'hrm_active_tenants',
        'Number of active tenants'
    )

    def record_employee_created(tenant_id: str):
        try:
            employees_created_total.labels(tenant_id=str(tenant_id)).inc()
        except Exception:
            pass

    def record_leave_request(tenant_id: str, status: str = 'pending'):
        try:
            leave_requests_total.labels(tenant_id=str(tenant_id), status=status).inc()
        except Exception:
            pass

    def update_employee_gauge():
        try:
            from core_hr.models import Employee
            active_employees_gauge.set(Employee.objects.filter(is_active=True).count())
        except Exception:
            pass

    METRICS_AVAILABLE = True

except ImportError:
    METRICS_AVAILABLE = False
    def record_employee_created(*args, **kwargs): pass
    def record_leave_request(*args, **kwargs): pass
    def update_employee_gauge(): pass
