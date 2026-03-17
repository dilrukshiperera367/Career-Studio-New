from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    HeadcountPlanViewSet,
    PositionBudgetViewSet,
    VacancyPlanViewSet,
    WorkforceScenarioViewSet,
    ScenarioLineItemViewSet,
    OrgDesignScenarioViewSet,
    OrgDesignNodeViewSet,
    SpanOfControlSnapshotViewSet,
    WorkforceCostForecastViewSet,
    CostForecastLineItemViewSet,
    DepartmentBudgetActualViewSet,
    LocationWorkforcePlanViewSet,
    WorkforceMixPlanViewSet,
    CriticalRoleMappingViewSet,
    SuccessionCoveragePlanViewSet,
    SkillsDemandForecastViewSet,
    SkillsDemandLineItemViewSet,
    HiringRequisitionViewSet,
    ReorgWorkflowViewSet,
    ReorgWorkflowTaskViewSet,
)

router = DefaultRouter()

# Core planning
router.register('planning/headcount-plans', HeadcountPlanViewSet, basename='headcount-plans')
router.register('planning/position-budgets', PositionBudgetViewSet, basename='position-budgets')
router.register('planning/vacancy-plans', VacancyPlanViewSet, basename='vacancy-plans')

# Scenario planning
router.register('planning/scenarios', WorkforceScenarioViewSet, basename='workforce-scenarios')
router.register('planning/scenario-line-items', ScenarioLineItemViewSet, basename='scenario-line-items')

# Org design
router.register('planning/org-scenarios', OrgDesignScenarioViewSet, basename='org-scenarios')
router.register('planning/org-nodes', OrgDesignNodeViewSet, basename='org-nodes')

# Span of control
router.register('planning/span-snapshots', SpanOfControlSnapshotViewSet, basename='span-snapshots')

# Cost forecasting
router.register('planning/cost-forecasts', WorkforceCostForecastViewSet, basename='cost-forecasts')
router.register('planning/cost-forecast-lines', CostForecastLineItemViewSet, basename='cost-forecast-lines')

# Budget vs actual
router.register('planning/dept-budget-actuals', DepartmentBudgetActualViewSet, basename='dept-budget-actuals')

# Location planning
router.register('planning/location-plans', LocationWorkforcePlanViewSet, basename='location-plans')

# Mix planning
router.register('planning/mix-plans', WorkforceMixPlanViewSet, basename='mix-plans')

# Critical roles & succession
router.register('planning/critical-role-mappings', CriticalRoleMappingViewSet, basename='critical-role-mappings')
router.register('planning/succession-coverage', SuccessionCoveragePlanViewSet, basename='succession-coverage')

# Skills demand forecasting
router.register('planning/skills-forecasts', SkillsDemandForecastViewSet, basename='skills-forecasts')
router.register('planning/skills-forecast-lines', SkillsDemandLineItemViewSet, basename='skills-forecast-lines')

# Hiring requisitions
router.register('planning/requisitions', HiringRequisitionViewSet, basename='hiring-requisitions')

# Reorg workflows
router.register('planning/reorg-workflows', ReorgWorkflowViewSet, basename='reorg-workflows')
router.register('planning/reorg-tasks', ReorgWorkflowTaskViewSet, basename='reorg-tasks')

urlpatterns = [
    path('', include(router.urls)),
]
