from rest_framework import serializers

class PersonalAgentPaymentProcessSerializer(serializers.Serializer):
    transaction_Id = serializers.CharField(required=True, error_messages={
        'required': 'Transaction ID is required.',
        'blank': 'Transaction ID cannot be blank.'
    })
    
    
    
    


