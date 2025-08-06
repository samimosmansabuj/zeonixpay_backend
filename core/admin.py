from django.contrib import admin
from .models import Invoice, PaymentTransfer, WithdrawRequest, WalletTransaction
from authentication.models import CustomUser, UserBrand


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('payment_uid', 'user', 'brand_id', 'customer_name', 'customer_number', 'customer_amount', 'status', 'pay_status')
    list_filter = ('status', 'pay_status', 'created_at')
    search_fields = ('payment_uid', 'customer_name', 'user__username')


@admin.register(PaymentTransfer)
class PaymentTransferAdmin(admin.ModelAdmin):
    list_display = ('transfer_id', 'user', 'brand', 'receiver_name', 'receiver_number', 'amount', 'payment_method', 'status')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('transfer_id', 'user__username', 'receiver_name', 'receiver_number')


@admin.register(WithdrawRequest)
class WithdrawRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'wallet', 'amount', 'charge', 'net_amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'wallet__user__username')


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'wallet', 'amount', 'method', 'status', 'tran_type', 'created_at', 'trx_id')
    list_filter = ('status', 'tran_type', 'created_at')
    search_fields = ('trx_id', 'wallet__user__username', 'brand__brand_name')

