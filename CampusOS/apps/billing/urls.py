from django.urls import path
from . import views

urlpatterns = [
    path("plans/", views.CampusPlanListView.as_view(), name="campus-plans"),
    path("subscription/", views.CampusSubscriptionView.as_view(), name="campus-subscription"),
    path("invoices/", views.CampusInvoiceListView.as_view(), name="billing-invoices"),
    path("events/", views.CampusBillingEventListView.as_view(), name="billing-events"),
    path("my-plan/", views.MyStudentPlanView.as_view(), name="my-student-plan"),
]
