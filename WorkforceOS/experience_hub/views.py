"""Experience Hub API views + serializers."""

from django.utils import timezone
from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from config.base_api import TenantViewSetMixin, TenantSerializerMixin
from config.permissions import PermissionViewSetMixin
from core_hr.models import Employee
from .models import (
    ERG, ERGMembership, CommunityEvent, EventRSVP,
    RecognitionProgram, RecognitionNomination,
)


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

class ERGSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ERG
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')


class ERGMembershipSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ERGMembership
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'joined_at')


class CommunityEventSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = CommunityEvent
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')


class EventRSVPSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = EventRSVP
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'registered_at')


class RecognitionProgramSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = RecognitionProgram
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')


class RecognitionNominationSerializer(TenantSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = RecognitionNomination
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at')


# ---------------------------------------------------------------------------
# ViewSets
# ---------------------------------------------------------------------------

class ERGViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = ERG.objects.all()
    serializer_class = ERGSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'is_active']
    search_fields = ['name']
    ordering_fields = ['name', 'created_at', 'member_count']
    required_permissions = {
        'list': 'experience_hub.manage_ergs',
        'retrieve': 'experience_hub.manage_ergs',
        'create': 'experience_hub.manage_ergs',
        'update': 'experience_hub.manage_ergs',
        'partial_update': 'experience_hub.manage_ergs',
        'destroy': 'experience_hub.manage_ergs',
        'join': 'experience_hub.manage_ergs',
        'leave': 'experience_hub.manage_ergs',
    }

    def get_queryset(self):
        return ERG.objects.filter(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """Join the ERG as the current employee."""
        erg = self.get_object()
        employee = getattr(request.user, 'employee_profile', None)
        if not employee:
            return Response(
                {'error': 'No employee profile linked to this user'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        membership, created = ERGMembership.objects.get_or_create(
            tenant_id=request.tenant_id,
            erg=erg,
            employee=employee,
            defaults={'role': 'member', 'is_active': True},
        )
        if not created and not membership.is_active:
            membership.is_active = True
            membership.save(update_fields=['is_active'])
        return Response(
            {'data': ERGMembershipSerializer(membership).data},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Leave the ERG as the current employee."""
        erg = self.get_object()
        employee = getattr(request.user, 'employee_profile', None)
        if not employee:
            return Response(
                {'error': 'No employee profile linked to this user'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        updated = ERGMembership.objects.filter(
            tenant_id=request.tenant_id,
            erg=erg,
            employee=employee,
            is_active=True,
        ).update(is_active=False)
        if not updated:
            return Response(
                {'error': 'Membership not found'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({'detail': 'Left ERG successfully.'})


class ERGMembershipViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = ERGMembership.objects.select_related('erg', 'employee').all()
    serializer_class = ERGMembershipSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['erg', 'employee', 'role', 'is_active']
    ordering_fields = ['joined_at', 'role']
    required_permissions = {
        'list': 'experience_hub.manage_erg_memberships',
        'retrieve': 'experience_hub.manage_erg_memberships',
        'create': 'experience_hub.manage_erg_memberships',
        'update': 'experience_hub.manage_erg_memberships',
        'partial_update': 'experience_hub.manage_erg_memberships',
        'destroy': 'experience_hub.manage_erg_memberships',
    }

    def get_queryset(self):
        return ERGMembership.objects.select_related(
            'erg', 'employee'
        ).filter(tenant_id=self.request.tenant_id)


class CommunityEventViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = CommunityEvent.objects.select_related('organizer', 'erg').all()
    serializer_class = CommunityEventSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['event_type', 'status', 'erg']
    search_fields = ['title']
    ordering_fields = ['start_datetime', 'created_at', 'attendees_count']
    required_permissions = {
        'list': 'experience_hub.manage_events',
        'retrieve': 'experience_hub.manage_events',
        'create': 'experience_hub.manage_events',
        'update': 'experience_hub.manage_events',
        'partial_update': 'experience_hub.manage_events',
        'destroy': 'experience_hub.manage_events',
        'upcoming': 'experience_hub.manage_events',
    }

    def get_queryset(self):
        return CommunityEvent.objects.select_related(
            'organizer', 'erg'
        ).filter(tenant_id=self.request.tenant_id)

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Return published events with start_datetime >= now."""
        qs = self.get_queryset().filter(
            status='published',
            start_datetime__gte=timezone.now(),
        ).order_by('start_datetime')
        return Response({'data': CommunityEventSerializer(qs, many=True).data})


class EventRSVPViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = EventRSVP.objects.select_related('event', 'employee').all()
    serializer_class = EventRSVPSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['event', 'employee', 'status']
    ordering_fields = ['registered_at']
    required_permissions = {
        'list': 'experience_hub.manage_rsvps',
        'retrieve': 'experience_hub.manage_rsvps',
        'create': 'experience_hub.manage_rsvps',
        'update': 'experience_hub.manage_rsvps',
        'partial_update': 'experience_hub.manage_rsvps',
        'destroy': 'experience_hub.manage_rsvps',
        'my_rsvps': 'experience_hub.manage_rsvps',
    }

    def get_queryset(self):
        return EventRSVP.objects.select_related(
            'event', 'employee'
        ).filter(tenant_id=self.request.tenant_id)

    @action(detail=False, methods=['get'], url_path='my-rsvps')
    def my_rsvps(self, request):
        """Return RSVPs for the current employee."""
        employee = getattr(request.user, 'employee_profile', None)
        if not employee:
            return Response({'data': []})
        qs = self.get_queryset().filter(employee=employee)
        return Response({'data': EventRSVPSerializer(qs, many=True).data})


class RecognitionProgramViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = RecognitionProgram.objects.all()
    serializer_class = RecognitionProgramSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['program_type', 'is_active']
    ordering_fields = ['name', 'created_at']
    required_permissions = {
        'list': 'experience_hub.manage_recognition_programs',
        'retrieve': 'experience_hub.manage_recognition_programs',
        'create': 'experience_hub.manage_recognition_programs',
        'update': 'experience_hub.manage_recognition_programs',
        'partial_update': 'experience_hub.manage_recognition_programs',
        'destroy': 'experience_hub.manage_recognition_programs',
    }

    def get_queryset(self):
        return RecognitionProgram.objects.filter(tenant_id=self.request.tenant_id)


class RecognitionNominationViewSet(PermissionViewSetMixin, TenantViewSetMixin, viewsets.ModelViewSet):
    queryset = RecognitionNomination.objects.select_related(
        'program', 'nominator', 'nominee'
    ).all()
    serializer_class = RecognitionNominationSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['program', 'nominator', 'nominee', 'status']
    search_fields = ['reason']
    ordering_fields = ['created_at', 'points_awarded']
    required_permissions = {
        'list': 'experience_hub.manage_nominations',
        'retrieve': 'experience_hub.manage_nominations',
        'create': 'experience_hub.manage_nominations',
        'update': 'experience_hub.manage_nominations',
        'partial_update': 'experience_hub.manage_nominations',
        'destroy': 'experience_hub.manage_nominations',
        'approve': 'experience_hub.manage_nominations',
        'reject': 'experience_hub.manage_nominations',
    }

    def get_queryset(self):
        return RecognitionNomination.objects.select_related(
            'program', 'nominator', 'nominee'
        ).filter(tenant_id=self.request.tenant_id)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a pending nomination."""
        nomination = self.get_object()
        nomination.status = 'approved'
        nomination.approved_by = request.user
        nomination.approved_at = timezone.now()
        nomination.save(update_fields=['status', 'approved_by', 'approved_at'])
        return Response({'data': RecognitionNominationSerializer(nomination).data})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a pending nomination."""
        nomination = self.get_object()
        nomination.status = 'rejected'
        nomination.approved_by = request.user
        nomination.approved_at = timezone.now()
        nomination.save(update_fields=['status', 'approved_by', 'approved_at'])
        return Response({'data': RecognitionNominationSerializer(nomination).data})
