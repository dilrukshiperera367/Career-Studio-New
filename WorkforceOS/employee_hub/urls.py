from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    EmployeeProfileCompletionViewSet,
    EmployeeQuickLinkViewSet,
    EmployeeHubWidgetViewSet,
    EmployeeFeedItemViewSet,
    ProfileChangeRequestViewSet,
    BankDetailViewSet,
    TaxDeclarationViewSet,
    EmergencyContactViewSet,
    DependentViewSet,
    PayslipAccessViewSet,
    TaxLetterRequestViewSet,
    ShiftSwapRequestViewSet,
    OvertimeRequestViewSet,
    BenefitsEnrollmentViewSet,
    LifeEventChangeViewSet,
    EmployeeDocumentVaultViewSet,
    PolicyAcknowledgementViewSet,
    TrainingEnrollmentViewSet,
    CertificationRecordViewSet,
    GoalCommentViewSet,
    InternalJobApplicationViewSet,
    EmployeeCaseViewSet,
    CaseCommentViewSet,
    AssetRequestViewSet,
    EmployeeLanguagePreferenceViewSet,
    AccessibilityPreferenceViewSet,
    SelfServiceRequestViewSet,
)

router = DefaultRouter()

# 1. Home dashboard
router.register(r'employee/profile-completion', EmployeeProfileCompletionViewSet, basename='employee-profile-completion')
router.register(r'employee/quick-links', EmployeeQuickLinkViewSet, basename='employee-quick-links')
router.register(r'employee/widgets', EmployeeHubWidgetViewSet, basename='employee-hub-widgets')
router.register(r'employee/feed', EmployeeFeedItemViewSet, basename='employee-feed')

# 2. Personal profile updates
router.register(r'employee/profile-changes', ProfileChangeRequestViewSet, basename='profile-change-requests')

# 3. Bank / tax / emergency / dependents
router.register(r'employee/bank-details', BankDetailViewSet, basename='employee-bank-details')
router.register(r'employee/tax-declarations', TaxDeclarationViewSet, basename='employee-tax-declarations')
router.register(r'employee/emergency-contacts', EmergencyContactViewSet, basename='employee-emergency-contacts')
router.register(r'employee/dependents', DependentViewSet, basename='employee-dependents')

# 4. Payslips / tax letters / salary history
router.register(r'employee/payslip-access', PayslipAccessViewSet, basename='employee-payslip-access')
router.register(r'employee/tax-letters', TaxLetterRequestViewSet, basename='employee-tax-letters')

# 5. Shift self-service
router.register(r'employee/shift-swaps', ShiftSwapRequestViewSet, basename='employee-shift-swaps')

# 6. Overtime
router.register(r'employee/overtime', OvertimeRequestViewSet, basename='employee-overtime')

# 7. Benefits enrollment / life events
router.register(r'employee/benefits-enrollments', BenefitsEnrollmentViewSet, basename='employee-benefits-enrollments')
router.register(r'employee/life-events', LifeEventChangeViewSet, basename='employee-life-events')

# 8. Document vault
router.register(r'employee/document-vault', EmployeeDocumentVaultViewSet, basename='employee-document-vault')

# 9. Policy acknowledgement center
router.register(r'employee/policy-acknowledgements', PolicyAcknowledgementViewSet, basename='employee-policy-acks')

# 10. Training and certification center
router.register(r'employee/training', TrainingEnrollmentViewSet, basename='employee-training')
router.register(r'employee/certifications', CertificationRecordViewSet, basename='employee-certifications')

# 11. Goals / reviews / feedback
router.register(r'employee/goal-comments', GoalCommentViewSet, basename='employee-goal-comments')

# 12. Internal jobs and gigs
router.register(r'employee/internal-applications', InternalJobApplicationViewSet, basename='employee-internal-applications')

# 13. Helpdesk / cases
router.register(r'employee/cases', EmployeeCaseViewSet, basename='employee-cases')
router.register(r'employee/case-comments', CaseCommentViewSet, basename='employee-case-comments')

# 14. Asset requests
router.register(r'employee/asset-requests', AssetRequestViewSet, basename='employee-asset-requests')

# 15. Language preferences
router.register(r'employee/language-preferences', EmployeeLanguagePreferenceViewSet, basename='employee-language-prefs')

# 16. Accessibility preferences (WCAG 2.2)
router.register(r'employee/accessibility', AccessibilityPreferenceViewSet, basename='employee-accessibility')

# Legacy
router.register(r'employee/service-requests', SelfServiceRequestViewSet, basename='service-requests')

urlpatterns = [
    path('', include(router.urls)),
]
