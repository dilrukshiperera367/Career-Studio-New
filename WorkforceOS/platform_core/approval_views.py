"""
Generic approval request API — standalone endpoints outside the platform prefix.
Works for leave, bank-detail changes, salary changes, etc.

Adapts to the real ApprovalRequest model fields:
  approver     (FK User)   — the user who must action this request
  requester    (FK User)   — who submitted the request
  comments     (TextField) — decision comments
  decided_at   (DateTimeField)
"""
import logging
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

logger = logging.getLogger('hrm.approvals')


class ApprovalRequestListView(APIView):
    """GET /api/v1/approvals/ — list pending approvals assigned to the current user."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            from platform_core.models import ApprovalRequest
            qs = ApprovalRequest.objects.filter(
                approver=request.user,
                status='pending',
                tenant=request.tenant,
            ).select_related('requester').order_by('-created_at')

            data = [{
                'id': str(obj.id),
                'entity_type': obj.entity_type,
                'entity_id': str(obj.entity_id),
                'action_type': obj.action_type,
                'requested_by': str(obj.requester),
                'created_at': obj.created_at.isoformat(),
                'comments': obj.comments or '',
                'metadata': obj.metadata or {},
                'step': obj.step,
                'total_steps': obj.total_steps,
            } for obj in qs]
            return Response({'results': data, 'count': len(data)})
        except AttributeError:
            # request.tenant not set (e.g. missing TenantMiddleware)
            return Response({'results': [], 'count': 0, 'detail': 'Tenant context missing.'})
        except Exception as e:
            logger.error(f"ApprovalRequestListView error: {e}")
            return Response({'results': [], 'count': 0})


class ApprovalActionView(APIView):
    """POST /api/v1/approvals/{pk}/approve/  or  /api/v1/approvals/{pk}/reject/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, action):
        if action not in ('approve', 'reject'):
            return Response({'error': 'Invalid action. Use "approve" or "reject".'}, status=400)

        try:
            from platform_core.models import ApprovalRequest
            obj = ApprovalRequest.objects.get(id=pk, tenant=request.tenant)
        except Exception:
            return Response({'error': 'Approval request not found.'}, status=404)

        if obj.approver != request.user:
            return Response({'error': 'This approval is not assigned to you.'}, status=403)

        if obj.status != 'pending':
            return Response({'error': f'Request is already {obj.status}.'}, status=400)

        obj.status = 'approved' if action == 'approve' else 'rejected'
        obj.comments = request.data.get('comment', obj.comments or '')
        obj.decided_at = timezone.now()
        obj.save(update_fields=['status', 'comments', 'decided_at', 'updated_at'])

        # Fire workflow event for downstream automation
        try:
            from workflows.engine import fire_event
            fire_event(f'approval.{action}d', {
                'approval_id': str(obj.id),
                'entity_type': obj.entity_type,
                'entity_id': str(obj.entity_id),
                'action_type': obj.action_type,
                'tenant_id': str(request.tenant.id),
            })
        except Exception as e:
            logger.warning(f"Workflow fire_event after approval action failed: {e}")

        return Response({'status': obj.status, 'id': str(obj.id)})
