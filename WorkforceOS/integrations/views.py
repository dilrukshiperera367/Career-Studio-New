"""Integrations API — inbound webhook receiver + outbound connector/webhook management."""

import hashlib
import hmac
import json
import logging
import secrets

from rest_framework import viewsets, serializers, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from django.utils import timezone

from config.base_api import TenantViewSetMixin, TenantSerializerMixin
from core_hr.models import Employee, Company, Department, Position
from onboarding.models import OnboardingTemplate, OnboardingInstance, OnboardingTask
from platform_core.services import emit_timeline_event, send_notification
from .models import Integration, WebhookRegistration, WebhookDeliveryLog

logger = logging.getLogger('hrm')


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

class IntegrationSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    """Masks credential values in responses."""
    credentials_masked = serializers.SerializerMethodField()

    class Meta:
        model = Integration
        fields = ['id', 'tenant', 'connector', 'name', 'status', 'config',
                  'credentials_masked', 'last_sync_at', 'error_message', 'created_at', 'updated_at']
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at', 'credentials_masked']

    def get_credentials_masked(self, obj):
        """Return keys with masked values so frontend knows which creds are set."""
        return {k: '***' for k in (obj.credentials or {})}


class IntegrationWriteSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Integration
        fields = ['connector', 'name', 'status', 'credentials', 'config']

    def validate_connector(self, value):
        valid = [c[0] for c in Integration.CONNECTOR_CHOICES]
        if value not in valid:
            raise serializers.ValidationError(f'Unknown connector. Valid: {valid}')
        return value


class WebhookRegistrationSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    delivery_count = serializers.SerializerMethodField()

    class Meta:
        model = WebhookRegistration
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at',
                            'last_triggered_at', 'last_status_code']
        extra_kwargs = {
            'secret': {'write_only': True},  # Never return raw secret
        }

    def get_delivery_count(self, obj):
        return obj.deliveries.count()


class WebhookDeliveryLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookDeliveryLog
        fields = '__all__'


# ---------------------------------------------------------------------------
# Integration connector views
# ---------------------------------------------------------------------------

CONNECTOR_CAPABILITIES = {
    'slack': {
        'description': 'Send HR notifications to Slack channels',
        'required_config': ['channel_id'],
        'required_credentials': ['bot_token'],
        'supported_events': ['employee.created', 'leave.approved', 'review.finalized', 'onboarding.completed'],
    },
    'google_calendar': {
        'description': 'Sync interview/meeting schedules to Google Calendar',
        'required_config': ['calendar_id'],
        'required_credentials': ['access_token', 'refresh_token', 'client_id', 'client_secret'],
        'supported_events': ['interview.scheduled'],
    },
    'microsoft_365': {
        'description': 'Sync with Microsoft Teams and Outlook calendar',
        'required_config': ['tenant_id_ms', 'calendar_id'],
        'required_credentials': ['access_token', 'refresh_token', 'client_id', 'client_secret'],
        'supported_events': ['interview.scheduled', 'employee.created'],
    },
    'linkedin': {
        'description': 'Post job openings to LinkedIn',
        'required_config': ['organization_id'],
        'required_credentials': ['access_token'],
        'supported_events': [],
    },
    'xero': {
        'description': 'Export payroll data to Xero accounting',
        'required_config': ['xero_tenant_id'],
        'required_credentials': ['access_token', 'refresh_token'],
        'supported_events': ['payroll.finalized'],
    },
    'quickbooks': {
        'description': 'Export payroll data to QuickBooks',
        'required_config': ['realm_id'],
        'required_credentials': ['access_token', 'refresh_token'],
        'supported_events': ['payroll.finalized'],
    },
    'ats': {
        'description': 'Internal ATS system integration (hire events)',
        'required_config': [],
        'required_credentials': ['webhook_secret'],
        'supported_events': ['offer.accepted'],
    },
    'custom_webhook': {
        'description': 'Custom HTTP endpoint integration',
        'required_config': ['endpoint_url', 'method'],
        'required_credentials': [],
        'supported_events': ['*'],
    },
}


class IntegrationViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    """CRUD for tenant connector installations."""
    queryset = Integration.objects.all()
    filterset_fields = ['connector', 'status']

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return IntegrationWriteSerializer
        return IntegrationSerializer

    @action(detail=False, methods=['get'])
    def available(self, request):
        """
        List all available connector types with their capabilities.
        Each entry shows whether it's installed for this tenant.
        """
        installed = {
            i.connector: i.status
            for i in Integration.objects.filter(tenant_id=request.tenant_id)
        }
        result = []
        for connector, caps in CONNECTOR_CAPABILITIES.items():
            result.append({
                'connector': connector,
                'description': caps['description'],
                'required_config': caps['required_config'],
                'required_credentials': caps['required_credentials'],
                'supported_events': caps['supported_events'],
                'installed': connector in installed,
                'installed_status': installed.get(connector),
            })
        return Response({'data': result})

    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """
        Test connectivity for an installed integration.
        Returns success/failure based on a lightweight ping.
        """
        integration = self.get_object()
        connector = integration.connector

        result = {'connector': connector, 'success': False, 'message': ''}

        try:
            if connector == 'slack':
                result = self._test_slack(integration)
            elif connector == 'xero':
                result = self._test_xero(integration)
            elif connector in ('google_calendar', 'microsoft_365'):
                # OAuth connectors — just verify token presence
                has_token = bool(integration.credentials.get('access_token'))
                result = {
                    'connector': connector,
                    'success': has_token,
                    'message': 'Access token present' if has_token else 'Missing access_token credential',
                }
            else:
                result = {
                    'connector': connector,
                    'success': integration.status == 'active',
                    'message': f'Integration status: {integration.status}',
                }

            if result['success']:
                integration.status = 'active'
                integration.error_message = ''
            else:
                integration.status = 'error'
                integration.error_message = result.get('message', 'Test failed')
            integration.save(update_fields=['status', 'error_message', 'updated_at'])

        except Exception as exc:
            logger.exception('Integration test failed for %s', connector)
            integration.status = 'error'
            integration.error_message = str(exc)
            integration.save(update_fields=['status', 'error_message', 'updated_at'])
            result = {'connector': connector, 'success': False, 'message': str(exc)}

        return Response({'data': result})

    def _test_slack(self, integration):
        import urllib.request
        token = integration.credentials.get('bot_token', '')
        if not token:
            return {'connector': 'slack', 'success': False, 'message': 'Missing bot_token'}
        req = urllib.request.Request(
            'https://slack.com/api/auth.test',
            headers={'Authorization': f'Bearer {token}'},
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                return {'connector': 'slack', 'success': data.get('ok', False),
                        'message': data.get('error', 'Connected') if not data.get('ok') else f"Connected as {data.get('user', '')}"}
        except Exception as e:
            return {'connector': 'slack', 'success': False, 'message': str(e)}

    def _test_xero(self, integration):
        token = integration.credentials.get('access_token', '')
        if not token:
            return {'connector': 'xero', 'success': False, 'message': 'Missing access_token'}
        return {'connector': 'xero', 'success': True, 'message': 'Credentials present (live check requires OAuth refresh)'}

    @action(detail=True, methods=['post'])
    def rotate_secret(self, request, pk=None):
        """Generate a new webhook/signing secret for this integration."""
        integration = self.get_object()
        new_secret = secrets.token_hex(32)
        creds = integration.credentials or {}
        creds['webhook_secret'] = new_secret
        integration.credentials = creds
        integration.save(update_fields=['credentials', 'updated_at'])
        return Response({'data': {'secret': new_secret}, 'meta': {'message': 'Secret rotated — update your webhook config'}})

    @action(detail=True, methods=['post'])
    def sync_payroll(self, request, pk=None):
        """
        Push a finalized payroll run to an accounting connector (Xero/QuickBooks).
        Body: {payroll_run_id}
        """
        integration = self.get_object()
        if integration.connector not in ('xero', 'quickbooks'):
            return Response({'error': 'This action is only for Xero or QuickBooks integrations'},
                            status=status.HTTP_400_BAD_REQUEST)
        if integration.status != 'active':
            return Response({'error': 'Integration is not active'},
                            status=status.HTTP_400_BAD_REQUEST)

        run_id = request.data.get('payroll_run_id')
        if not run_id:
            return Response({'error': 'payroll_run_id required'}, status=status.HTTP_400_BAD_REQUEST)

        from payroll.models import PayrollRun
        try:
            run = PayrollRun.objects.get(id=run_id, tenant_id=request.tenant_id)
        except PayrollRun.DoesNotExist:
            return Response({'error': 'Payroll run not found'}, status=status.HTTP_404_NOT_FOUND)

        if run.status != 'finalized':
            return Response({'error': 'Only finalized payroll runs can be synced'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Stub: real implementation would call Xero/QB API
        # Mark run as synced in metadata
        meta = run.metadata if hasattr(run, 'metadata') and run.metadata else {}
        meta[f'{integration.connector}_synced_at'] = timezone.now().isoformat()
        if hasattr(run, 'metadata'):
            run.metadata = meta
            run.save(update_fields=['metadata'])

        integration.last_sync_at = timezone.now()
        integration.save(update_fields=['last_sync_at', 'updated_at'])

        return Response({'meta': {'message': f'Payroll run {run_id} queued for sync to {integration.connector}'}})

    @action(detail=True, methods=['post'])
    def post_job(self, request, pk=None):
        """
        Post a job opening to LinkedIn.
        Body: {job_id}
        """
        integration = self.get_object()
        if integration.connector != 'linkedin':
            return Response({'error': 'This action is only for LinkedIn integration'},
                            status=status.HTTP_400_BAD_REQUEST)
        if integration.status != 'active':
            return Response({'error': 'Integration is not active'},
                            status=status.HTTP_400_BAD_REQUEST)

        job_id = request.data.get('job_id')
        if not job_id:
            return Response({'error': 'job_id required'}, status=status.HTTP_400_BAD_REQUEST)

        # Stub — real implementation calls LinkedIn Jobs API
        integration.last_sync_at = timezone.now()
        integration.save(update_fields=['last_sync_at', 'updated_at'])
        return Response({'meta': {'message': f'Job {job_id} queued for posting to LinkedIn'}})


# ---------------------------------------------------------------------------
# Webhook management views
# ---------------------------------------------------------------------------

class WebhookRegistrationViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    """Manage outbound webhook subscriptions for a tenant."""
    queryset = WebhookRegistration.objects.all()
    serializer_class = WebhookRegistrationSerializer
    filterset_fields = ['is_active']

    def perform_create(self, serializer):
        # Auto-generate a signing secret if not provided
        secret = serializer.validated_data.get('secret') or secrets.token_hex(32)
        serializer.save(secret=secret)

    @action(detail=True, methods=['get'])
    def deliveries(self, request, pk=None):
        """Recent delivery log for this webhook."""
        webhook = self.get_object()
        qs = webhook.delivery_logs.order_by('-delivered_at')[:50]
        return Response({'data': WebhookDeliveryLogSerializer(qs, many=True).data})

    @action(detail=True, methods=['post'])
    def ping(self, request, pk=None):
        """Send a test ping payload to the registered URL."""
        webhook = self.get_object()
        if not webhook.is_active:
            return Response({'error': 'Webhook is inactive'}, status=status.HTTP_400_BAD_REQUEST)

        payload = {
            'event': 'ping',
            'webhook_id': str(webhook.id),
            'message': 'Test ping from HRM System',
        }

        success, resp_code, resp_body = _deliver_webhook(webhook, 'ping', payload)

        return Response({
            'data': {'success': success, 'status_code': resp_code, 'response': resp_body[:500]},
            'meta': {'message': 'Ping sent' if success else 'Ping failed'},
        })

    @action(detail=True, methods=['post'])
    def rotate_secret(self, request, pk=None):
        """Generate a new signing secret."""
        webhook = self.get_object()
        webhook.secret = secrets.token_hex(32)
        webhook.save(update_fields=['secret', 'updated_at'])
        return Response({
            'data': {'secret': webhook.secret},
            'meta': {'message': 'Webhook secret rotated — update your receiver verification'},
        })

    @action(detail=True, methods=['post'])
    def toggle(self, request, pk=None):
        """Enable or disable this webhook."""
        webhook = self.get_object()
        webhook.is_active = not webhook.is_active
        webhook.save(update_fields=['is_active', 'updated_at'])
        state = 'enabled' if webhook.is_active else 'disabled'
        return Response({'data': WebhookRegistrationSerializer(webhook).data,
                         'meta': {'message': f'Webhook {state}'}})


# ---------------------------------------------------------------------------
# Inbound ATS webhook receiver (unchanged logic, moved here)
# ---------------------------------------------------------------------------

class ATSWebhookView(APIView):
    """Receives hire events from the ATS system."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # Verify webhook signature
        signature = request.META.get('HTTP_X_WEBHOOK_SIGNATURE', '')
        if not self._verify_signature(request.body, signature):
            return Response({'error': 'Invalid signature'}, status=status.HTTP_401_UNAUTHORIZED)

        data = request.data
        event_type = data.get('event')

        if event_type == 'offer.accepted':
            return self._handle_offer_accepted(data)
        else:
            return Response({'meta': {'message': f'Event {event_type} not handled'}})

    def _handle_offer_accepted(self, data):
        """Create employee from accepted offer."""
        candidate = data.get('data', {})
        tenant_id = data.get('tenant_id')

        if not tenant_id:
            return Response({'error': 'tenant_id required'}, status=400)

        company = Company.objects.filter(tenant_id=tenant_id).first()
        if not company:
            return Response({'error': 'No company found for tenant'}, status=400)

        department = None
        if candidate.get('department_name'):
            department, _ = Department.objects.get_or_create(
                tenant_id=tenant_id,
                company=company,
                name=candidate.get('department_name')
            )

        position = None
        if candidate.get('job_title'):
            position, _ = Position.objects.get_or_create(
                tenant_id=tenant_id,
                title=candidate.get('job_title'),
                defaults={'department': department}
            )

        employee = Employee.objects.create(
            tenant_id=tenant_id,
            company=company,
            first_name=candidate.get('first_name', ''),
            last_name=candidate.get('last_name', ''),
            work_email=candidate.get('email', ''),
            personal_email=candidate.get('email', ''),
            mobile_phone=candidate.get('phone', ''),
            hire_date=candidate.get('start_date', None),
            position=position,
            department=department,
            source='ats_import',
            ats_candidate_id=candidate.get('candidate_id'),
            status='probation',
        )

        template = OnboardingTemplate.objects.filter(
            tenant_id=tenant_id, status='active'
        ).first()

        if template:
            from datetime import timedelta
            instance = OnboardingInstance.objects.create(
                tenant_id=tenant_id,
                employee=employee,
                template=template,
                start_date=employee.hire_date,
                target_completion=employee.hire_date + timedelta(days=30),
            )
            for i, task_def in enumerate(template.tasks or []):
                due = employee.hire_date + timedelta(days=task_def.get('due_offset_days', 7))
                OnboardingTask.objects.create(
                    tenant_id=tenant_id,
                    instance=instance,
                    title=task_def.get('title', ''),
                    description=task_def.get('description', ''),
                    category=task_def.get('category', 'hr'),
                    due_date=due,
                    sort_order=i,
                )

        emit_timeline_event(
            tenant_id=tenant_id,
            employee=employee,
            event_type='employee.created',
            category='hr',
            title=f'{employee.full_name} hired via ATS',
            actor_type='system',
        )

        # Fire outbound webhooks for employee.created
        _dispatch_event(str(tenant_id), 'employee.created', {
            'employee_id': str(employee.id),
            'employee_number': employee.employee_number,
            'full_name': employee.full_name,
        })

        # ── Back-write employee ID to ATS offer record ────────────────────────
        _notify_ats_employee_id_assigned(employee)

        return Response({
            'data': {'employee_id': str(employee.id), 'employee_number': employee.employee_number},
            'meta': {'message': 'Employee created from ATS hire'}
        }, status=status.HTTP_201_CREATED)

    def _verify_signature(self, payload, signature):
        secret = getattr(settings, 'ATS_WEBHOOK_SECRET', None)
        if not secret:
            if getattr(settings, 'DEBUG', False):
                return True  # Skip verification in local dev only
            return False  # Reject unsigned webhooks in production
        expected = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(f'sha256={expected}', signature)


# ---------------------------------------------------------------------------
# Outbound delivery utilities
# ---------------------------------------------------------------------------

def _deliver_webhook(webhook: WebhookRegistration, event_type: str, payload: dict):
    """
    Deliver a webhook payload to the target URL over HTTPS.
    Returns (success: bool, status_code: int, response_body: str).
    """
    import urllib.request
    import urllib.error

    body = json.dumps(payload).encode('utf-8')
    sig = ''
    if webhook.secret:
        sig = 'sha256=' + hmac.new(webhook.secret.encode(), body, hashlib.sha256).hexdigest()

    req = urllib.request.Request(
        webhook.target_url,
        data=body,
        method='POST',
        headers={
            'Content-Type': 'application/json',
            'X-HRM-Event': event_type,
            'X-HRM-Signature': sig,
            'X-HRM-Webhook-ID': str(webhook.id),
        },
    )

    success = False
    resp_code = None
    resp_body = ''

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_code = resp.status
            resp_body = resp.read(2048).decode('utf-8', errors='replace')
            success = 200 <= resp_code < 300
    except urllib.error.HTTPError as e:
        resp_code = e.code
        resp_body = e.read(512).decode('utf-8', errors='replace')
    except Exception as exc:
        resp_body = str(exc)

    # Log the delivery attempt
    WebhookDeliveryLog.objects.create(
        webhook=webhook,
        event_type=event_type,
        payload=payload,
        status_code=resp_code,
        response_body=resp_body[:2000],
        success=success,
    )

    webhook.last_triggered_at = timezone.now()
    webhook.last_status_code = resp_code
    webhook.save(update_fields=['last_triggered_at', 'last_status_code', 'updated_at'])

    return success, resp_code, resp_body


def _dispatch_event(tenant_id: str, event_type: str, data: dict):
    """
    Fan-out an event to all active webhooks subscribed to it for this tenant.
    Should ideally be called from a Celery task in production.
    """
    payload = {
        'event': event_type,
        'tenant_id': tenant_id,
        'data': data,
        'sent_at': timezone.now().isoformat(),
    }
    webhooks = WebhookRegistration.objects.filter(
        tenant_id=tenant_id,
        is_active=True,
    )
    for wh in webhooks:
        subscribed = wh.events or []
        if '*' in subscribed or event_type in subscribed:
            try:
                _deliver_webhook(wh, event_type, payload)
            except Exception as exc:
                logger.exception('Webhook delivery failed for %s: %s', wh.id, exc)


# ---------------------------------------------------------------------------
# HRM → ATS bi-directional sync: employee termination callback
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# HRM → ATS bi-directional sync helpers
# ---------------------------------------------------------------------------

def _notify_ats_employee_id_assigned(employee):
    """
    Fire a POST to the ATS immediately after an employee record is created
    so the ATS can write the HRM employee_id back to the Offer record.
    """
    import urllib.request, urllib.error, json as _json, hashlib as _hl

    ats_candidate_id = getattr(employee, 'ats_candidate_id', None)
    if not ats_candidate_id:
        return  # Not an ATS-sourced employee

    ats_url = getattr(settings, 'ATS_BASE_URL_FRONTEND', None)
    if not ats_url:
        return

    callback_url = ats_url.rstrip('/') + '/api/v1/integrations/hrm/webhook/'
    secret = getattr(settings, 'HRM_WEBHOOK_SECRET', '') or getattr(settings, 'ATS_WEBHOOK_SECRET', '')

    payload = {
        'event': 'employee.id_assigned',
        'tenant_id': str(employee.tenant_id),
        'data': {
            'ats_candidate_id': str(ats_candidate_id),
            'employee_id': str(employee.id),
            'employee_number': employee.employee_number,
        },
    }

    body = _json.dumps(payload).encode('utf-8')
    sig = ''
    if secret:
        sig = 'sha256=' + hmac.new(secret.encode(), body, _hl.sha256).hexdigest()

    req = urllib.request.Request(
        callback_url,
        data=body,
        method='POST',
        headers={
            'Content-Type': 'application/json',
            'X-HRM-Event': 'employee.id_assigned',
            'X-HRM-Signature': sig,
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info('ATS employee_id_assigned sync succeeded (HTTP %s)', resp.status)
    except Exception as exc:
        logger.warning('ATS employee_id_assigned sync failed: %s', exc)


def _notify_ats_employee_terminated(employee, termination_reason: str = ''):
    """
    Fire a POST to the ATS to update the candidate's status when an employee
    is terminated in HRM.  This keeps ATS talent-pool records in sync.

    Called from HRMEmployeeTerminateView after persisting the termination.
    Uses SHARED_JWT_SECRET / ATS_WEBHOOK_SECRET for HMAC signing.
    Non-blocking: errors are logged but do not bubble up to the API response.
    """
    import urllib.request, urllib.error, json as _json, hashlib as _hl

    ats_candidate_id = getattr(employee, 'ats_candidate_id', None)
    if not ats_candidate_id:
        return  # Employee was not created from ATS; nothing to sync

    ats_url = getattr(settings, 'ATS_BASE_URL_FRONTEND', None) or getattr(settings, 'ATS_WEBHOOK_URL', None)
    if not ats_url:
        logger.warning('ATS_BASE_URL_FRONTEND not configured — skipping termination sync')
        return

    # Resolve the ATS inbound webhook endpoint
    callback_url = ats_url.rstrip('/') + '/api/v1/integrations/hrm/webhook/'
    secret = getattr(settings, 'HRM_WEBHOOK_SECRET', '') or getattr(settings, 'ATS_WEBHOOK_SECRET', '')

    payload = {
        'event': 'employee.terminated',
        'tenant_id': str(employee.tenant_id),
        'data': {
            'employee_id': str(employee.id),
            'ats_candidate_id': str(ats_candidate_id),
            'employee_number': employee.employee_number,
            'full_name': employee.full_name,
            'termination_date': employee.termination_date.isoformat() if employee.termination_date else None,
            'termination_reason': termination_reason,
            'new_status': 'hired_terminated',  # ATS-side status label
        },
    }

    body = _json.dumps(payload).encode('utf-8')
    sig = ''
    if secret:
        sig = 'sha256=' + hmac.new(secret.encode(), body, _hl.sha256).hexdigest()

    req = urllib.request.Request(
        callback_url,
        data=body,
        method='POST',
        headers={
            'Content-Type': 'application/json',
            'X-HRM-Event': 'employee.terminated',
            'X-HRM-Signature': sig,
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info('ATS termination sync succeeded for candidate %s (HTTP %s)',
                        ats_candidate_id, resp.status)
    except urllib.error.HTTPError as e:
        logger.warning('ATS termination sync HTTP error %s for candidate %s', e.code, ats_candidate_id)
    except Exception as exc:
        logger.warning('ATS termination sync failed for candidate %s: %s', ats_candidate_id, exc)


class HRMEmployeeTerminateView(APIView):
    """
    PATCH /employees/{id}/terminate/

    Marks an employee as terminated, records the separation details, and
    fires a callback to the ATS to update the linked candidate record.
    """
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, employee_id):
        from core_hr.models import Employee as EmpModel
        from core_hr.models import JobHistory

        try:
            employee = EmpModel.objects.get(id=employee_id, tenant=request.user.tenant)
        except EmpModel.DoesNotExist:
            return Response({'error': 'Employee not found'}, status=status.HTTP_404_NOT_FOUND)

        if employee.status == 'terminated':
            return Response({'error': 'Employee already terminated'},
                            status=status.HTTP_400_BAD_REQUEST)

        previous_status = employee.status
        termination_date = request.data.get('termination_date')
        termination_reason = request.data.get('reason', '')
        rehire_eligible = request.data.get('rehire_eligible', True)

        from django.utils.dateparse import parse_date
        t_date = parse_date(termination_date) if termination_date else timezone.now().date()

        # Persist termination
        employee.status = 'terminated'
        employee.termination_date = t_date
        employee.save(update_fields=['status', 'termination_date', 'updated_at'])

        # Record job history entry
        JobHistory.objects.create(
            tenant=employee.tenant,
            employee=employee,
            effective_date=t_date,
            change_type='termination',
            new_status='terminated',
            previous_status=previous_status,
            note=termination_reason,
            actor=request.user,
        )

        # Timeline event
        emit_timeline_event(
            tenant_id=str(employee.tenant_id),
            employee=employee,
            event_type='employee.terminated',
            category='hr',
            title=f'{employee.full_name} terminated — {termination_reason}',
            actor_type='user',
            actor_id=str(request.user.id),
        )

        # Fan-out to registered outbound webhooks
        _dispatch_event(str(employee.tenant_id), 'employee.terminated', {
            'employee_id': str(employee.id),
            'employee_number': employee.employee_number,
            'full_name': employee.full_name,
            'termination_date': t_date.isoformat(),
            'termination_reason': termination_reason,
            'rehire_eligible': rehire_eligible,
        })

        # Bi-directional ATS sync
        _notify_ats_employee_terminated(employee, termination_reason)

        return Response({
            'data': {'employee_id': str(employee.id), 'status': 'terminated'},
            'meta': {'message': 'Employee terminated and ATS notified'}
        })
