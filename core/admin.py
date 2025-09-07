from django.contrib.contenttypes.models import ContentType
from django.utils.html import format_html
from django.contrib import admin


from .models import (
    Invoice,
    PaymentTransfer,
    WithdrawRequest,
    WalletTransaction,
)


# -------------------- Invoice --------------------
@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_payment_id",
        "merchant",
        "customer_name",
        "customer_number",
        "customer_amount",
        "method",
        "status",
        "pay_status",
        "transaction_id",
        "invoice_trxn",
        "created_at",
    )
    list_filter = ("status", "pay_status", "method", "created_at")
    search_fields = (
        "invoice_payment_id",
        "invoice_trxn",
        "transaction_id",
        "merchant__brand_name",
        "merchant__user__username",
        "customer_name",
        "customer_number",
        "customer_email",
        "customer_order_id",
    )
    autocomplete_fields = ("merchant",)
    readonly_fields = ("invoice_payment_id", "invoice_trxn", "created_at")


# -------------------- Payment Transfer --------------------
@admin.register(PaymentTransfer)
class PaymentTransferAdmin(admin.ModelAdmin):
    list_display = (
        "trx_uuid",
        "trx_id",
        "merchant",
        "confirm_by",
        "receiver_name",
        "receiver_number",
        "amount",
        "payment_method",
        "status",
        "created_at",
    )
    list_filter = ("payment_method", "status", "created_at")
    search_fields = (
        "trx_uuid",
        "trx_id",
        "merchant__brand_name",
        "merchant__user__username",
        "receiver_name",
        "receiver_number",
    )
    autocomplete_fields = ("merchant",)
    readonly_fields = ("trx_uuid", "created_at")


# -------------------- Withdraw Request --------------------
@admin.register(WithdrawRequest)
class WithdrawRequestAdmin(admin.ModelAdmin):
    list_display = (
        "trx_uuid",
        "trx_id",
        "merchant",
        "amount",
        "status",
        "trx_id",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "created_at", "updated_at")
    search_fields = (
        "merchant__brand_name",
        "merchant__user__username",
        "trx_uuid",
        "trx_id",
    )
    autocomplete_fields = ("merchant",)
    readonly_fields = ("created_at", "updated_at")


# -------------------- Wallet Transaction --------------------
@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "trx_uuid",
        "trx_id",
        "merchant",
        "wallet",
        "amount",
        "fee",
        "method",
        "status",
        "tran_type",
        "created_at",
        "service_repr",
    )
    list_filter = ("status", "tran_type", "created_at", "method")
    search_fields = (
        "trx_uuid",
        "trx_id",
        "merchant__brand_name",
        "merchant__user__username",
        "wallet__wallet_id",
    )
    autocomplete_fields = ("merchant", "wallet")
    readonly_fields = (
        "trx_uuid",
        "created_at",
        "content_type",
        "object_id",
        "service_readonly",
    )
    fields = (
        "merchant",
        "wallet",
        "ip_address",
        "amount",
        "fee",
        "net_amount",
        "previous_balance",
        "current_balance",
        "method",
        "status",
        "tran_type",
        "trx_uuid",
        "trx_id",
        "created_at",
        # Show Generic FK in a safe/read-only way
        "service_readonly",
        "content_type",
        "object_id",
    )

    def service_repr(self, obj):
        if not obj.content_type or not obj.object_id:
            return "-"
        return f"{obj.content_type.app_label}.{obj.content_type.model}#{obj.object_id}"

    service_repr.short_description = "Service"

    def service_readonly(self, obj):
        if not obj or not obj.content_type or not obj.object_id:
            return "-"
        return format_html(
            "<code>{}.{}</code> — ID: <b>{}</b>",
            obj.content_type.app_label,
            obj.content_type.model,
            obj.object_id,
        )

    service_readonly.short_description = "Linked service (Generic FK)"


