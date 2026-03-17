"""
ATS — Inbound HRM webhook receiver.

Handles callbacks from the HRM system:
  - employee.terminated  → update linked candidate record status
  - employee.id_assigned → write HRM employee_id back onto the ATS offer record
"""

import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger('ats')


def _verify_hrm_signature(payload: bytes, signature: str) -> bool:
    """Validate X-HRM-Signature header using HRM_WEBHOOK_SECRET (or SHARED_JWT_SECRET)."""
    secret = getattr(settings, 'HRM_WEBHOOK_SECRET', '') or getattr(settings, 'SHARED_JWT_SECRET', '')
    if not secret:
        if getattr(settings, 'DEBUG', False):
            logger.debug('HRM_WEBHOOK_SECRET not set — skipping signature verification (dev mode)')
            return True
        logger.error('HRM_WEBHOOK_SECRET not configured — rejecting unsigned webhook in production')
        return False
    expected = 'sha256=' + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@method_decorator(csrf_exempt, name='dispatch')
class HRMWebhookView(APIView):
    """
    POST /api/v1/integrations/hrm/webhook/

    Receives event callbacks from the HRM system.
    Registered handlers:
      • employee.terminated   — mark linked candidate as 'hired_terminated'
      • employee.id_assigned  — write hrm_employee_id back to the matching Offer record
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        signature = request.META.get('HTTP_X_HRM_SIGNATURE', '')
        if not _verify_hrm_signature(request.body, signature):
            return Response({'error': 'Invalid signature'}, status=status.HTTP_401_UNAUTHORIZED)

        data = request.data
        event_type = data.get('event')

        dispatch = {
            'employee.terminated': self._handle_employee_terminated,
            'employee.id_assigned': self._handle_employee_id_assigned,
        }

        handler = dispatch.get(event_type)
        if handler:
            return handler(data)

        logger.debug('HRM webhook: unhandled event %s', event_type)
        return Response({'meta': {'message': f'Event {event_type} acknowledged'}})

    # ─────────────────────────────────────────────────────────────────────────
    # Handlers
    # ─────────────────────────────────────────────────────────────────────────

    def _handle_employee_terminated(self, data: dict) -> Response:
        """
        When HRM marks an employee as terminated, update the ATS candidate's
        status to 'hired_terminated' so recruiters can see they have re-hire
        potential or need a replacement hire.
        """
        from apps.candidates.models import Candidate

        payload = data.get('data', {})
        ats_candidate_id = payload.get('ats_candidate_id')
        tenant_id = data.get('tenant_id')
        termination_date = payload.get('termination_date')
        reason = payload.get('termination_reason', '')

        if not ats_candidate_id:
            return Response({'error': 'ats_candidate_id required in data payload'},
                            status=status.HTTP_400_BAD_REQUEST)

        updated = Candidate.objects.filter(
            id=ats_candidate_id,
            tenant_id=tenant_id,
        ).update(
            status='hired_terminated',
        )

        if updated == 0:
            logger.warning('HRM termination sync: candidate %s not found for tenant %s',
                           ats_candidate_id, tenant_id)
            return Response({'error': 'Candidate not found'}, status=status.HTTP_404_NOT_FOUND)

        logger.info('HRM termination sync: candidate %s marked hired_terminated', ats_candidate_id)
        return Response({'meta': {'message': 'Candidate status updated to hired_terminated'}})

    def _handle_employee_id_assigned(self, data: dict) -> Response:
        """
        When HRM creates an employee and assigns an employee ID, write that
        employee_id back onto the ATS Offer record so ATS can display it.
        """
        from apps.applications.models import Offer

        payload = data.get('data', {})
        ats_candidate_id = payload.get('ats_candidate_id')
        hrm_employee_id = payload.get('employee_id')
        hrm_employee_number = payload.get('employee_number', '')
        tenant_id = data.get('tenant_id')

        if not (ats_candidate_id and hrm_employee_id):
            return Response({'error': 'ats_candidate_id and employee_id required'},
                            status=status.HTTP_400_BAD_REQUEST)

        updated = Offer.objects.filter(
            application__candidate_id=ats_candidate_id,
            application__tenant_id=tenant_id,
            status='accepted',
        ).update(
            hrm_employee_id=hrm_employee_id,
            hrm_employee_number=hrm_employee_number,
        )

        if updated == 0:
            logger.warning('HRM employee_id_assigned: no accepted offer found for candidate %s',
                           ats_candidate_id)

        logger.info('HRM employee_id_assigned: offer updated with employee %s / %s',
                    hrm_employee_id, hrm_employee_number)
        return Response({'meta': {'message': 'Offer updated with HRM employee ID'}})
