"""
ATS → HRM Bridge endpoint.
Receives offer.accepted webhook from ATS, creates Employee record, triggers onboarding.
"""
import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core_hr.models import Employee, Department, Position
from onboarding.models import OnboardingTemplate, OnboardingInstance
from platform_core.models import AuditLog

logger = logging.getLogger('hrm.bridge')


class BridgeError(Exception):
    pass


def _verify_ats_signature(request) -> bool:
    secret = getattr(settings, 'ATS_WEBHOOK_SECRET', '')
    if not secret:
        # In DEBUG mode allow unsigned requests for local development only
        if getattr(settings, 'DEBUG', False):
            logger.warning("ATS_WEBHOOK_SECRET not configured — skipping signature verification (DEBUG only)")
            return True
        logger.error("ATS_WEBHOOK_SECRET not configured — rejecting unsigned webhook in production")
        return False
    sig_header = request.headers.get('X-ATS-Signature', '')
    expected = hmac.new(
        secret.encode(),
        request.body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", sig_header)


def _map_candidate_to_employee(payload: dict, tenant) -> dict:
    """Map ATS offer payload fields to Employee model fields."""
    candidate = payload.get('candidate', {})
    offer = payload.get('offer', {})
    job = payload.get('job', {})

    first_name = candidate.get('first_name') or candidate.get('name', '').split()[0] if candidate.get('name') else ''
    last_name = candidate.get('last_name') or (' '.join(candidate.get('name', '').split()[1:]) if candidate.get('name') else '')

    return {
        'first_name': first_name,
        'last_name': last_name,
        'email': candidate.get('email') or candidate.get('primary_email', ''),
        'phone': candidate.get('phone', ''),
        'hire_date': offer.get('start_date'),
        'employment_type': 'full_time',
        'status': 'active',
        'source': 'ats_import',
        'ats_candidate_id': str(candidate.get('id', '')),
        'position_title': job.get('title', ''),
        'tenant': tenant,
    }


class ATSHireWebhookView(APIView):
    """
    POST /api/v1/integrations/ats/hire
    Receives offer.accepted event from ATS system.
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        if not _verify_ats_signature(request):
            logger.warning("ATS webhook signature mismatch")
            return Response({'error': 'Invalid signature'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            payload = request.data
        except Exception:
            return Response({'error': 'Invalid JSON'}, status=status.HTTP_400_BAD_REQUEST)

        event_type = payload.get('event')
        if event_type != 'offer.accepted':
            return Response({'status': 'ignored', 'event': event_type}, status=status.HTTP_200_OK)

        # Get tenant from payload or header
        tenant_id = payload.get('tenant_id') or request.headers.get('X-Tenant-ID')
        if not tenant_id:
            return Response({'error': 'tenant_id required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from tenants.models import Tenant
            tenant = Tenant.objects.get(id=tenant_id)
        except Exception:
            logger.error(f"Bridge: unknown tenant_id={tenant_id}")
            return Response({'error': 'Unknown tenant'}, status=status.HTTP_404_NOT_FOUND)

        try:
            with transaction.atomic():
                employee = self._create_employee(payload, tenant)
                self._trigger_onboarding(employee, payload)
                self._log_bridge_event(tenant, employee, payload)

            logger.info(f"Bridge: created employee {employee.id} from ATS candidate {payload.get('candidate', {}).get('id')}")
            return Response({
                'status': 'created',
                'employee_id': str(employee.id),
                'employee_number': employee.employee_number,
            }, status=status.HTTP_201_CREATED)

        except BridgeError as e:
            logger.error(f"Bridge error: {e}")
            self._create_bridge_error_record(tenant, payload, str(e))
            return Response({'error': str(e)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        except Exception as e:
            logger.exception(f"Bridge unexpected error: {e}")
            self._create_bridge_error_record(tenant, payload, str(e))
            return Response({'error': 'Internal bridge error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _create_employee(self, payload, tenant):
        fields = _map_candidate_to_employee(payload, tenant)

        # Check for duplicate by email
        email = fields.get('email', '')
        if email:
            existing = Employee.objects.filter(tenant=tenant, email=email).first()
            if existing:
                logger.info(f"Bridge: employee with email {email} already exists (id={existing.id})")
                return existing

        # Try to resolve department / position from payload
        job = payload.get('job', {})
        dept_name = job.get('department')
        if dept_name:
            dept = Department.objects.filter(tenant=tenant, name__iexact=dept_name).first()
            if dept:
                fields['department'] = dept

        try:
            employee = Employee.objects.create(**{k: v for k, v in fields.items() if v is not None and v != ''})
        except Exception as e:
            raise BridgeError(f"Failed to create employee: {e}")

        return employee

    def _trigger_onboarding(self, employee, payload):
        """Auto-trigger default onboarding template if available."""
        try:
            template = OnboardingTemplate.objects.filter(
                tenant=employee.tenant,
                is_active=True,
            ).order_by('-created_at').first()
            if template:
                OnboardingInstance.objects.create(
                    employee=employee,
                    template=template,
                    status='active',
                )
                logger.info(f"Bridge: triggered onboarding template '{template.name}' for employee {employee.id}")
        except Exception as e:
            logger.warning(f"Bridge: could not trigger onboarding: {e}")

    def _log_bridge_event(self, tenant, employee, payload):
        try:
            AuditLog.objects.create(
                tenant=tenant,
                action='bridge.employee_created',
                entity_type='employee',
                entity_id=str(employee.id),
                metadata={
                    'source': 'ats_bridge',
                    'ats_candidate_id': payload.get('candidate', {}).get('id'),
                    'event': payload.get('event'),
                },
            )
        except Exception:
            pass  # Non-fatal

    def _create_bridge_error_record(self, tenant, payload, error_message):
        try:
            AuditLog.objects.create(
                tenant=tenant,
                action='bridge.error',
                entity_type='bridge',
                entity_id='',
                metadata={
                    'error': error_message,
                    'payload_snapshot': json.dumps(payload)[:2000],
                },
            )
        except Exception:
            pass


class ATSTerminationSyncView(APIView):
    """
    POST /api/v1/integrations/ats/terminate
    Called by HRM to notify ATS when employee is terminated.
    Alternatively — this view RECEIVES termination events from ATS (bidirectional).
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        if not _verify_ats_signature(request):
            return Response({'error': 'Invalid signature'}, status=status.HTTP_401_UNAUTHORIZED)

        payload = request.data
        ats_candidate_id = payload.get('candidate_id')
        separation_reason = payload.get('reason', 'resigned')
        separation_date = payload.get('separation_date')

        if not ats_candidate_id:
            return Response({'error': 'candidate_id required'}, status=status.HTTP_400_BAD_REQUEST)

        employees = Employee.objects.filter(ats_candidate_id=str(ats_candidate_id))
        updated = employees.update(
            status='terminated',
            separation_type=separation_reason,
        )

        return Response({'status': 'synced', 'employees_updated': updated})
