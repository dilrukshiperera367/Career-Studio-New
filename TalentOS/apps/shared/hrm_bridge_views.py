"""
ATS endpoint that receives lifecycle events from HRM system.
Handles: employee termination (updates candidate availability record).
"""
import hashlib
import hmac
import logging

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger('ats.bridge')


def _verify_hrm_signature(request) -> bool:
    """Verify HMAC-SHA256 signature from HRM webhook delivery."""
    secret = getattr(settings, 'HRM_WEBHOOK_SECRET', '')
    if not secret:
        if getattr(settings, 'DEBUG', False):
            logger.warning("HRM_WEBHOOK_SECRET not configured — skipping verification in dev mode")
            return True
        logger.error("HRM_WEBHOOK_SECRET not configured — rejecting unsigned webhook in production")
        return False
    sig_header = request.headers.get('X-HRM-Signature', '')
    if not sig_header:
        return False
    try:
        expected = hmac.new(secret.encode(), request.body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(f"sha256={expected}", sig_header)
    except Exception:
        return False


class HRMEmployeeTerminatedView(APIView):
    """
    POST /api/v1/integrations/hrm/employee-terminated
    Receives employee.terminated event from HRM system.
    Updates the source candidate record's availability to 'immediate'.
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        if not _verify_hrm_signature(request):
            logger.warning("HRM bridge signature mismatch — rejected")
            return Response({'error': 'Invalid signature'}, status=status.HTTP_401_UNAUTHORIZED)

        payload = request.data
        candidate_id = payload.get('candidate_id')
        employee_id = payload.get('employee_id')
        reason = payload.get('reason', 'terminated')

        if not candidate_id:
            logger.info(f"HRM termination event received but no candidate_id — employee_id={employee_id}")
            return Response({'status': 'ignored', 'reason': 'no candidate_id'})

        try:
            from apps.candidates.models import Candidate
            updated = Candidate.objects.filter(id=candidate_id).update(
                availability='immediate',
            )
            logger.info(
                f"HRM bridge: candidate {candidate_id} availability set to 'immediate' "
                f"(employee {employee_id} terminated, reason: {reason}). "
                f"Records updated: {updated}"
            )

            # Log to audit log if available
            try:
                from apps.shared.models import AuditLog
                AuditLog.objects.create(
                    action='update',
                    resource_type='candidate',
                    resource_id=str(candidate_id),
                    changes={
                        'source': 'hrm_bridge',
                        'employee_id': employee_id,
                        'reason': reason,
                    },
                )
            except Exception:
                pass

            return Response({'status': 'synced', 'candidate_id': candidate_id, 'updated': updated})

        except Exception as e:
            logger.error(f"HRM bridge termination sync error: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HRMEmployeeCreatedView(APIView):
    """
    POST /api/v1/integrations/hrm/employee-created
    Receives confirmation from HRM after successful hire → employee creation.
    Stores the HRM employee_id back onto the ATS offer/application records.
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        if not _verify_hrm_signature(request):
            return Response({'error': 'Invalid signature'}, status=status.HTTP_401_UNAUTHORIZED)

        payload = request.data
        candidate_id = payload.get('candidate_id')
        employee_id = payload.get('employee_id')
        employee_number = payload.get('employee_number', '')

        if not candidate_id or not employee_id:
            return Response({'error': 'candidate_id and employee_id required'}, status=status.HTTP_400_BAD_REQUEST)

        updated = 0
        try:
            from apps.applications.models import Offer
            # Store HRM employee ID on the accepted offer record
            updated = Offer.objects.filter(
                candidate_id=candidate_id,
                status='accepted',
            ).update(
                hrm_employee_id=str(employee_id),
            )
        except Exception as e:
            logger.warning(f"Could not write hrm_employee_id to Offer: {e}")

        logger.info(f"HRM bridge: employee-created ack — candidate={candidate_id}, employee={employee_id}, updated={updated}")
        return Response({'status': 'acknowledged', 'updated': updated})
