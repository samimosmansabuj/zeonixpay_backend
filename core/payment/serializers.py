from rest_framework import serializers

class PersonalAgentPaymentProcessSerializer(serializers.Serializer):
    # amount = serializers.DecimalField(decimal_places=2, max_digits=9)
    # phone_number = serializers.CharField()
    transaction_Id = serializers.CharField()
    # invoice_payment_id = serializers.CharField()
    
    


