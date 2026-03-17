from django.contrib import admin
from .models import Payment, Payout, PromoCode, Wallet, Invoice, RefundRequest, TaxDocument


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["reference", "payer", "payment_type", "net_amount_lkr", "status", "created_at"]
    list_filter = ["status", "payment_type", "payment_method"]
    search_fields = ["reference", "payer__email"]
    readonly_fields = ["id", "reference", "created_at", "updated_at"]
    date_hierarchy = "created_at"


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ["reference", "provider", "net_amount_lkr", "status", "period_start", "period_end"]
    list_filter = ["status"]
    search_fields = ["reference", "provider__display_name"]


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ["code", "discount_type", "discount_value", "total_used", "is_active", "valid_from", "valid_to"]
    list_filter = ["discount_type", "scope", "is_active"]
    search_fields = ["code"]


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ["user", "balance_lkr", "currency", "is_active"]
    search_fields = ["user__email"]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ["invoice_number", "issued_to", "total_lkr", "status", "issued_at"]
    list_filter = ["status"]
    search_fields = ["invoice_number", "issued_to__email"]


@admin.register(RefundRequest)
class RefundRequestAdmin(admin.ModelAdmin):
    list_display = ["payment", "requested_by", "requested_amount_lkr", "status", "created_at"]
    list_filter = ["status"]


@admin.register(TaxDocument)
class TaxDocumentAdmin(admin.ModelAdmin):
    list_display = ["provider", "doc_type", "is_verified", "submitted_at"]
    list_filter = ["doc_type", "is_verified"]
