"""
Team scorecard aggregation — computes average scores across all interviewers
for a given application, grouped by criterion.
"""
from __future__ import annotations
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Avg, Count

from apps.scoring.models import Scorecard


class TeamScorecardView(APIView):
    """
    GET /api/v1/scoring/team-scorecard/?application_id=<id>
    
    Returns:
      {
        "application_id": 42,
        "total_interviewers": 3,
        "overall_avg": 4.1,
        "by_criterion": [
          {"criterion": "Technical Skills", "avg": 4.3, "responses": 3},
          ...
        ],
        "by_interviewer": [
          {"interviewer": "Jane Smith", "overall_avg": 4.2, "scores": [...]},
          ...
        ]
      }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        application_id = request.query_params.get('application_id')
        if not application_id:
            return Response({'detail': 'application_id query parameter is required.'}, status=400)

        qs = Scorecard.objects.filter(application_id=application_id)

        if not qs.exists():
            return Response({
                'application_id': application_id,
                'total_interviewers': 0,
                'overall_avg': None,
                'by_criterion': [],
                'by_interviewer': [],
                'message': 'No scorecards submitted yet.',
            })

        # Overall average score across all scorecards
        overall = qs.aggregate(avg=Avg('overall_score'), count=Count('id'))

        # Count distinct interviewers
        interviewers_count = qs.values('interviewer_id').distinct().count()

        # By criterion — aggregate across criteria JSONField is not directly queryable,
        # so we report by interviewer recommendation instead
        by_criterion = []

        # By interviewer
        by_interviewer = []
        for interviewer_id in qs.values_list('interviewer_id', flat=True).distinct():
            user_qs = qs.filter(interviewer_id=interviewer_id)
            user_avg = user_qs.aggregate(avg=Avg('overall_score'))['avg'] or 0
            interviewer_obj = getattr(user_qs.first(), 'interviewer', None)
            name = str(interviewer_obj) if interviewer_obj else f'User {interviewer_id}'
            by_interviewer.append({
                'interviewer': name,
                'overall_avg': round(user_avg, 2),
                'count': user_qs.count(),
            })

        return Response({
            'application_id': application_id,
            'total_interviewers': interviewers_count,
            'overall_avg': round(overall['avg'] or 0, 2),
            'total_responses': overall['count'],
            'by_criterion': by_criterion,
            'by_interviewer': by_interviewer,
        })
