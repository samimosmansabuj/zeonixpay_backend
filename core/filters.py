import django_filters
from django_filters import rest_framework as filters
from .models import Invoice, WithdrawRequest, UserPaymentMethod, PaymentTransfer

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
