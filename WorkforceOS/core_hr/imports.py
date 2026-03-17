import csv
import io
import datetime
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from .models import Employee, Company, Department, Branch, Position

def bulk_import_employees(file_obj, tenant, user):
    """
    Parses a CSV file and bulk inserts Employees.
    Expected headers: first_name, last_name, work_email, mobile_phone, hire_date, company, department, branch, position
    """
    try:
        decoded_file = file_obj.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        return {'success': False, 'errors': ['File must be a valid UTF-8 encoded CSV.']}
        
    reader = csv.DictReader(io.StringIO(decoded_file))
    
    if not reader.fieldnames or 'first_name' not in reader.fieldnames:
        return {'success': False, 'errors': ['Invalid CSV format. Expected headers including first_name, last_name, etc.']}
    
    employees_to_create = []
    errors = []
    
    # Pre-fetch lookup dictionaries for foreign keys to minimize DB hits
    companies = {c.name.lower(): c for c in Company.objects.filter(tenant=tenant)}
    departments = {d.name.lower(): d for d in Department.objects.filter(tenant=tenant)}
    branches = {b.name.lower(): b for b in Branch.objects.filter(tenant=tenant)}
    positions = {p.title.lower(): p for p in Position.objects.filter(tenant=tenant)}
    
    for row_num, row in enumerate(reader, start=2): # Row 2 because of headers
        try:
            first_name = row.get('first_name', '').strip()
            last_name = row.get('last_name', '').strip()
            work_email = row.get('work_email', '').strip()
            
            if not first_name or not last_name or not work_email:
                errors.append(f"Row {row_num}: Missing required fields (first_name, last_name, work_email)")
                continue
                
            try:
                validate_email(work_email)
            except ValidationError:
                errors.append(f"Row {row_num}: Invalid email format ({work_email})")
                continue
                
            hire_date_str = row.get('hire_date', '').strip()
            try:
                hire_date = datetime.datetime.strptime(hire_date_str, '%Y-%m-%d').date() if hire_date_str else datetime.date.today()
            except ValueError:
                errors.append(f"Row {row_num}: Invalid hire_date format ({hire_date_str}). Expected YYYY-MM-DD")
                continue

            company_name = row.get('company', '').strip().lower()
            company = companies.get(company_name)
            if not company:
                errors.append(f"Row {row_num}: Company '{company_name}' not found")
                continue

            department_name = row.get('department', '').strip().lower()
            department = departments.get(department_name) if getattr(row, 'get', lambda x, y: '')('department', '') else None

            branch_name = row.get('branch', '').strip().lower()
            branch = branches.get(branch_name) if getattr(row, 'get', lambda x, y: '')('branch', '') else None

            position_name = row.get('position', '').strip().lower()
            position = positions.get(position_name) if getattr(row, 'get', lambda x, y: '')('position', '') else None
            
            emp = Employee(
                tenant=tenant,
                company=company,
                department=department,
                branch=branch,
                position=position,
                first_name=first_name,
                last_name=last_name,
                work_email=work_email,
                mobile_phone=row.get('mobile_phone', '').strip(),
                hire_date=hire_date,
                created_by=user,
                source='bulk_import'
            )
            employees_to_create.append(emp)
        except Exception as e:
            errors.append(f"Row {row_num}: Unexpected error - {str(e)}")
            
    if errors:
        return {'success': False, 'errors': errors}
        
    if not employees_to_create:
        return {'success': False, 'errors': ['The CSV file was empty or contained no valid data rows.']}
        
    try:
        with transaction.atomic():
            # Get last employee number to manually sequence them
            last = Employee.objects.filter(
                tenant=tenant,
                employee_number__startswith='EMP-'
            ).order_by('-employee_number').first()
            
            start_num = 1
            if last and last.employee_number:
                try:
                    start_num = int(last.employee_number.split('-')[1]) + 1
                except (ValueError, IndexError):
                    pass
            
            for emp in employees_to_create:
                emp.employee_number = f"EMP-{start_num:04d}"
                start_num += 1

            Employee.objects.bulk_create(employees_to_create)
            
        return {'success': True, 'count': len(employees_to_create)}
    except Exception as e:
        return {'success': False, 'errors': [f"Database error during bulk insert: {str(e)}"]}


class ImportEmployeesView(APIView):
    """
    POST /api/v1/import/employees/
    Accepts multipart CSV upload. Creates Employee records via get_or_create.

    Expected CSV columns: first_name, last_name, email, department, job_title, start_date
    Maps to Employee fields: first_name, last_name, work_email, department (name lookup),
                             position (title lookup), hire_date
    """
    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return JsonResponse({'error': 'No file provided. Use field name "file".'}, status=400)
        if not file.name.endswith('.csv'):
            return JsonResponse({'error': 'Only CSV files are accepted.'}, status=400)

        try:
            content = file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(content))
            rows = list(reader)
        except Exception as e:
            return JsonResponse({'error': f'CSV parse error: {e}'}, status=400)

        created = 0
        errors = []
        tenant = getattr(request, 'tenant', None)

        # Pre-fetch lookup dicts to minimise DB hits
        departments = {d.name.lower(): d for d in Department.objects.filter(tenant=tenant)} if tenant else {}
        positions = {p.title.lower(): p for p in Position.objects.filter(tenant=tenant)} if tenant else {}
        companies = {c.name.lower(): c for c in Company.objects.filter(tenant=tenant)} if tenant else {}

        for i, row in enumerate(rows, start=2):
            email = (row.get('email') or '').strip().lower()
            first_name = (row.get('first_name') or '').strip()
            last_name = (row.get('last_name') or '').strip()

            if not email:
                errors.append({'row': i, 'error': 'email required'})
                continue

            try:
                validate_email(email)
            except ValidationError:
                errors.append({'row': i, 'error': f'Invalid email: {email}'})
                continue

            hire_date_str = (row.get('start_date') or '').strip()
            try:
                hire_date = datetime.datetime.strptime(hire_date_str, '%Y-%m-%d').date() if hire_date_str else datetime.date.today()
            except ValueError:
                errors.append({'row': i, 'error': f'Invalid start_date format: {hire_date_str}. Use YYYY-MM-DD'})
                continue

            try:
                fields = {
                    'first_name': first_name,
                    'last_name': last_name,
                    'hire_date': hire_date,
                }
                if tenant:
                    fields['tenant'] = tenant

                # Optional FK lookups
                dept_name = (row.get('department') or '').strip().lower()
                if dept_name and dept_name in departments:
                    fields['department'] = departments[dept_name]

                job_title = (row.get('job_title') or '').strip().lower()
                if job_title and job_title in positions:
                    fields['position'] = positions[job_title]

                company_name = (row.get('company') or '').strip().lower()
                if company_name and company_name in companies:
                    fields['company'] = companies[company_name]

                # company is required on Employee; skip row if not resolved
                if 'company' not in fields:
                    default_company = Company.objects.filter(tenant=tenant).first() if tenant else None
                    if not default_company:
                        errors.append({'row': i, 'error': 'Could not resolve a company for this employee'})
                        continue
                    fields['company'] = default_company

                _, was_created = Employee.objects.get_or_create(
                    work_email=email,
                    tenant=tenant,
                    defaults=fields,
                )
                created += 1
            except Exception as e:
                errors.append({'row': i, 'error': str(e)})

        return JsonResponse(
            {'imported': created, 'errors': errors, 'total_rows': len(rows)},
            status=207 if errors else 201,
        )
