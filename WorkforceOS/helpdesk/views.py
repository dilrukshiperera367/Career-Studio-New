"""HR Helpdesk API — Tickets, Categories, Comments, Service Catalog, Chatbot."""

from rest_framework import viewsets, serializers, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta

from config.base_api import TenantViewSetMixin, TenantSerializerMixin
from .models import (
    TicketCategory, Ticket, TicketComment,
    ServiceCatalogItem, ServiceRequest, ChatbotIntake, SLADashboardConfig,
)


# --- Serializers ---

class TicketCategorySerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = TicketCategory
        fields = '__all__'
        read_only_fields = ['id', 'tenant']


class TicketCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = TicketComment
        fields = '__all__'
        read_only_fields = ['id', 'created_at']

    def get_author_name(self, obj):
        return obj.author.full_name if obj.author else 'System'


class TicketSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    assigned_to_name = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    sla_status = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'ticket_number', 'created_at', 'updated_at',
                           'first_response_at', 'sla_response_breached', 'sla_resolution_breached']

    def get_assigned_to_name(self, obj):
        return obj.assigned_to.full_name if obj.assigned_to else None

    def get_comments_count(self, obj):
        return obj.comments.count()

    def get_sla_status(self, obj):
        now = timezone.now()
        if obj.sla_response_due and not obj.first_response_at and now > obj.sla_response_due:
            return 'response_breached'
        if obj.sla_resolution_due and obj.status not in ('resolved', 'closed') and now > obj.sla_resolution_due:
            return 'resolution_breached'
        return 'on_track'


# --- Views ---

class TicketCategoryViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = TicketCategory.objects.all()
    serializer_class = TicketCategorySerializer
    permission_classes = [permissions.IsAuthenticated]


class TicketViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = Ticket.objects.select_related('employee', 'category', 'assigned_to').all()
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'priority', 'category', 'assigned_to', 'employee']
    search_fields = ['ticket_number', 'subject']
    ordering_fields = ['created_at', 'priority']

    def perform_create(self, serializer):
        ticket = serializer.save()
        # Auto-set SLA deadlines from category
        if ticket.category:
            now = timezone.now()
            ticket.sla_response_due = now + timedelta(hours=ticket.category.sla_response_hours)
            ticket.sla_resolution_due = now + timedelta(hours=ticket.category.sla_resolution_hours)
            if ticket.category.default_assignee and not ticket.assigned_to:
                ticket.assigned_to = ticket.category.default_assignee
            ticket.save()

    @action(detail=True, methods=['post'], url_path='add-comment')
    def add_comment(self, request, pk=None):
        ticket = self.get_object()
        comment = TicketComment.objects.create(
            ticket=ticket, author=request.user,
            body=request.data.get('body', ''),
            is_internal=request.data.get('is_internal', False))
        # Record first response time
        if not ticket.first_response_at and ticket.assigned_to == request.user:
            ticket.first_response_at = timezone.now()
            ticket.sla_response_breached = (
                ticket.sla_response_due and timezone.now() > ticket.sla_response_due)
            ticket.save()
        return Response({'data': TicketCommentSerializer(comment).data}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def comments(self, request, pk=None):
        ticket = self.get_object()
        qs = ticket.comments.select_related('author').all()
        # Hide internal notes from non-staff
        if not request.user.is_staff:
            qs = qs.filter(is_internal=False)
        return Response({'data': TicketCommentSerializer(qs, many=True).data})

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        ticket = self.get_object()
        ticket.status = 'resolved'
        ticket.resolved_at = timezone.now()
        ticket.sla_resolution_breached = (
            ticket.sla_resolution_due and timezone.now() > ticket.sla_resolution_due)
        ticket.save()
        return Response({'data': TicketSerializer(ticket).data})

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        ticket = self.get_object()
        ticket.assigned_to_id = request.data.get('assigned_to')
        ticket.status = 'in_progress'
        ticket.save()
        return Response({'data': TicketSerializer(ticket).data})

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        qs = self.get_queryset()
        return Response({'data': {
            'total': qs.count(),
            'open': qs.filter(status='open').count(),
            'in_progress': qs.filter(status='in_progress').count(),
            'resolved': qs.filter(status='resolved').count(),
            'sla_breached': qs.filter(sla_response_breached=True).count() + qs.filter(sla_resolution_breached=True).count(),
        }})


# =============================================================================
# P1 Upgrades — Service Catalog, Service Requests, Chatbot Intake, SLA Config
# =============================================================================

class ServiceCatalogItemSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)

    class Meta:
        model = ServiceCatalogItem
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at']


class ServiceRequestSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    catalog_item_name = serializers.CharField(source='catalog_item.name', read_only=True)

    class Meta:
        model = ServiceRequest
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']


class ChatbotIntakeSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = ChatbotIntake
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'started_at']

    def get_employee_name(self, obj):
        return obj.employee.full_name if obj.employee else None


class SLADashboardConfigSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = SLADashboardConfig
        fields = '__all__'
        read_only_fields = ['id', 'tenant', 'updated_at']


class ServiceCatalogItemViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = ServiceCatalogItem.objects.select_related('category').all()
    serializer_class = ServiceCatalogItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['is_active', 'category']
    search_fields = ['name', 'description']
    ordering_fields = ['sort_order', 'name', 'created_at']


class ServiceRequestViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = ServiceRequest.objects.select_related('catalog_item', 'employee', 'ticket').all()
    serializer_class = ServiceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'catalog_item', 'employee']
    ordering_fields = ['created_at', 'due_by']

    def perform_create(self, serializer):
        instance = serializer.save()
        # Auto-set due_by from catalog item SLA
        if not instance.due_by and instance.catalog_item.fulfillment_sla_hours:
            instance.due_by = timezone.now() + timedelta(hours=instance.catalog_item.fulfillment_sla_hours)
            instance.save(update_fields=['due_by'])

    @action(detail=True, methods=['post'])
    def fulfill(self, request, pk=None):
        sr = self.get_object()
        sr.status = 'fulfilled'
        sr.fulfilled_at = timezone.now()
        sr.fulfillment_notes = request.data.get('fulfillment_notes', sr.fulfillment_notes)
        sr.save(update_fields=['status', 'fulfilled_at', 'fulfillment_notes'])
        return Response({'data': ServiceRequestSerializer(sr).data})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        sr = self.get_object()
        sr.status = 'rejected'
        sr.fulfillment_notes = request.data.get('fulfillment_notes', sr.fulfillment_notes)
        sr.save(update_fields=['status', 'fulfillment_notes'])
        return Response({'data': ServiceRequestSerializer(sr).data})


class ChatbotIntakeViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = ChatbotIntake.objects.select_related('employee', 'escalated_ticket').all()
    serializer_class = ChatbotIntakeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['channel', 'resolved_by_bot', 'employee']
    ordering_fields = ['started_at']

    @action(detail=True, methods=['post'])
    def escalate(self, request, pk=None):
        """Escalate this chatbot session to a helpdesk ticket."""
        intake = self.get_object()
        if intake.escalated_ticket:
            return Response({'error': 'Already escalated'}, status=status.HTTP_400_BAD_REQUEST)
        employee = intake.employee
        ticket = Ticket.objects.create(
            tenant_id=request.tenant_id,
            employee=employee,
            subject=request.data.get('subject', f'Escalated from chatbot session {intake.session_id}'),
            description=request.data.get('description', ''),
            priority=request.data.get('priority', 'medium'),
        )
        intake.escalated_ticket = ticket
        intake.resolved_by_bot = False
        intake.ended_at = timezone.now()
        intake.save(update_fields=['escalated_ticket', 'resolved_by_bot', 'ended_at'])
        return Response({'data': {'ticket_id': str(ticket.id), 'ticket_number': ticket.ticket_number}},
                        status=status.HTTP_201_CREATED)


class SLADashboardConfigViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = SLADashboardConfig.objects.all()
    serializer_class = SLADashboardConfigSerializer
    permission_classes = [permissions.IsAuthenticated]
