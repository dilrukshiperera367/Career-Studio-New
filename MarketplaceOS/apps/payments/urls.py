from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PaymentViewSet, PayoutViewSet, PromoCodeViewSet,
    WalletViewSet, InvoiceViewSet, RefundRequestViewSet,
)

router = DefaultRouter()
router.register("payments", PaymentViewSet, basename="payment")
router.register("payouts", PayoutViewSet, basename="payout")
router.register("promo-codes", PromoCodeViewSet, basename="promo-code")
router.register("wallet", WalletViewSet, basename="wallet")
router.register("invoices", InvoiceViewSet, basename="invoice")
router.register("refund-requests", RefundRequestViewSet, basename="refund-request")

urlpatterns = [path("", include(router.urls))]
