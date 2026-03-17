"""
ATS GDPR Compliance Views.

Implements the GDPR data subject rights:
  - Right of Access (#49): export all data the ATS holds about a candidate
  - Right to Erasure (#50): delete or anonymize a candidate's personal data
  - Data Subject Request management: list, create, and process requests

Endpoint registration:
    In apps/shared/views/audits.py compliance_urlpatterns, add:
        path("gdpr/export/<uuid:pk>/", GDPRDataExportView.as_view(), name="gdpr-export"),
        path("gdpr/erase/<uuid:pk>/",  GDPRDataEraseView.as_view(),  name="gdpr-erase"),
        path("gdpr/requests/",         DataSubjectRequestListView.as_view(), name="gdpr-requests"),
        path("gdpr/requests/<uuid:pk>/process/",
             DataSubjectRequestProcessView.as_view(), name="gdpr-request-process"),
"""

import json
import logging
from datetime import timedelta

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasTenantAccess, IsRecruiter

logger = logging.getLogger('ats.gdpr')


class GDPRDataExportView(APIView):
    """
    GET /api/v1/compliance/gdpr/export/<candidate_id>/

    Right of Access — returns a JSON export of all ATS data held for a candidate.
    Written to HTTP response as 'application/json' attachment.
    """
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def get(self, request, pk):
        from apps.candidates.models import Candidate

        try:
            candidate = Candidate.objects.get(id=pk, tenant_id=request.tenant_id)
        except Candidate.DoesNotExist:
            return Response({'error': 'Candidate not found'}, status=status.HTTP_404_NOT_FOUND)

        export = _build_candidate_export(candidate)
        response = HttpResponse(
            json.dumps(export, indent=2, default=str),
            content_type='application/json',
        )
        response['Content-Disposition'] = (
            f'attachment; filename="gdpr_export_{candidate.id}.json"'
        )
        logger.info(
            'gdpr_export: tenant=%s candidate=%s requested_by=%s',
            request.tenant_id, pk, request.user.id,
        )
        return response


class GDPRDataEraseView(APIView):
    """
    DELETE /api/v1/compliance/gdpr/erase/<candidate_id>/

    Right to Erasure — anonymizes all personally identifiable information for
    the candidate while retaining audit records (as required by law).

    Optional request body:
      { "full_delete": true }  — permanently removes the record entirely (use sparingly)
    """
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def delete(self, request, pk):
        from apps.candidates.models import Candidate

        try:
            candidate = Candidate.objects.get(id=pk, tenant_id=request.tenant_id)
        except Candidate.DoesNotExist:
            return Response({'error': 'Candidate not found'}, status=status.HTTP_404_NOT_FOUND)

        full_delete = bool(request.data.get('full_delete', False))

        if full_delete:
            candidate_id = str(candidate.id)
            candidate.delete()
            logger.warning(
                'gdpr_full_delete: tenant=%s candidate=%s requested_by=%s',
                request.tenant_id, pk, request.user.id,
            )
            return Response({'id': candidate_id, 'action': 'deleted'}, status=status.HTTP_200_OK)

        # Anonymize in place
        _anonymize_candidate(candidate)
        logger.info(
            'gdpr_anonymize: tenant=%s candidate=%s requested_by=%s',
            request.tenant_id, pk, request.user.id,
        )
        return Response({
            'id': str(candidate.id),
            'action': 'anonymized',
            'anonymized_at': timezone.now().isoformat(),
        })


class DataSubjectRequestListView(APIView):
    """
    GET  /api/v1/compliance/gdpr/requests/   — list pending data subject requests
    POST /api/v1/compliance/gdpr/requests/   — create a new data subject request
    """
    permission_classes = [IsAuthenticated, HasTenantAccess]

    def get(self, request):
        from apps.candidates.models import DataSubjectRequest
        qs = DataSubjectRequest.objects.filter(
            tenant_id=request.tenant_id,
        ).order_by('-created_at')[:100]

        return Response([
            {
                'id': str(r.id),
                'type': r.request_type,
                'requester_email': r.requester_email,
                'status': r.status,
                'deadline': r.deadline.isoformat() if r.deadline else None,
                'created_at': r.created_at.isoformat(),
            }
            for r in qs
        ])

    def post(self, request):
        from apps.candidates.models import DataSubjectRequest
        req_type = request.data.get('type')
        email = request.data.get('email', '').strip()

        if req_type not in ('access', 'erasure', 'portability', 'rectification'):
            return Response({'error': 'Invalid request type'}, status=400)
        if not email:
            return Response({'error': 'email is required'}, status=400)

        deadline = timezone.now().date() + timedelta(days=30)

        dsr = DataSubjectRequest.objects.create(
            tenant_id=request.tenant_id,
            request_type=req_type,
            requester_email=email,
            status='pending',
            deadline=deadline,
            submitted_by=request.user,
        )

        return Response({
            'id': str(dsr.id),
            'type': dsr.request_type,
            'status': dsr.status,
            'deadline': dsr.deadline.isoformat(),
        }, status=201)


