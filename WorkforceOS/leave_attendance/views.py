"""Leave & Attendance API views."""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db import models
from datetime import date, timedelta

from config.base_api import TenantViewSetMixin, AuditMixin
from platform_core.services import emit_timeline_event, send_notification
from .models import (
    LeaveType, LeaveBalance, LeaveRequest, HolidayCalendar, Holiday,
    ShiftTemplate, ShiftAssignment, AttendanceRecord, OvertimeRecord,
    Roster, RosterSlot, ShiftSwapRequest, ShiftBid, ShiftBidApplication, GeofenceZone,
)
from .serializers import (
    LeaveTypeSerializer, LeaveBalanceSerializer, LeaveRequestSerializer,
    HolidayCalendarSerializer, HolidaySerializer, ShiftTemplateSerializer,
    ShiftAssignmentSerializer, AttendanceRecordSerializer, ClockInSerializer,
    ClockOutSerializer, OvertimeRecordSerializer,
)


class LeaveTypeViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    filterset_fields = ['status', 'paid']


class LeaveBalanceViewSet(TenantViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = LeaveBalance.objects.select_related('leave_type').all()
    serializer_class = LeaveBalanceSerializer
    filterset_fields = ['employee', 'year']

    @action(detail=False, methods=['get'], url_path='my')
    def my_balances(self, request):
        """Get current user's leave balances."""
        employee = getattr(request.user, 'employee_profile', None)
        if not employee:
            return Response({'data': []})
        balances = self.get_queryset().filter(
            employee=employee, year=date.today().year
        )
        return Response({'data': LeaveBalanceSerializer(balances, many=True).data})


class LeaveRequestViewSet(TenantViewSetMixin, AuditMixin, viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.select_related('employee', 'leave_type', 'approved_by').all()
    serializer_class = LeaveRequestSerializer
    filterset_fields = ['employee', 'leave_type', 'status']
    ordering_fields = ['start_date', 'created_at']

    def perform_create(self, serializer):
        employee = serializer.validated_data.get('employee')
        leave_type = serializer.validated_data.get('leave_type')
        start_date = serializer.validated_data.get('start_date')
        end_date = serializer.validated_data.get('end_date')
        days = serializer.validated_data.get('days')

        # Validate: balance check
        balance = LeaveBalance.objects.filter(
            tenant_id=self.request.tenant_id,
            employee=employee,
            leave_type=leave_type,
            year=start_date.year,
        ).first()

        if balance and leave_type.paid and balance.remaining < days:
            return Response(
                {'error': {'code': 'INSUFFICIENT_BALANCE', 'message': f'Only {balance.remaining} days remaining'}},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate: overlap check
        overlap = LeaveRequest.objects.filter(
            tenant_id=self.request.tenant_id,
            employee=employee,
            status__in=['pending', 'approved'],
            start_date__lte=end_date,
            end_date__gte=start_date,
        ).exists()

        if overlap:
            return Response(
                {'error': {'code': 'OVERLAPPING_LEAVE', 'message': 'Overlapping leave request exists'}},
                status=status.HTTP_400_BAD_REQUEST
            )

        leave_request = serializer.save(tenant_id=self.request.tenant_id)

        # Update pending balance
        if balance:
            balance.pending += days
            balance.save()

        # Notify manager
        if employee.manager and employee.manager.user:
            send_notification(
                tenant_id=self.request.tenant_id,
                recipient=employee.manager.user,
                title=f'Leave request from {employee.full_name}',
                body=f'{leave_type.name}: {start_date} to {end_date} ({days} days)',
                type='action',
                action_url=f'/leave/requests/{leave_request.id}',
            )

        emit_timeline_event(
            tenant_id=self.request.tenant_id,
            employee=employee,
            event_type='leave.requested',
            category='leave',
            title=f'{employee.full_name} requested {leave_type.name} ({days} days)',
            actor=self.request.user,
            source_object_type='LeaveRequest',
            source_object_id=leave_request.id,
        )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        leave_request = self.get_object()
        if leave_request.status != 'pending':
            return Response({'error': {'message': 'Can only approve pending requests'}}, status=400)

        leave_request.status = 'approved'
        leave_request.approved_by = request.user
        leave_request.approved_at = timezone.now()
        leave_request.save()

        # Update balance: move from pending to taken
        balance = LeaveBalance.objects.filter(
            tenant_id=request.tenant_id,
            employee=leave_request.employee,
            leave_type=leave_request.leave_type,
            year=leave_request.start_date.year,
        ).first()
        if balance:
            balance.pending -= leave_request.days
            balance.taken += leave_request.days
            balance.save()

        # Notify employee
        if leave_request.employee.user:
            send_notification(
                tenant_id=request.tenant_id,
                recipient=leave_request.employee.user,
                title='Leave request approved ✅',
                body=f'Your {leave_request.leave_type.name} from {leave_request.start_date} to {leave_request.end_date} has been approved.',
                type='success',
            )

        emit_timeline_event(
            tenant_id=request.tenant_id,
            employee=leave_request.employee,
            event_type='leave.approved',
            category='leave',
            title=f'Leave approved: {leave_request.leave_type.name}',
            actor=request.user,
            source_object_type='LeaveRequest',
            source_object_id=leave_request.id,
        )

        return Response({'data': LeaveRequestSerializer(leave_request).data, 'meta': {'message': 'Leave approved'}})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        leave_request = self.get_object()
        if leave_request.status != 'pending':
            return Response({'error': {'message': 'Can only reject pending requests'}}, status=400)

        leave_request.status = 'rejected'
        leave_request.approved_by = request.user
        leave_request.approved_at = timezone.now()
        leave_request.rejection_reason = request.data.get('reason', '')
        leave_request.save()

        # Restore balance
        balance = LeaveBalance.objects.filter(
            tenant_id=request.tenant_id,
            employee=leave_request.employee,
            leave_type=leave_request.leave_type,
            year=leave_request.start_date.year,
        ).first()
        if balance:
            balance.pending -= leave_request.days
            balance.save()

        emit_timeline_event(
            tenant_id=request.tenant_id,
            employee=leave_request.employee,
            event_type='leave.rejected',
            category='leave',
            title=f'Leave rejected: {leave_request.leave_type.name}',
            actor=request.user,
            source_object_type='LeaveRequest',
            source_object_id=leave_request.id,
        )

        return Response({'data': LeaveRequestSerializer(leave_request).data, 'meta': {'message': 'Leave rejected'}})

    @action(detail=False, methods=['get'])
    def calendar(self, request):
        """Team leave calendar for a date range."""
        start = request.query_params.get('start', date.today().replace(day=1).isoformat())
        end = request.query_params.get('end', (date.today().replace(day=28) + timedelta(days=4)).replace(day=1).isoformat())
        leaves = LeaveRequest.objects.filter(
            tenant_id=request.tenant_id,
            status='approved',
            start_date__lte=end,
            end_date__gte=start,
        ).select_related('employee', 'leave_type')
        return Response({'data': LeaveRequestSerializer(leaves, many=True).data})


class HolidayViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = HolidayCalendar.objects.prefetch_related('holidays').all()
    serializer_class = HolidayCalendarSerializer
    filterset_fields = ['year', 'country']

    @action(detail=True, methods=['post'], url_path='holidays')
    def add_holiday(self, request, pk=None):
        calendar = self.get_object()
        serializer = HolidaySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(calendar=calendar)
        return Response({'data': serializer.data}, status=status.HTTP_201_CREATED)


class ShiftTemplateViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = ShiftTemplate.objects.all()
    serializer_class = ShiftTemplateSerializer
    filterset_fields = ['status']


class AttendanceViewSet(TenantViewSetMixin, AuditMixin, viewsets.ModelViewSet):
    queryset = AttendanceRecord.objects.select_related('employee', 'shift').all()
    serializer_class = AttendanceRecordSerializer
    filterset_fields = ['employee', 'date', 'status']
    ordering_fields = ['date']

    @action(detail=False, methods=['post'], url_path='clock-in')
    def clock_in(self, request):
        """Clock in for the current user."""
        serializer = ClockInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        employee = getattr(request.user, 'employee_profile', None)
        if not employee:
            return Response({'error': {'message': 'No employee profile linked'}}, status=400)

        today = date.today()

        # Check if already clocked in
        record = AttendanceRecord.objects.filter(
            tenant_id=request.tenant_id, employee=employee, date=today
        ).first()

        if record and record.clock_in:
            return Response({'error': {'message': 'Already clocked in today'}}, status=400)

        now = timezone.now()
        data = serializer.validated_data

        if not record:
            # Get assigned shift
            shift_assignment = ShiftAssignment.objects.filter(
                tenant_id=request.tenant_id, employee=employee, date=today
            ).select_related('shift').first()

            shift = shift_assignment.shift if shift_assignment else None

            # Calculate late minutes
            late_minutes = 0
            if shift:
                from datetime import datetime, time as dt_time
                shift_start = timezone.make_aware(
                    datetime.combine(today, shift.start_time)
                )
                grace_end = shift_start + timedelta(minutes=shift.grace_minutes)
                if now > grace_end:
                    late_minutes = int((now - shift_start).total_seconds() / 60)

            record = AttendanceRecord.objects.create(
                tenant_id=request.tenant_id,
                employee=employee,
                date=today,
                shift=shift,
                clock_in=now,
                clock_in_source=data.get('source', 'web'),
                clock_in_location=data.get('location'),
                clock_in_photo_url=data.get('photo_url', ''),
                late_minutes=late_minutes,
                status='present',
            )
        else:
            record.clock_in = now
            record.clock_in_source = data.get('source', 'web')
            record.clock_in_location = data.get('location')
            record.save()

        return Response({
            'data': AttendanceRecordSerializer(record).data,
            'meta': {'message': 'Clocked in successfully'}
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='clock-out')
    def clock_out(self, request):
        """Clock out for the current user."""
        serializer = ClockOutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        employee = getattr(request.user, 'employee_profile', None)
        if not employee:
            return Response({'error': {'message': 'No employee profile linked'}}, status=400)

        today = date.today()
        record = AttendanceRecord.objects.filter(
            tenant_id=request.tenant_id, employee=employee, date=today
        ).first()

        if not record or not record.clock_in:
            return Response({'error': {'message': 'No clock-in found for today'}}, status=400)

        if record.clock_out:
            return Response({'error': {'message': 'Already clocked out today'}}, status=400)

        now = timezone.now()
        data = serializer.validated_data

        record.clock_out = now
        record.clock_out_source = data.get('source', 'web')
        record.clock_out_location = data.get('location')

        # Calculate working hours
        if record.clock_in:
            delta = now - record.clock_in
            record.working_hours = round(delta.total_seconds() / 3600, 2)

        # Calculate overtime
        if record.shift and record.working_hours:
            shift_hours = float(record.shift.working_hours or 8)
            if record.working_hours > shift_hours:
                record.overtime_hours = round(float(record.working_hours) - shift_hours, 2)

        record.save()

        return Response({
            'data': AttendanceRecordSerializer(record).data,
            'meta': {'message': 'Clocked out successfully'}
        })

    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's attendance status for current user."""
        employee = getattr(request.user, 'employee_profile', None)
        if not employee:
            return Response({'data': None})
        record = AttendanceRecord.objects.filter(
            tenant_id=request.tenant_id, employee=employee, date=date.today()
        ).first()
        return Response({'data': AttendanceRecordSerializer(record).data if record else None})

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Attendance summary for payroll (days worked, absent, OT by employee)."""
        year = int(request.query_params.get('year', date.today().year))
        month = int(request.query_params.get('month', date.today().month))
        records = AttendanceRecord.objects.filter(
            tenant_id=request.tenant_id,
            date__year=year,
            date__month=month,
        ).values('employee_id').annotate(
            days_present=models.Count('id', filter=models.Q(status='present')),
            days_absent=models.Count('id', filter=models.Q(status='absent')),
            total_ot_hours=models.Sum('overtime_hours'),
            total_late_minutes=models.Sum('late_minutes'),
        )
        return Response({'data': list(records)})

    @action(detail=False, methods=['post'])
    def regularize(self, request):
        """Regularize (correct) a missing/incorrect punch for a past date."""
        employee = getattr(request.user, 'employee_profile', None)
        if not employee:
            return Response({'error': {'message': 'No employee profile linked'}}, status=400)

        target_date = request.data.get('date')
        clock_in_time = request.data.get('clock_in')
        clock_out_time = request.data.get('clock_out')
        reason = request.data.get('reason', '')

        if not target_date:
            return Response({'error': {'message': 'date is required'}}, status=400)

        from datetime import datetime as dt
        target = dt.strptime(target_date, '%Y-%m-%d').date()

        record, created = AttendanceRecord.objects.get_or_create(
            tenant_id=request.tenant_id,
            employee=employee,
            date=target,
            defaults={'status': 'regularized'},
        )

        if clock_in_time:
            record.clock_in = timezone.make_aware(dt.strptime(f"{target_date} {clock_in_time}", '%Y-%m-%d %H:%M'))
            record.clock_in_source = 'regularization'

        if clock_out_time:
            record.clock_out = timezone.make_aware(dt.strptime(f"{target_date} {clock_out_time}", '%Y-%m-%d %H:%M'))
            record.clock_out_source = 'regularization'

        if record.clock_in and record.clock_out:
            delta = record.clock_out - record.clock_in
            record.working_hours = round(delta.total_seconds() / 3600, 2)

        record.status = 'regularized'
        record.notes = reason
        record.save()

        return Response({
            'data': AttendanceRecordSerializer(record).data,
            'meta': {'message': 'Attendance regularized'}
        })

    @action(detail=False, methods=['get'])
    def history(self, request):
        """Weekly/monthly attendance history for current user."""
        employee = getattr(request.user, 'employee_profile', None)
        if not employee:
            return Response({'data': []})

        range_type = request.query_params.get('range', 'week')
        if range_type == 'week':
            start = date.today() - timedelta(days=date.today().weekday())
        else:
            start = date.today().replace(day=1)

        records = AttendanceRecord.objects.filter(
            tenant_id=request.tenant_id,
            employee=employee,
            date__gte=start,
            date__lte=date.today(),
        ).order_by('-date')
        return Response({'data': AttendanceRecordSerializer(records, many=True).data})

    @action(detail=False, methods=['get'], url_path='qr-token')
    def qr_token(self, request):
        """Generate a signed QR code token for the current employee.

        The token is valid for 2 minutes and encodes the employee's identity.
        The client (mobile app or employee kiosk) displays this as a QR code.
        A kiosk operator/scanner app then calls /attendance/qr-scan/ with the token.

        Returns: { token, expires_at }
        """
        from django.core import signing
        from django.utils import timezone as tz

        employee = getattr(request.user, 'employee_profile', None)
        if not employee:
            return Response({'error': {'message': 'No employee profile linked to this account'}}, status=400)

        payload = {
            'employee_id': str(employee.id),
            'tenant_id': str(request.tenant_id),
            'employee_number': employee.employee_number,
        }
        # Sign with max_age=120 seconds (2 minutes)
        token = signing.dumps(payload, salt='qr_attendance')
        expires_at = tz.now() + timedelta(seconds=120)

        return Response({
            'data': {
                'token': token,
                'expires_at': expires_at.isoformat(),
                'employee_number': employee.employee_number,
                'employee_name': employee.full_name,
            }
        })

    @action(detail=False, methods=['post'], url_path='qr-scan')
    def qr_scan(self, request):
        """Process a scanned QR attendance token.

        Used by a kiosk or manager device. Verifies the signed token and
        records a clock-in (or clock-out if already clocked in) for the employee.

        Body: { "token": "<signed token>", "action": "clock-in" | "clock-out" }
        """
        from django.core import signing

        token = request.data.get('token', '').strip()
        scan_action = request.data.get('action', 'clock-in')

        if not token:
            return Response({'error': {'message': 'token is required'}}, status=400)

        try:
            payload = signing.loads(token, salt='qr_attendance', max_age=120)
        except signing.SignatureExpired:
            return Response({'error': {'message': 'QR code has expired. Ask the employee to regenerate it.'}}, status=400)
        except signing.BadSignature:
            return Response({'error': {'message': 'Invalid QR code'}}, status=400)

        # Verify tenant matches
        if str(payload.get('tenant_id')) != str(request.tenant_id):
            return Response({'error': {'message': 'QR code belongs to a different workspace'}}, status=400)

        from core_hr.models import Employee as HREmployee
        try:
            employee = HREmployee.objects.get(
                id=payload['employee_id'],
                tenant_id=request.tenant_id,
                status__in=['active', 'probation'],
            )
        except HREmployee.DoesNotExist:
            return Response({'error': {'message': 'Employee not found or inactive'}}, status=404)

        today = date.today()
        now = timezone.now()

        record = AttendanceRecord.objects.filter(
            tenant_id=request.tenant_id, employee=employee, date=today
        ).first()

        if scan_action == 'clock-in':
            if record and record.clock_in:
                return Response({'error': {'message': f'{employee.full_name} is already clocked in today'}}, status=400)

            if not record:
                record = AttendanceRecord.objects.create(
                    tenant_id=request.tenant_id,
                    employee=employee,
                    date=today,
                    clock_in=now,
                    clock_in_source='qr',
                    status='present',
                )
            else:
                record.clock_in = now
                record.clock_in_source = 'qr'
                record.save()

            return Response({
                'data': AttendanceRecordSerializer(record).data,
                'meta': {'message': f'{employee.full_name} clocked in via QR at {now.strftime("%H:%M")}'},
            }, status=status.HTTP_201_CREATED)

        elif scan_action == 'clock-out':
            if not record or not record.clock_in:
                return Response({'error': {'message': f'{employee.full_name} has not clocked in today'}}, status=400)
            if record.clock_out:
                return Response({'error': {'message': f'{employee.full_name} already clocked out today'}}, status=400)

            record.clock_out = now
            record.clock_out_source = 'qr'
            if record.clock_in:
                delta = now - record.clock_in
                record.working_hours = round(delta.total_seconds() / 3600, 2)
            record.save()

            return Response({
                'data': AttendanceRecordSerializer(record).data,
                'meta': {'message': f'{employee.full_name} clocked out via QR at {now.strftime("%H:%M")}'},
            })

        else:
            return Response({'error': {'message': 'action must be "clock-in" or "clock-out"'}}, status=400)


class OvertimeViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = OvertimeRecord.objects.select_related('employee').all()
    serializer_class = OvertimeRecordSerializer
    filterset_fields = ['employee', 'status', 'date']

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        record = self.get_object()
        record.status = 'approved'
        record.approved_by = request.user
        record.save()
        return Response({'data': OvertimeRecordSerializer(record).data, 'meta': {'message': 'OT approved'}})


class ShiftAssignmentViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    """CRUD for shift assignments — assign employees to shifts per-day or as recurring defaults."""
    queryset = ShiftAssignment.objects.select_related('employee', 'shift').all()
    serializer_class = ShiftAssignmentSerializer
    filterset_fields = ['employee', 'shift', 'date', 'is_default']
    ordering_fields = ['date', 'employee']


# =============================================================================
# P1 Upgrades — Roster, Shift Swap, Shift Bid, Geofence
# =============================================================================

from rest_framework import serializers as drf_serializers


class _RosterSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = Roster
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']


class _RosterSlotSerializer(drf_serializers.ModelSerializer):
    employee_name = drf_serializers.CharField(source='employee.full_name', read_only=True)

    class Meta:
        model = RosterSlot
        fields = '__all__'
        read_only_fields = ['id']


class _ShiftSwapRequestSerializer(drf_serializers.ModelSerializer):
    requester_name = drf_serializers.CharField(source='requester.full_name', read_only=True)

    class Meta:
        model = ShiftSwapRequest
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']


class _ShiftBidSerializer(drf_serializers.ModelSerializer):
    application_count = drf_serializers.SerializerMethodField()

    class Meta:
        model = ShiftBid
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']

    def get_application_count(self, obj):
        return obj.applications.count()


class _ShiftBidApplicationSerializer(drf_serializers.ModelSerializer):
    employee_name = drf_serializers.CharField(source='employee.full_name', read_only=True)

    class Meta:
        model = ShiftBidApplication
        fields = '__all__'
        read_only_fields = ['id', 'applied_at']


class _GeofenceZoneSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = GeofenceZone
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']


class RosterViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = Roster.objects.select_related('department', 'branch').all()
    serializer_class = _RosterSerializer
    filterset_fields = ['status', 'department', 'branch']
    ordering_fields = ['week_start', 'created_at']

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        roster = self.get_object()
        roster.status = 'published'
        roster.published_at = timezone.now()
        roster.published_by = request.user
        roster.save(update_fields=['status', 'published_at', 'published_by', 'updated_at'])
        return Response({'data': _RosterSerializer(roster).data,
                         'meta': {'message': 'Roster published'}})

    @action(detail=True, methods=['get'])
    def slots(self, request, pk=None):
        roster = self.get_object()
        slots = roster.slots.select_related('employee', 'shift').all()
        return Response({'data': _RosterSlotSerializer(slots, many=True).data})


class RosterSlotViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = _RosterSlotSerializer
    filterset_fields = ['roster', 'employee', 'date', 'is_day_off']

    def get_queryset(self):
        return RosterSlot.objects.select_related('employee', 'shift').filter(
            roster__tenant_id=self.request.tenant_id
        )


class ShiftSwapRequestViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = ShiftSwapRequest.objects.select_related('requester', 'swap_with').all()
    serializer_class = _ShiftSwapRequestSerializer
    filterset_fields = ['requester', 'swap_with', 'status']
    ordering_fields = ['swap_date', 'created_at']

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        swap = self.get_object()
        swap.status = 'accepted'
        swap.peer_response_at = timezone.now()
        swap.save(update_fields=['status', 'peer_response_at'])
        return Response({'data': _ShiftSwapRequestSerializer(swap).data})

    @action(detail=True, methods=['post'])
    def manager_approve(self, request, pk=None):
        swap = self.get_object()
        swap.status = 'manager_approved'
        swap.manager_approved_by = request.user
        swap.manager_approved_at = timezone.now()
        swap.save(update_fields=['status', 'manager_approved_by', 'manager_approved_at'])
        return Response({'data': _ShiftSwapRequestSerializer(swap).data})


class ShiftBidViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = ShiftBid.objects.select_related('shift', 'department').all()
    serializer_class = _ShiftBidSerializer
    filterset_fields = ['status', 'department', 'date']
    ordering_fields = ['date', 'bid_deadline']

    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        """Current user's employee applies for the open shift bid."""
        from core_hr.models import Employee
        bid = self.get_object()
        if bid.status != 'open':
            return Response({'error': 'Bid is not open'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            emp = Employee.objects.get(tenant_id=request.tenant_id, user=request.user)
        except Employee.DoesNotExist:
            return Response({'error': 'No employee record'}, status=status.HTTP_400_BAD_REQUEST)
        application, created = ShiftBidApplication.objects.get_or_create(
            bid=bid, employee=emp, defaults={'status': 'pending'}
        )
        return Response({
            'data': _ShiftBidApplicationSerializer(application).data,
            'meta': {'created': created},
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class ShiftBidApplicationViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = _ShiftBidApplicationSerializer
    filterset_fields = ['status', 'employee']

    def get_queryset(self):
        return ShiftBidApplication.objects.select_related('bid', 'employee').filter(
            bid__tenant_id=self.request.tenant_id
        )

    @action(detail=True, methods=['post'])
    def award(self, request, pk=None):
        application = self.get_object()
        application.status = 'awarded'
        application.save(update_fields=['status'])
        return Response({'data': _ShiftBidApplicationSerializer(application).data})


class GeofenceZoneViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = GeofenceZone.objects.select_related('branch').all()
    serializer_class = _GeofenceZoneSerializer
    filterset_fields = ['branch', 'is_active']


# =============================================================================
# Feature 4 — New ViewSets
# =============================================================================

from .models import (
    EmployeeAvailability, BreakRecord, BiometricDevice, FatigueAlert,
    AttendanceAnomaly, AbsenceForecast, OvertimeThreshold, UnionRulePack,
    SiteAttendanceAnalytics, ContractorTimeEntry, ShiftCoveragePlan,
)


class _EmployeeAvailabilitySerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = EmployeeAvailability
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']


class _BreakRecordSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = BreakRecord
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']


class _BiometricDeviceSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = BiometricDevice
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']


class _FatigueAlertSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = FatigueAlert
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']


class _AttendanceAnomalySerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = AttendanceAnomaly
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'detected_at']


class _AbsenceForecastSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = AbsenceForecast
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'generated_at']


class _OvertimeThresholdSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = OvertimeThreshold
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']


class _UnionRulePackSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = UnionRulePack
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']


class _SiteAttendanceAnalyticsSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = SiteAttendanceAnalytics
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'computed_at']


class _ContractorTimeEntrySerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = ContractorTimeEntry
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']


class _ShiftCoveragePlanSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = ShiftCoveragePlan
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']


class EmployeeAvailabilityViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = _EmployeeAvailabilitySerializer
    filterset_fields = ['employee', 'is_active']
    ordering_fields = ['effective_from']

    def get_queryset(self):
        return EmployeeAvailability.objects.filter(tenant_id=self.request.tenant_id)


class BreakRecordViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = _BreakRecordSerializer
    filterset_fields = ['employee', 'break_type', 'is_compliant']
    ordering_fields = ['break_start']

    def get_queryset(self):
        return BreakRecord.objects.filter(tenant_id=self.request.tenant_id).select_related('employee')


class BiometricDeviceViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = _BiometricDeviceSerializer
    filterset_fields = ['branch', 'device_type', 'status']

    def get_queryset(self):
        return BiometricDevice.objects.filter(tenant_id=self.request.tenant_id).select_related('branch')


class FatigueAlertViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = _FatigueAlertSerializer
    filterset_fields = ['employee', 'severity', 'is_acknowledged']
    ordering_fields = ['alert_date', 'severity']

    def get_queryset(self):
        return FatigueAlert.objects.filter(tenant_id=self.request.tenant_id).select_related('employee')

    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        alert = self.get_object()
        alert.is_acknowledged = True
        alert.acknowledged_by = request.user
        alert.acknowledged_at = timezone.now()
        alert.save(update_fields=['is_acknowledged', 'acknowledged_by', 'acknowledged_at'])
        return Response({'data': _FatigueAlertSerializer(alert).data})


class AttendanceAnomalyViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = _AttendanceAnomalySerializer
    filterset_fields = ['employee', 'anomaly_type', 'is_confirmed', 'is_false_positive']
    ordering_fields = ['detected_at', 'confidence_score']

    def get_queryset(self):
        return AttendanceAnomaly.objects.filter(tenant_id=self.request.tenant_id).select_related('employee')


class AbsenceForecastViewSet(TenantViewSetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = _AbsenceForecastSerializer
    filterset_fields = ['department']
    ordering_fields = ['forecast_date']

    def get_queryset(self):
        return AbsenceForecast.objects.filter(tenant_id=self.request.tenant_id).select_related('department')


class OvertimeThresholdViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = _OvertimeThresholdSerializer
    filterset_fields = ['department', 'is_active']

    def get_queryset(self):
        return OvertimeThreshold.objects.filter(tenant_id=self.request.tenant_id)


class UnionRulePackViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = _UnionRulePackSerializer
    filterset_fields = ['is_active']
    ordering_fields = ['effective_from']

    def get_queryset(self):
        return UnionRulePack.objects.filter(tenant_id=self.request.tenant_id)


class SiteAttendanceAnalyticsViewSet(TenantViewSetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = _SiteAttendanceAnalyticsSerializer
    filterset_fields = ['branch', 'period_type']
    ordering_fields = ['period_date']

    def get_queryset(self):
        return SiteAttendanceAnalytics.objects.filter(tenant_id=self.request.tenant_id).select_related('branch')


class ContractorTimeEntryViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = _ContractorTimeEntrySerializer
    filterset_fields = ['status', 'department']
    ordering_fields = ['work_date', 'created_at']

    def get_queryset(self):
        return ContractorTimeEntry.objects.filter(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        entry = self.get_object()
        entry.status = 'approved'
        entry.approved_by = request.user
        entry.save(update_fields=['status', 'approved_by', 'updated_at'])
        return Response({'data': _ContractorTimeEntrySerializer(entry).data})


class ShiftCoveragePlanViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    serializer_class = _ShiftCoveragePlanSerializer
    filterset_fields = ['manager', 'status', 'department']
    ordering_fields = ['coverage_date']

    def get_queryset(self):
        return ShiftCoveragePlan.objects.filter(tenant_id=self.request.tenant_id).select_related(
            'manager', 'shift', 'department'
        )
