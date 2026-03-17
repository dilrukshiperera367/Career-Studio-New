from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import EmployerVerification, RecruiterVerification, FraudReport, TrustScore
from .serializers import (
    EmployerVerificationSerializer, RecruiterVerificationSerializer,
    FraudReportSerializer, TrustScoreSerializer
)


class EmployerVerificationViewSet(viewsets.ModelViewSet):
    queryset = EmployerVerification.objects.all()
    serializer_class = EmployerVerificationSerializer
    permission_classes = [permissions.IsAuthenticated]


class RecruiterVerificationViewSet(viewsets.ModelViewSet):
    queryset = RecruiterVerification.objects.all()
    serializer_class = RecruiterVerificationSerializer
    permission_classes = [permissions.IsAuthenticated]


class FraudReportViewSet(viewsets.ModelViewSet):
    serializer_class = FraudReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return FraudReport.objects.all()

    def perform_create(self, serializer):
        serializer.save(reported_by=self.request.user)


class TrustScoreViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TrustScore.objects.all()
    serializer_class = TrustScoreSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @action(detail=False, methods=['get'])
    def lookup(self, request):
        entity_type = request.query_params.get('entity_type')
        entity_id = request.query_params.get('entity_id')
        if not entity_type or not entity_id:
            return Response({'error': 'entity_type and entity_id required'}, status=400)
        try:
            score = TrustScore.objects.get(entity_type=entity_type, entity_id=entity_id)
            return Response(TrustScoreSerializer(score).data)
        except TrustScore.DoesNotExist:
            return Response({'overall_score': 0.5, 'status': 'unscored'})
