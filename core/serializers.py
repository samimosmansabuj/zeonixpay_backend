from .models import Invoice, PaymentTransfer, WithdrawRequest, WalletTransaction
from authentication.models import UserPaymentMethod
from rest_framework import serializers



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
        return obj.merchant.brand_name or None
    
    def get_paymentMethod(self, obj):
        try:
            return obj.payment_method.method_type
        except:
            return None
    
    def get_paymentDetails(self, obj):
        try:
            return obj.payment_method.params
        except:
            return None


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

