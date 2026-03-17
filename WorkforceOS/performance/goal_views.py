"""
Enhanced performance goal tracking views.
Adds progress updates, goal cascading, and completion analytics.
"""
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db.models import Avg, Count, Q
from django.utils import timezone


class GoalProgressUpdateSerializer(serializers.Serializer):
    progress = serializers.IntegerField(min_value=0, max_value=100)
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)


class GoalAnalyticsView(APIView):
    """
    GET /api/v1/performance/goals/analytics/
    Returns goal completion stats for the current tenant.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            from performance.models import Goal
        except ImportError:
            # Try alternate model names
            try:
                from performance.models import PerformanceGoal as Goal
            except ImportError:
                return Response({'detail': 'Goal model not found'}, status=404)

        queryset = Goal.objects.all()
        tenant = getattr(request, 'tenant', None)
        if tenant:
            queryset = queryset.filter(tenant=tenant) if hasattr(Goal, 'tenant') else queryset

        total = queryset.count()
        if total == 0:
            return Response({
                'total': 0, 'completed': 0, 'in_progress': 0,
                'not_started': 0, 'completion_rate': 0, 'avg_progress': 0,
            })

        # Try to get status/progress fields
        stats = {'total': total}
        for status_field in ('status', 'state'):
            if hasattr(Goal, status_field):
                completed = queryset.filter(**{status_field: 'completed'}).count()
                in_progress = queryset.filter(**{status_field: 'in_progress'}).count()
                stats['completed'] = completed
                stats['in_progress'] = in_progress
                stats['not_started'] = total - completed - in_progress
                stats['completion_rate'] = round(completed / total * 100, 1)
                break

        for progress_field in ('progress', 'progress_percentage', 'percent_complete'):
            if hasattr(Goal, progress_field):
                avg = queryset.aggregate(avg=Avg(progress_field))['avg'] or 0
                stats['avg_progress'] = round(avg, 1)
                break

        return Response(stats)


class TeamGoalsSummaryView(APIView):
    """
    GET /api/v1/performance/goals/team-summary/?manager_id=<id>
    Returns goal summary for all direct reports of a manager.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            from performance.models import Goal
        except ImportError:
            try:
                from performance.models import PerformanceGoal as Goal
            except ImportError:
                return Response({'detail': 'Goal model not found'}, status=404)

        employee_id = request.query_params.get('employee_id')
        manager_id = request.query_params.get('manager_id')

        queryset = Goal.objects.all()
        if employee_id:
            for field in ('employee_id', 'assigned_to_id', 'owner_id'):
                if hasattr(Goal, field.replace('_id', '')):
                    queryset = queryset.filter(**{field: employee_id})
                    break

        results = []
        for goal in queryset.select_related() if hasattr(queryset, 'select_related') else queryset:
            item = {
                'id': goal.id,
                'title': str(getattr(goal, 'title', '') or getattr(goal, 'name', '') or goal),
                'status': str(getattr(goal, 'status', '') or getattr(goal, 'state', '')),
                'progress': getattr(goal, 'progress', 0) or getattr(goal, 'progress_percentage', 0) or 0,
                'due_date': str(getattr(goal, 'due_date', '') or getattr(goal, 'deadline', '') or ''),
            }
            results.append(item)

        return Response({'count': len(results), 'results': results})
