"""Bulk import utilities for CSV data ingestion."""
import csv
import io
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated

try:
    from apps.candidates.models import Candidate
except ImportError:
    Candidate = None


class ImportCandidatesView(APIView):
    """
    POST /api/v1/import/candidates/
    Accepts multipart CSV upload. Creates Candidate records.

    Expected CSV columns: first_name, last_name, email, phone, location, headline
    Maps to Candidate fields: full_name, primary_email, primary_phone, location, headline
    """
    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not Candidate:
            return JsonResponse({'error': 'Candidates module unavailable'}, status=500)

        file = request.FILES.get('file')
        if not file:
            return JsonResponse({'error': 'No file uploaded. Use field name "file".'}, status=400)

        if not file.name.endswith('.csv'):
            return JsonResponse({'error': 'Only CSV files are accepted.'}, status=400)

        try:
            content = file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(content))
            rows = list(reader)
        except Exception as e:
            return JsonResponse({'error': f'Could not parse CSV: {e}'}, status=400)

        created = 0
        errors = []
        tenant_id = getattr(request, 'tenant_id', None)

        for i, row in enumerate(rows, start=2):  # row 1 = header
            email = (row.get('email') or '').strip().lower()
            first_name = (row.get('first_name') or '').strip()
            last_name = (row.get('last_name') or '').strip()
            full_name = f'{first_name} {last_name}'.strip() or 'Unknown'

            if not email:
                errors.append({'row': i, 'error': 'email is required'})
                continue
            if not tenant_id:
                errors.append({'row': i, 'error': 'Cannot determine tenant'})
                continue

            if Candidate.objects.filter(primary_email=email, tenant_id=tenant_id).exists():
                errors.append({'row': i, 'error': f'Duplicate email: {email}'})
                continue

            try:
                candidate_data = {
                    'full_name': full_name,
                    'primary_email': email,
                    'tenant_id': tenant_id,
                    'source': 'csv_import',
                }
                phone = (row.get('phone') or '').strip()
                if phone:
                    candidate_data['primary_phone'] = phone
                location = (row.get('location') or '').strip()
                if location:
                    candidate_data['location'] = location
                headline = (row.get('headline') or '').strip()
                if headline:
                    candidate_data['headline'] = headline
                Candidate.objects.create(**candidate_data)
                created += 1
            except Exception as e:
                errors.append({'row': i, 'error': str(e)})

        return JsonResponse({
            'imported': created,
            'errors': errors,
            'total_rows': len(rows),
        }, status=207 if errors else 201)
