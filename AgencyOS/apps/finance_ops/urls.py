from rest_framework.routers import DefaultRouter
from .views import ClientInvoiceViewSet, MarginRecordViewSet

router = DefaultRouter()
router.register("invoices", ClientInvoiceViewSet, basename="invoice")
router.register("margins", MarginRecordViewSet, basename="margin")

urlpatterns = router.urls
