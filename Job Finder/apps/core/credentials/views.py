from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Credential, CredentialShare
from .serializers import (
    CredentialListSerializer, CredentialDetailSerializer,
    CredentialCreateSerializer, CredentialShareSerializer
)


class CredentialViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Credential.objects.filter(owner=self.request.user)

    def get_serializer_class(self):
        if self.action == 'list':
            return CredentialListSerializer
        if self.action == 'create':
            return CredentialCreateSerializer
        return CredentialDetailSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=['get'])
    def expiring(self, request):
        """Get credentials expiring in the next 90 days."""
        from django.utils import timezone
        import datetime
        cutoff = timezone.now().date() + datetime.timedelta(days=90)
        expiring = self.get_queryset().filter(
            expiry_date__lte=cutoff,
            expiry_date__gte=timezone.now().date(),
            status__in=['verified', 'pending', 'unverified'],
        )
        return Response(CredentialListSerializer(expiring, many=True).data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        qs = self.get_queryset()
        return Response({
            'total': qs.count(),
            'verified': qs.filter(status='verified').count(),
            'expired': qs.filter(status='expired').count(),
            'pending': qs.filter(status='pending').count(),
            'by_type': dict(
                qs.values_list('credential_type').annotate(
                    count=__import__('django.db.models', fromlist=['Count']).Count('id')
                ).values_list('credential_type', 'count')
            ),
        })

    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        credential = self.get_object()
        shared_with_id = request.data.get('shared_with')
        if not shared_with_id:
            return Response(
                {'error': 'shared_with is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        share = CredentialShare.objects.create(
            credential=credential,
            shared_with_id=shared_with_id,
        )
        return Response(
            CredentialShareSerializer(share).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['get'], url_path='public/(?P<user_id>[^/.]+)')
    def public_profile(self, request, user_id=None):
        """View someone's public credentials."""
        public_creds = Credential.objects.filter(
            owner_id=user_id, is_public=True,
            status__in=['verified', 'pending']
        )
        return Response(CredentialListSerializer(public_creds, many=True).data)
