import django_filters
from django_filters import rest_framework as filters
from .models import Invoice, WithdrawRequest, UserPaymentMethod, PaymentTransfer, WalletTransaction

class InvoiceFilter(filters.FilterSet):
    created_at = django_filters.IsoDateTimeFromToRangeFilter()
    customer_amount = django_filters.RangeFilter()
    class Meta:
        model = Invoice
        fields = {
            'status': ['exact', 'in'],
            'pay_status': ['exact', 'in'],
            'method': ['exact', 'in', 'icontains'],
            'payment_gateway': ['exact'],
            'customer_number': ['exact', 'icontains'],
            'invoice_payment_id': ['exact', 'icontains'],
            'transaction_id': ['exact', 'icontains'],
        }

class WithdrawRequestFilter(filters.FilterSet):
    created_at = django_filters.IsoDateTimeFromToRangeFilter()
    amount = django_filters.RangeFilter()
    class Meta:
        model = WithdrawRequest
        fields = {
            'status': ['exact', 'in'],
            'payment_method': ['exact'],
            'trx_id': ['exact', 'icontains'],
            'trx_uuid': ['exact'],
        }

class PaymentTransferFilter(filters.FilterSet):
    created_at = django_filters.IsoDateTimeFromToRangeFilter()
    amount = django_filters.RangeFilter()
    class Meta:
        model = PaymentTransfer
        fields = {
            'status': ['exact', 'in'],
            'payment_method': ['exact', 'in'],
            'confirm_by': ['exact'],
            'trx_id': ['exact', 'icontains'],
            'trx_uuid': ['exact'],
            'receiver_number': ['exact', 'icontains'],
        }

class UserPaymentMethodFilter(filters.FilterSet):
    class Meta:
        model = UserPaymentMethod
        fields = {
            'status': ['exact', 'in'],
            'method_type': ['exact', 'in'],
            'is_primary': ['exact'],
            'method_type': ['exact', 'icontains'],
        }


class WalletTransactionFilter(filters.FilterSet):
    created_at = django_filters.IsoDateTimeFromToRangeFilter()
    amount = django_filters.RangeFilter()
    status = django_filters.ChoiceFilter(choices=WalletTransaction.STATUS)
    tran_type = django_filters.ChoiceFilter(choices=WalletTransaction.TRAN_TYPE)
    # source = django_filters.ChoiceFilter(choices=(('payout', 'Payout'), ('withdraw', 'Withdraw'), ('deposit', 'Deposit')))
    source = django_filters.CharFilter(method='filter_source')
    class Meta:
        model = WalletTransaction
        fields = {
            'status': ['exact', 'in'],
            'tran_type': ['exact', 'in'],
            'method': ['exact', 'in', 'icontains'],
            'trx_id': ['exact', 'in', 'icontains'],
        }

    def filter_source(self, queryset, name, value):
        if value:
            if value.lower() == 'payout':
                return queryset.filter(content_type__model='paymenttransfer')
            elif value.lower() == 'withdraw':
                return queryset.filter(content_type__model='withdrawrequest')
            elif value.lower() == 'deposit':
                return queryset.filter(content_type__model='invoice')
        return queryset

