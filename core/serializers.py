from rest_framework import serializers
from .models import Invoice, PaymentTransfer, WithdrawRequest, WalletTransaction
from authentication.models import CustomUser, MerchantWallet


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = '__all__'

class CreatePaymentSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Invoice
        fields = '__all__'


class PaymentTransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransfer
        fields = '__all__'


class WithdrawRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawRequest
        fields = '__all__'


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = '__all__'