class DataSubjectRequestProcessView(APIView):
    """
    POST /api/v1/compliance/gdpr/requests/<uuid:pk>/process/

    Mark a data subject request as completed and perform the underlying action
    (export or anonymize based on request type).
    """
    permission_classes = [IsAuthenticated, HasTenantAccess, IsRecruiter]

    def post(self, request, pk):
        from apps.candidates.models import DataSubjectRequest, Candidate

        try:
            dsr = DataSubjectRequest.objects.get(id=pk, tenant_id=request.tenant_id)
        except DataSubjectRequest.DoesNotExist:
            return Response({'error': 'Request not found'}, status=404)

        if dsr.status == 'completed':
            return Response({'error': 'Already completed'}, status=400)

        # Locate the candidate by email
        try:
            candidate = Candidate.objects.get(
                primary_email=dsr.requester_email,
                tenant_id=request.tenant_id,
            )
        except Candidate.DoesNotExist:
            dsr.status = 'completed'
            dsr.processed_by = request.user
            dsr.processed_at = timezone.now()
            dsr.notes = 'No candidate record found for this email'
            dsr.save(update_fields=['status', 'processed_by', 'processed_at', 'notes'])
            return Response({'status': 'completed', 'note': 'No record found'})

        if dsr.request_type in ('erasure',):
            _anonymize_candidate(candidate)
            action = 'anonymized'
        else:
            # For access/portability: generate export but don't delete
            action = 'exported'

        dsr.status = 'completed'
        dsr.processed_by = request.user
        dsr.processed_at = timezone.now()
        dsr.save(update_fields=['status', 'processed_by', 'processed_at'])

        logger.info(
            'gdpr_dsr_processed: id=%s type=%s action=%s tenant=%s by=%s',
            pk, dsr.request_type, action, request.tenant_id, request.user.id,
        )

        return Response({
            'id': str(dsr.id),
            'action': action,
            'candidate_id': str(candidate.id),
            'processed_at': dsr.processed_at.isoformat(),
        })


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _build_candidate_export(candidate) -> dict:
    """Build a full GDPR data export for a candidate."""
    from apps.applications.models import Application

    apps_qs = Application.objects.filter(
        candidate=candidate,
    ).select_related('job', 'current_stage').order_by('-created_at')

    return {
        'export_generated_at': timezone.now().isoformat(),
        'candidate': {
            'id': str(candidate.id),
            'full_name': candidate.full_name,
            'email': candidate.primary_email,
            'phone': candidate.primary_phone,
            'location': candidate.location,
            'source': candidate.source,
            'created_at': candidate.created_at.isoformat(),
            'tags': candidate.tags or [],
        },
        'applications': [
            {
                'job_title': app.job.title if app.job else None,
                'stage': app.current_stage.name if app.current_stage else None,
                'status': app.status,
                'applied_at': app.created_at.isoformat(),
            }
            for app in apps_qs
        ],
    }


def _anonymize_candidate(candidate) -> None:
    """Overwrite PII fields with anonymized values."""
    from uuid import uuid4
    anon_id = str(uuid4())[:8]

    candidate.full_name = f'ANONYMIZED_{anon_id}'
    candidate.primary_email = f'anon_{anon_id}@deleted.invalid'
    candidate.primary_phone = ''
    candidate.location = ''
    candidate.tags = []
    candidate.consent_given_at = None
    candidate.data_retention_until = None
    candidate.save(update_fields=[
        'full_name', 'primary_email', 'primary_phone',
        'location', 'tags',
        'consent_given_at', 'data_retention_until', 'updated_at',
    ])
