"""Payroll URL configuration."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import PayslipPDFView, BankFileView, EPFETFReportView, APYTCalculationView

router = DefaultRouter()
router.register(r'salary-structures', views.SalaryStructureViewSet, basename='salary-structure')
router.register(r'compensations', views.EmployeeCompensationViewSet, basename='compensation')
router.register(r'payroll/runs', views.PayrollRunViewSet, basename='payroll-run')
router.register(r'payroll/entries', views.PayrollEntryViewSet, basename='payroll-entry')
router.register(r'loans', views.LoanRecordViewSet, basename='loan')
# Feature 5 upgrades
router.register(r'off-cycle-comp-changes', views.OffCycleCompChangeViewSet, basename='off-cycle-comp-change')
router.register(r'retro-pay-entries', views.RetroPayEntryViewSet, basename='retro-pay-entry')
router.register(r'payroll-anomalies', views.PayrollAnomalyViewSet, basename='payroll-anomaly')
router.register(r'pay-compression-alerts', views.PayCompressionAlertViewSet, basename='pay-compression-alert')
router.register(r'comp-benchmark-imports', views.CompBenchmarkImportViewSet, basename='comp-benchmark-import')
router.register(r'salary-progressions', views.SalaryProgressionViewSet, basename='salary-progression')
router.register(r'reward-simulations', views.RewardSimulationViewSet, basename='reward-simulation')
router.register(r'budget-guardrails', views.BudgetGuardrailViewSet, basename='budget-guardrail')
router.register(r'variable-pay-plans', views.VariablePayPlanViewSet, basename='variable-pay-plan')
router.register(r'variable-pay-entries', views.VariablePayEntryViewSet, basename='variable-pay-entry')

urlpatterns = [
    path('', include(router.urls)),
    path('entries/<uuid:pk>/payslip/', PayslipPDFView.as_view(), name='payslip-pdf'),
    path('runs/<uuid:pk>/bank-file/', BankFileView.as_view(), name='bank-file'),
    path('runs/<uuid:pk>/epf-etf-report/', EPFETFReportView.as_view(), name='epf-etf-report'),
    path('apit-calculate/', APYTCalculationView.as_view(), name='apit-calculate'),
]
