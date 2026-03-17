from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import CommunicationTemplate, CommunicationMessage, CommunicationPreference
from .serializers import (
    CommunicationTemplateSerializer, CommunicationMessageSerializer,
    CommunicationPreferenceSerializer, SendMessageSerializer
)


class CommunicationTemplateViewSet(viewsets.ModelViewSet):
    queryset = CommunicationTemplate.objects.filter(is_active=True)
    serializer_class = CommunicationTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'slug'

    def get_queryset(self):
        qs = super().get_queryset()
        channel = self.request.query_params.get('channel')
        category = self.request.query_params.get('category')
        if channel:
            qs = qs.filter(channel=channel)
        if category:
            qs = qs.filter(category=category)
        return qs


class CommunicationMessageViewSet(viewsets.ModelViewSet):
    serializer_class = CommunicationMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CommunicationMessage.objects.filter(
            sent_by=self.request.user
        ).select_related('recipient', 'template')

    @action(detail=False, methods=['get'])
    def inbox(self, request):
        messages = CommunicationMessage.objects.filter(
            recipient=request.user
        ).order_by('-created_at')[:50]
        return Response(
            CommunicationMessageSerializer(messages, many=True).data
        )

    @action(detail=False, methods=['post'])
    def send(self, request):
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        msg = CommunicationMessage.objects.create(
            channel=data['channel'],
            category='system',
            sent_by=request.user,
            recipient_id=data['recipient_id'],
            subject=data.get('subject', ''),
            body=data['body'],
            entity_type=data.get('entity_type', ''),
            entity_id=data.get('entity_id'),
            status=CommunicationMessage.STATUS_QUEUED,
        )
        return Response(
            CommunicationMessageSerializer(msg).data,
            status=status.HTTP_201_CREATED
        )


class CommunicationPreferenceViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        prefs, _ = CommunicationPreference.objects.get_or_create(
            user=request.user
        )
        return Response(CommunicationPreferenceSerializer(prefs).data)

    def create(self, request):
        prefs, _ = CommunicationPreference.objects.get_or_create(
            user=request.user
        )
        serializer = CommunicationPreferenceSerializer(
            prefs, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
