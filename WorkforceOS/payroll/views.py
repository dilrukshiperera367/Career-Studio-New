"""Payroll API views."""

from decimal import Decimal
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import models

from config.base_api import TenantViewSetMixin, AuditMixin
from core_hr.models import Employee
from platform_core.services import emit_timeline_event
from .models import (
    SalaryStructure, EmployeeCompensation, PayrollRun,
    PayrollEntry, LoanRecord, PayrollAuditLog,
    OffCycleCompChange, RetroPayEntry, PayrollAnomaly, PayCompressionAlert,
    CompBenchmarkImport, SalaryProgression, RewardSimulation, BudgetGuardrail,
    VariablePayPlan, VariablePayEntry,
)
from .serializers import (
    SalaryStructureSerializer, EmployeeCompensationSerializer,
    PayrollRunSerializer, PayrollEntrySerializer, LoanRecordSerializer,
)
from .engine import PayrollCalculator
from .calculator import calculate_payroll, apply_calculation_to_run, DeductionResult


class SalaryStructureViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = SalaryStructure.objects.all()
    serializer_class = SalaryStructureSerializer
    filterset_fields = ['status', 'company']


class EmployeeCompensationViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = EmployeeCompensation.objects.select_related('employee', 'salary_structure').all()
    serializer_class = EmployeeCompensationSerializer
    filterset_fields = ['employee', 'is_current']

    @action(detail=False, methods=['post'], url_path='final-settlement')
    def final_settlement(self, request):
        """Calculate final settlement for an exiting employee.

        Body:
          - employee_id (UUID)
          - last_working_date (YYYY-MM-DD, optional, defaults to today)

        Returns a breakdown: pro-rata salary, leave encashment, gratuity,
        outstanding loans, and net payable.
        """
        from .advanced import calculate_final_settlement
        from core_hr.models import Employee as HREmployee
        from leave_attendance.models import LeaveBalance
        from .models import LoanRecord
        from datetime import date as _date

        employee_id = request.data.get('employee_id')
        last_working_str = request.data.get('last_working_date')

        if not employee_id:
            return Response({'error': {'message': 'employee_id is required'}}, status=status.HTTP_400_BAD_REQUEST)

        try:
            employee = HREmployee.objects.get(id=employee_id, tenant_id=request.tenant_id)
        except HREmployee.DoesNotExist:
            return Response({'error': {'message': 'Employee not found'}}, status=status.HTTP_404_NOT_FOUND)

        compensation = EmployeeCompensation.objects.filter(
            tenant_id=request.tenant_id,
            employee=employee,
            is_current=True,
        ).first()

        if not compensation:
            return Response(
                {'error': {'message': 'No active compensation record found for this employee'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        last_working_date = None
        if last_working_str:
            try:
                from datetime import datetime
                last_working_date = datetime.strptime(last_working_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': {'message': 'last_working_date must be YYYY-MM-DD'}},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Fetch leave balances and pending loans
        leave_balances = list(LeaveBalance.objects.filter(
            tenant_id=request.tenant_id,
            employee=employee,
            year=_date.today().year,
        ).select_related('leave_type'))

        pending_loans = list(LoanRecord.objects.filter(
            tenant_id=request.tenant_id,
            employee=employee,
            status__in=['active', 'disbursed'],
        ))

        result = calculate_final_settlement(
            employee_compensation=compensation,
            employee=employee,
            leave_balances=leave_balances,
            pending_loans=pending_loans,
            last_working_date=last_working_date,
        )
        return Response({'data': result})


class PayrollRunViewSet(TenantViewSetMixin, AuditMixin, viewsets.ModelViewSet):
    queryset = PayrollRun.objects.select_related('company').all()
    serializer_class = PayrollRunSerializer
    filterset_fields = ['company', 'period_year', 'period_month', 'status']
    ordering_fields = ['period_year', 'period_month', 'created_at']

    @action(detail=False, methods=['post'], url_path='run')
    def run(self, request):
        """Create a new draft payroll run and return it ready for processing.

        Body:
          - company_id (UUID)
          - period_year (int)
          - period_month (int, 1-12)

        Returns the created PayrollRun. Use POST /payroll/runs/{id}/process/ to calculate.
        """
        company_id = request.data.get('company_id')
        period_year = request.data.get('period_year')
        period_month = request.data.get('period_month')

        if not all([company_id, period_year, period_month]):
            return Response(
                {'error': {'message': 'company_id, period_year, and period_month are required'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            period_year = int(period_year)
            period_month = int(period_month)
        except (ValueError, TypeError):
            return Response(
                {'error': {'message': 'period_year and period_month must be integers'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not (1 <= period_month <= 12):
            return Response(
                {'error': {'message': 'period_month must be between 1 and 12'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing = PayrollRun.objects.filter(
            tenant_id=request.tenant_id,
            company_id=company_id,
            period_year=period_year,
            period_month=period_month,
        ).exclude(status='cancelled').first()

        if existing:
            return Response(
                {'error': {'message': f'A payroll run already exists for this period (status: {existing.status})'}},
                status=status.HTTP_409_CONFLICT,
            )

        run = PayrollRun.objects.create(
            tenant_id=request.tenant_id,
            company_id=company_id,
            period_year=period_year,
            period_month=period_month,
            status='draft',
        )

        return Response(
            {
                'data': PayrollRunSerializer(run).data,
                'meta': {
                    'message': 'Payroll run created in draft status.',
                    'next_step': f'POST /api/v1/payroll/runs/{run.id}/process/ to calculate payroll.',
                },
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Process payroll — calculate all employee entries."""
        run = self.get_object()
        if run.status not in ['draft', 'review']:
            return Response({'error': {'message': f'Cannot process payroll in {run.status} status'}}, status=400)

        run.status = 'processing'
        run.processed_by = request.user
        run.save()

        # Get active employees for this company
        employees = Employee.objects.filter(
            tenant_id=request.tenant_id,
            company=run.company,
            status__in=['active', 'probation'],
        )

        calculator = PayrollCalculator(
            tenant_id=request.tenant_id,
            company_id=run.company_id,
            year=run.period_year,
            month=run.period_month,
        )

        # Get attendance summary
        from leave_attendance.models import AttendanceRecord
        attendance_summary = {}
        attendance_qs = AttendanceRecord.objects.filter(
            tenant_id=request.tenant_id,
            date__year=run.period_year,
            date__month=run.period_month,
        ).values('employee_id').annotate(
            days_present=models.Count('id', filter=models.Q(status='present')),
            days_absent=models.Count('id', filter=models.Q(status='absent')),
            ot_hours=models.Sum('overtime_hours'),
        )
        for row in attendance_qs:
            attendance_summary[row['employee_id']] = row

        total_gross = total_deductions = total_net = total_employer = 0

        for employee in employees:
            att_data = attendance_summary.get(employee.id, {})
            result = calculator.calculate_employee(employee, att_data)

            if not result:
                # Fallback: use the standalone calculator when the engine cannot
                # locate a compensation record (e.g. recently-hired employees whose
                # EmployeeCompensation record has not yet been confirmed as current).
                from datetime import date as _date
                import calendar as _cal
                period_start = _date(run.period_year, run.period_month, 1)
                last_day = _cal.monthrange(run.period_year, run.period_month)[1]
                period_end = _date(run.period_year, run.period_month, last_day)

                # Collect active loan deductions for this employee
                loan_deductions_calc = []
                for loan in LoanRecord.objects.filter(
                    tenant_id=request.tenant_id,
                    employee=employee,
                    status='active',
                ):
                    loan_deductions_calc.append(DeductionResult(
                        name=f'Loan: {loan.loan_type}',
                        amount=loan.installment_amount,
                        is_statutory=False,
                    ))

                calc_result = calculate_payroll(
                    employee=employee,
                    period_start=period_start,
                    period_end=period_end,
                    extra_allowances=Decimal('0'),
                    voluntary_deductions=loan_deductions_calc,
                )

                if calc_result.gross_pay <= 0:
                    # Truly no salary data — skip
                    continue

                # Build a result dict compatible with the entry creation below
                result = {
                    'basic_salary': calc_result.gross_pay,
                    'earnings': [],
                    'total_earnings': calc_result.gross_pay,
                    'deductions': [
                        {'component': d.name, 'amount': float(d.amount)}
                        for d in calc_result.deductions
                    ],
                    'total_deductions': float(calc_result.total_deductions),
                    'statutory': {
                        'epf_employee': float(calc_result.epf_employee),
                        'epf_employer': float(calc_result.epf_employer),
                        'etf_employer': float(calc_result.etf_employer),
                        'apit': float(calc_result.apit),
                    },
                    'ot_hours': 0,
                    'ot_amount': 0,
                    'days_worked': att_data.get('days_present', 0),
                    'days_absent': att_data.get('days_absent', 0),
                    'loan_deductions': [
                        {'loan_type': d.name, 'amount': float(d.amount)}
                        for d in loan_deductions_calc
                    ],
                    'gross_salary': float(calc_result.gross_pay),
                    'net_salary': float(calc_result.net_pay),
                    'employer_total_cost': float(
                        calc_result.gross_pay
                        + calc_result.epf_employer
                        + calc_result.etf_employer
                    ),
                }

            # Delete existing entry if re-processing
            PayrollEntry.objects.filter(payroll_run=run, employee=employee).delete()

            entry = PayrollEntry.objects.create(
                tenant_id=request.tenant_id,
                payroll_run=run,
                employee=employee,
                basic_salary=result['basic_salary'],
                earnings_json=result['earnings'],
                total_earnings=result['total_earnings'],
                deductions_json=result['deductions'],
                total_deductions=result['total_deductions'],
                epf_employee=result['statutory'].get('epf_employee', 0),
                epf_employer=result['statutory'].get('epf_employer', 0),
                etf_employer=result['statutory'].get('etf_employer', 0),
                apit=result['statutory'].get('apit', 0),
                statutory_json=result['statutory'],
                ot_hours=result.get('ot_hours', 0),
                ot_amount=result.get('ot_amount', 0),
                days_worked=result.get('days_worked', 0),
                days_absent=result.get('days_absent', 0),
                loan_deductions=result.get('loan_deductions', []),
                gross_salary=result['gross_salary'],
                net_salary=result['net_salary'],
                employer_total_cost=result['employer_total_cost'],
                bank_details=employee.bank_details,
            )

            total_gross += result['gross_salary']
            total_deductions += result['total_deductions']
            total_net += result['net_salary']
            total_employer += result['employer_total_cost']

        # Update run totals
        run.status = 'review'
        run.employee_count = employees.count()
        run.total_gross = total_gross
        run.total_deductions = total_deductions
        run.total_net = total_net
        run.total_employer_cost = total_employer
        run.save()

        # Audit
        PayrollAuditLog.objects.create(
            tenant_id=request.tenant_id,
            payroll_run=run,
            action='processed',
            actor=request.user,
            details={'employee_count': run.employee_count, 'total_net': float(total_net)},
        )

        return Response({
            'data': PayrollRunSerializer(run).data,
            'meta': {'message': f'Processed {run.employee_count} employees'}
        })

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        run = self.get_object()
        if run.status != 'review':
            return Response({'error': {'message': 'Can only approve payroll in review status'}}, status=400)
        run.status = 'approved'
        run.approved_by = request.user
        run.save()
        PayrollAuditLog.objects.create(
            tenant_id=request.tenant_id, payroll_run=run,
            action='approved', actor=request.user,
        )
        return Response({'data': PayrollRunSerializer(run).data, 'meta': {'message': 'Payroll approved'}})

    @action(detail=True, methods=['post'])
    def finalize(self, request, pk=None):
        run = self.get_object()
        if run.status != 'approved':
            return Response({'error': {'message': 'Must be approved before finalizing'}}, status=400)

        run.status = 'finalized'
        run.finalized_at = timezone.now()
        run.save()

        # Update loan balances
        for entry in run.entries.all():
            for ld in entry.loan_deductions:
                try:
                    loan = LoanRecord.objects.get(id=ld['loan_id'])
                    loan.outstanding_balance -= ld['amount']
                    loan.installments_paid += 1
                    if loan.outstanding_balance <= 0:
                        loan.status = 'completed'
                        loan.outstanding_balance = 0
                    loan.save()
                except LoanRecord.DoesNotExist:
                    pass

            # Timeline event per employee
            emit_timeline_event(
                tenant_id=request.tenant_id,
                employee=entry.employee,
                event_type='payroll.payslip_generated',
                category='payroll',
                title=f'Payslip generated for {run.period_year}-{run.period_month:02d}',
                actor=request.user,
                source_object_type='PayrollEntry',
                source_object_id=entry.id,
            )

        PayrollAuditLog.objects.create(
            tenant_id=request.tenant_id, payroll_run=run,
            action='finalized', actor=request.user,
        )

        # Audit log (#164) — structured AuditLog entry for payroll finalization
        try:
            from platform_core.models import AuditLog
            entry_count = run.entries.count()
            AuditLog.objects.create(
                tenant_id=request.tenant_id,
                user=request.user,
                action='payroll_run_finalized',
                entity_type='PayrollRun',
                entity_id=run.id,
                changes={
                    'period': f'{run.period_year}-{run.period_month:02d}',
                    'total_entries': entry_count,
                    'total_gross': str(run.total_gross),
                },
            )
        except Exception:
            pass

        return Response({'data': PayrollRunSerializer(run).data, 'meta': {'message': 'Payroll finalized'}})

    @action(detail=True, methods=['get'])
    def entries(self, request, pk=None):
        run = self.get_object()
        entries = run.entries.select_related('employee').all()
        return Response({'data': PayrollEntrySerializer(entries, many=True).data})

    @action(detail=True, methods=['get'], url_path='bank-file')
    def bank_file(self, request, pk=None):
        """Download bank transfer CSV."""
        from django.http import HttpResponse
        from .reports import generate_bank_file
        run = self.get_object()
        if run.status not in ['approved', 'finalized']:
            return Response({'error': {'message': 'Payroll must be approved or finalized'}}, status=400)
        csv_content = generate_bank_file(run)
        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="bank_transfer_{run.period_year}_{run.period_month:02d}.csv"'
        return response

    @action(detail=True, methods=['get'], url_path='epf-return')
    def epf_return(self, request, pk=None):
        """Download EPF Return (Form C) CSV."""
        from django.http import HttpResponse
        from .reports import generate_epf_return
        run = self.get_object()
        csv_content = generate_epf_return(run)
        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="epf_return_{run.period_year}_{run.period_month:02d}.csv"'
        return response

    @action(detail=True, methods=['get'], url_path='etf-return')
    def etf_return(self, request, pk=None):
        """Download ETF Return CSV."""
        from django.http import HttpResponse
        from .reports import generate_etf_return
        run = self.get_object()
        csv_content = generate_etf_return(run)
        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="etf_return_{run.period_year}_{run.period_month:02d}.csv"'
        return response

    @action(detail=True, methods=['get'], url_path='apit-summary')
    def apit_summary(self, request, pk=None):
        """Download APIT summary CSV."""
        from django.http import HttpResponse
        from .reports import generate_apit_summary
        run = self.get_object()
        csv_content = generate_apit_summary(run)
        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="apit_summary_{run.period_year}_{run.period_month:02d}.csv"'
        return response

    @action(detail=True, methods=['post'], url_path='dispatch-payslips')
    def dispatch_payslips(self, request, pk=None):
        """Queue a Celery task to email payslips for every employee in this run.
        The run must be in 'finalized' status.
        """
        from .tasks import dispatch_payslips as dispatch_task
        run = self.get_object()
        if run.status != 'finalized':
            return Response(
                {'error': {'message': f'Payroll run must be finalized before dispatching payslips (current status: {run.status})'}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        task = dispatch_task.delay(str(run.id))
        return Response({
            'meta': {
                'message': 'Payslip dispatch queued',
                'task_id': task.id,
                'run_id': str(run.id),
                'period': f'{run.period_year}-{run.period_month:02d}',
            }
        })

    @action(detail=True, methods=['post'], url_path='process-arrears')
    def process_arrears(self, request, pk=None):
        """Queue arrears processing for this payroll run.
        Identifies backdated salary changes and adds arrears lines to existing entries.
        """
        from .tasks import arrears_processing
        run = self.get_object()
        if run.status not in ['draft', 'review', 'processing']:
            return Response(
                {'error': {'message': f'Arrears can only be processed on active runs (current status: {run.status})'}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        task = arrears_processing.delay(str(run.id))
        return Response({
            'meta': {
                'message': 'Arrears processing queued',
                'task_id': task.id,
                'run_id': str(run.id),
            }
        })


class PayrollEntryViewSet(TenantViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = PayrollEntry.objects.select_related('employee', 'payroll_run').all()
    serializer_class = PayrollEntrySerializer
    filterset_fields = ['payroll_run', 'employee']

    @action(detail=True, methods=['get'])
    def payslip(self, request, pk=None):
        """Generate and return payslip PDF."""
        from django.http import HttpResponse
        from .payslip import generate_payslip_pdf
        entry = self.get_object()
        pdf_bytes = generate_payslip_pdf(entry)
        content_type = 'application/pdf' if isinstance(pdf_bytes, bytes) and pdf_bytes[:4] == b'%PDF' else 'text/html'
        response = HttpResponse(pdf_bytes, content_type=content_type)
        filename = f"payslip_{entry.employee.employee_number}_{entry.payroll_run.period_year}_{entry.payroll_run.period_month:02d}"
        ext = 'pdf' if content_type == 'application/pdf' else 'html'
        response['Content-Disposition'] = f'attachment; filename="{filename}.{ext}"'
        return response

    @action(detail=True, methods=['get'], url_path='payslip-html')
    def payslip_html(self, request, pk=None):
        """Return payslip as HTML (for preview)."""
        from django.http import HttpResponse
        from .payslip import generate_payslip_html
        entry = self.get_object()
        html = generate_payslip_html(entry)
        return HttpResponse(html, content_type='text/html')


class LoanRecordViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = LoanRecord.objects.select_related('employee').all()
    serializer_class = LoanRecordSerializer
    filterset_fields = ['employee', 'status', 'loan_type']


# ============ STANDALONE API VIEWS ============

class PayslipPDFView(APIView):
    """
    GET /api/v1/payroll/entries/{pk}/payslip/
    Generate and return payslip as PDF (or JSON representation if no PDF library).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        import datetime
        import calendar as _cal

        try:
            entry = PayrollEntry.objects.select_related(
                'employee', 'payroll_run'
            ).get(id=pk, payroll_run__tenant_id=request.tenant_id)
        except PayrollEntry.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        run = entry.payroll_run
        period_start = datetime.date(run.period_year, run.period_month, 1)
        last_day = _cal.monthrange(run.period_year, run.period_month)[1]
        period_end = datetime.date(run.period_year, run.period_month, last_day)

        # Compute total loan deductions from JSON list
        total_loan = sum(
            Decimal(str(ld.get('amount', 0)))
            for ld in (entry.loan_deductions or [])
        )

        # Try to generate actual PDF with reportlab if available
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            import io

            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=A4)
            width, height = A4

            # Header
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, height - 60, "PAYSLIP")
            c.setFont("Helvetica", 10)
            c.drawString(50, height - 80, f"Period: {period_start} \u2013 {period_end}")
            c.drawString(50, height - 95, f"Employee: {entry.employee.first_name} {entry.employee.last_name}")
            c.drawString(50, height - 110, f"Employee ID: {entry.employee.employee_number}")

            # Earnings
            y = height - 150
            c.setFont("Helvetica-Bold", 11)
            c.drawString(50, y, "EARNINGS")
            y -= 20
            c.setFont("Helvetica", 10)
            c.drawString(60, y, f"Basic Salary: LKR {entry.basic_salary:,.2f}")
            y -= 15
            c.drawString(60, y, f"Allowances: LKR {(entry.gross_salary - entry.basic_salary):,.2f}")
            y -= 15
            c.setFont("Helvetica-Bold", 10)
            c.drawString(60, y, f"Gross Salary: LKR {entry.gross_salary:,.2f}")

            # Deductions
            y -= 30
            c.setFont("Helvetica-Bold", 11)
            c.drawString(50, y, "DEDUCTIONS")
            y -= 20
            c.setFont("Helvetica", 10)
            c.drawString(60, y, f"EPF (Employee 8%): LKR {entry.epf_employee:,.2f}")
            y -= 15
            c.drawString(60, y, f"APIT Tax: LKR {entry.apit:,.2f}")
            if total_loan > 0:
                y -= 15
                c.drawString(60, y, f"Loan Deduction: LKR {total_loan:,.2f}")

            # Net Pay
            y -= 30
            c.setFont("Helvetica-Bold", 13)
            c.drawString(50, y, f"NET PAY: LKR {entry.net_salary:,.2f}")

            # Footer
            c.setFont("Helvetica-Oblique", 8)
            c.drawString(50, 50, "This is a computer-generated payslip and does not require a signature.")

            c.save()
            buffer.seek(0)

            from django.http import HttpResponse as DjangoHttpResponse
            response = DjangoHttpResponse(buffer.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = (
                f'attachment; filename="payslip_{entry.employee.employee_number}'
                f'_{run.period_year}_{run.period_month:02d}.pdf"'
            )
            return response

        except ImportError:
            # Fallback: return JSON representation
            return Response({
                'employee': f"{entry.employee.first_name} {entry.employee.last_name}",
                'employee_id': entry.employee.employee_number,
                'period': f"{period_start} \u2013 {period_end}",
                'basic_salary': str(entry.basic_salary),
                'gross_salary': str(entry.gross_salary),
                'epf_employee': str(entry.epf_employee),
                'apit': str(entry.apit),
                'loan_deductions': str(total_loan),
                'net_salary': str(entry.net_salary),
                'note': 'Install reportlab for PDF generation: pip install reportlab',
            })


class BankFileView(APIView):
    """
    GET /api/v1/payroll/runs/{pk}/bank-file/
    Generate bank transfer file (CSV format) for salary disbursement.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        import csv
        import io
        import datetime
        import calendar as _cal

        try:
            run = PayrollRun.objects.get(id=pk, tenant_id=request.tenant_id)
        except PayrollRun.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        if run.status != 'finalized':
            return Response(
                {'error': 'Payroll run must be finalized before generating bank file'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        entries = PayrollEntry.objects.filter(payroll_run=run).select_related('employee')

        last_day = _cal.monthrange(run.period_year, run.period_month)[1]
        payment_date = datetime.date(run.period_year, run.period_month, last_day)
        period_start = datetime.date(run.period_year, run.period_month, 1)

        output = io.StringIO()
        writer = csv.writer(output)

        # Header row
        writer.writerow([
            'EMPLOYEE_ID', 'EMPLOYEE_NAME', 'BANK_CODE', 'BRANCH_CODE',
            'ACCOUNT_NUMBER', 'AMOUNT', 'PAYMENT_REFERENCE', 'PAYMENT_DATE',
        ])

        for entry in entries:
            emp = entry.employee
            bank = emp.bank_details if isinstance(emp.bank_details, dict) else {}
            writer.writerow([
                emp.employee_number,
                f"{emp.first_name} {emp.last_name}",
                bank.get('bank_code', ''),
                bank.get('branch_code', ''),
                bank.get('account_number', bank.get('bank_account_number', '')),
                f"{entry.net_salary:.2f}",
                f"SAL-{period_start}-{emp.employee_number}",
                payment_date,
            ])

        from django.http import HttpResponse as DjangoHttpResponse
        response = DjangoHttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = (
            f'attachment; filename="bank_transfer_{run.period_year}_{run.period_month:02d}.csv"'
        )
        return response


class EPFETFReportView(APIView):
    """
    GET /api/v1/payroll/runs/{pk}/epf-etf-report/
    Generate combined EPF/ETF return report (JSON or CSV).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        import csv
        import io
        import datetime
        import calendar as _cal

        try:
            run = PayrollRun.objects.get(id=pk, tenant_id=request.tenant_id)
        except PayrollRun.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        entries = list(
            PayrollEntry.objects.filter(payroll_run=run).select_related('employee')
        )

        period_start = datetime.date(run.period_year, run.period_month, 1)
        last_day = _cal.monthrange(run.period_year, run.period_month)[1]
        period_end = datetime.date(run.period_year, run.period_month, last_day)

        total_epf_employee = sum(e.epf_employee for e in entries)
        total_epf_employer = sum(e.epf_employer for e in entries)
        total_etf = sum(e.etf_employer for e in entries)

        fmt = request.query_params.get('format', 'json')
        if fmt == 'csv':
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                'EMPLOYEE_ID', 'NAME', 'NIC', 'BASIC_SALARY',
                'EPF_EMPLOYEE_8%', 'EPF_EMPLOYER_12%', 'TOTAL_EPF', 'ETF_3%',
            ])
            for e in entries:
                emp = e.employee
                writer.writerow([
                    emp.employee_number,
                    f"{emp.first_name} {emp.last_name}",
                    getattr(emp, 'nic_number', ''),
                    f"{e.basic_salary:.2f}",
                    f"{e.epf_employee:.2f}",
                    f"{e.epf_employer:.2f}",
                    f"{e.epf_employee + e.epf_employer:.2f}",
                    f"{e.etf_employer:.2f}",
                ])
            writer.writerow([])
            writer.writerow([
                'TOTALS', '', '', '',
                f"{total_epf_employee:.2f}",
                f"{total_epf_employer:.2f}",
                f"{total_epf_employee + total_epf_employer:.2f}",
                f"{total_etf:.2f}",
            ])
            from django.http import HttpResponse as DjangoHttpResponse
            resp = DjangoHttpResponse(output.getvalue(), content_type='text/csv')
            resp['Content-Disposition'] = (
                f'attachment; filename="epf_etf_{run.period_year}_{run.period_month:02d}.csv"'
            )
            return resp

        return Response({
            'period': {'start': str(period_start), 'end': str(period_end)},
            'summary': {
                'total_employees': len(entries),
                'total_epf_employee': str(total_epf_employee),
                'total_epf_employer': str(total_epf_employer),
                'total_epf_combined': str(total_epf_employee + total_epf_employer),
                'total_etf': str(total_etf),
            },
            'entries': [{
                'employee_id': e.employee.employee_number,
                'name': f"{e.employee.first_name} {e.employee.last_name}",
                'nic': getattr(e.employee, 'nic_number', ''),
                'basic_salary': str(e.basic_salary),
                'epf_employee': str(e.epf_employee),
                'epf_employer': str(e.epf_employer),
                'etf': str(e.etf_employer),
            } for e in entries],
        })


class APYTCalculationView(APIView):
    """
    POST /api/v1/payroll/apit-calculate/
    Calculate APIT (Annual Personal Income Tax) for given monthly salary.
    Uses Sri Lanka IRD brackets for 2025/2026.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        monthly_salary = request.data.get('monthly_salary')
        if not monthly_salary:
            return Response({'error': 'monthly_salary required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            monthly = Decimal(str(monthly_salary))
        except Exception:
            return Response({'error': 'Invalid salary value'}, status=status.HTTP_400_BAD_REQUEST)

        annual = monthly * 12

        # Sri Lanka APIT brackets 2025/2026 (IRD)
        # Personal relief: LKR 1,200,000 per annum
        PERSONAL_RELIEF = Decimal('1200000')
        taxable_income = max(Decimal('0'), annual - PERSONAL_RELIEF)

        BRACKETS = [
            (Decimal('3000000'), Decimal('0.06')),   # First 3M @ 6%
            (Decimal('3000000'), Decimal('0.12')),   # Next 3M @ 12%
            (Decimal('3000000'), Decimal('0.18')),   # Next 3M @ 18%
            (Decimal('3000000'), Decimal('0.24')),   # Next 3M @ 24%
            (None,               Decimal('0.36')),   # Above 12M @ 36%
        ]

        annual_tax = Decimal('0')
        remaining = taxable_income
        breakdown = []

        for bracket_size, rate in BRACKETS:
            if remaining <= 0:
                break
            if bracket_size is None:
                taxable_in_bracket = remaining
            else:
                taxable_in_bracket = min(remaining, bracket_size)

            tax = (taxable_in_bracket * rate).quantize(Decimal('0.01'))
            annual_tax += tax
            breakdown.append({
                'bracket': f"Up to LKR {bracket_size:,}" if bracket_size else "Above previous bracket",
                'rate': f"{rate * 100:.0f}%",
                'taxable': str(taxable_in_bracket),
                'tax': str(tax),
            })
            remaining -= taxable_in_bracket

        monthly_apit = (annual_tax / 12).quantize(Decimal('0.01'))

        return Response({
            'inputs': {
                'monthly_salary': str(monthly),
                'annual_salary': str(annual),
                'personal_relief': str(PERSONAL_RELIEF),
                'taxable_income': str(taxable_income),
            },
            'results': {
                'annual_tax': str(annual_tax),
                'monthly_apit': str(monthly_apit),
                'effective_rate': (
                    f"{(annual_tax / annual * 100).quantize(Decimal('0.01'))}%"
                    if annual > 0 else '0%'
                ),
            },
            'breakdown': breakdown,
        })


# ============ FEATURE 5: PAYROLL & COMP PLANNING VIEWSETS ============

from rest_framework import serializers as drf_serializers


class _OffCycleCompChangeSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = OffCycleCompChange
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class OffCycleCompChangeViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = OffCycleCompChange.objects.all()
    serializer_class = _OffCycleCompChangeSerializer
    filterset_fields = ['employee', 'change_type', 'status']


class _RetroPayEntrySerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = RetroPayEntry
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')


class RetroPayEntryViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = RetroPayEntry.objects.all()
    serializer_class = _RetroPayEntrySerializer
    filterset_fields = ['employee', 'payroll_run', 'is_applied']


class _PayrollAnomalySerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = PayrollAnomaly
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')


class PayrollAnomalyViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = PayrollAnomaly.objects.all()
    serializer_class = _PayrollAnomalySerializer
    filterset_fields = ['payroll_run', 'employee', 'anomaly_type', 'severity', 'is_resolved']


class _PayCompressionAlertSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = PayCompressionAlert
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'detected_at')


class PayCompressionAlertViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = PayCompressionAlert.objects.all()
    serializer_class = _PayCompressionAlertSerializer
    filterset_fields = ['employee', 'manager', 'status']


class _CompBenchmarkImportSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = CompBenchmarkImport
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'imported_at')


class CompBenchmarkImportViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = CompBenchmarkImport.objects.all()
    serializer_class = _CompBenchmarkImportSerializer
    filterset_fields = ['source', 'survey_year', 'job_family', 'currency']


class _SalaryProgressionSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = SalaryProgression
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')


class SalaryProgressionViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = SalaryProgression.objects.all()
    serializer_class = _SalaryProgressionSerializer
    filterset_fields = ['employee', 'currency']


class _RewardSimulationSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = RewardSimulation
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class RewardSimulationViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = RewardSimulation.objects.all()
    serializer_class = _RewardSimulationSerializer
    filterset_fields = ['is_finalized', 'created_by']


class _BudgetGuardrailSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = BudgetGuardrail
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')


class BudgetGuardrailViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = BudgetGuardrail.objects.all()
    serializer_class = _BudgetGuardrailSerializer
    filterset_fields = ['cycle_year', 'budget_type', 'department', 'is_active']


class _VariablePayPlanSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = VariablePayPlan
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class VariablePayPlanViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = VariablePayPlan.objects.all()
    serializer_class = _VariablePayPlanSerializer
    filterset_fields = ['plan_type', 'plan_year', 'is_active']


class _VariablePayEntrySerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = VariablePayEntry
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')


class VariablePayEntryViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = VariablePayEntry.objects.all()
    serializer_class = _VariablePayEntrySerializer
    filterset_fields = ['plan', 'employee', 'status', 'paid_in_run']

