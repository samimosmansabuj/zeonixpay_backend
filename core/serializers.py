from rest_framework import serializers
from .models import Invoice, PaymentTransfer, WithdrawRequest, WalletTransaction
from authentication.models import UserPaymentMethod


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = '__all__'

class CreatePaymentSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Invoice
        fields = '__all__'


class PaymentTransferSerializer(serializers.ModelSerializer):
    store_name = serializers.SerializerMethodField()
    class Meta:
        model = PaymentTransfer
        fields = '__all__'
    
    def get_store_name(self, obj):
        return obj.merchant.brand_name


class WithdrawRequestSerializer(serializers.ModelSerializer):
    store_name = serializers.SerializerMethodField()
    paymentMethod = serializers.SerializerMethodField()
    paymentDetails = serializers.SerializerMethodField()
    class Meta:
        model = WithdrawRequest
        fields = '__all__'
    
    def get_store_name(self, obj):
        return obj.merchant.brand_name
    
    def get_paymentMethod(self, obj):
        return obj.payment_method.method_type
    
    def get_paymentDetails(self, obj):
        return obj.payment_method.params


class WalletTransactionSerializer(serializers.ModelSerializer):
    store_name = serializers.SerializerMethodField()
    class Meta:
        model = WalletTransaction
        fields = '__all__'
    
    def get_store_name(self, obj):
        return obj.merchant.brand_name
    


class UserPaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPaymentMethod
        fields = '__all__'

