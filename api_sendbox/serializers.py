from rest_framework import serializers
from .models import SendBoxInvoice, SendBoxPaymentTransfer

class CreatePaymentSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = SendBoxInvoice
        fields = '__all__'


class PaymentTransferSerializer(serializers.ModelSerializer):
    store_name = serializers.SerializerMethodField()
    class Meta:
        model = SendBoxPaymentTransfer
        fields = '__all__'
    
    def get_store_name(self, obj):
        return obj.merchant.brand_name

