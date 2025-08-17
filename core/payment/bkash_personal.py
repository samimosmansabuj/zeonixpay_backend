from django.shortcuts import render, HttpResponse, get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import PersonalAgentPaymentProcessSerializer
from rest_framework import status, views
from core.models import Invoice
from core.serializers import InvoiceSerializer
from rest_framework.exceptions import ValidationError
from authentication.models import BasePaymentGateWay
from django.db.models import Q
from django.core.cache import cache





class BkashPersonalAgentPaymentView(views.APIView):
    serializer_class = PersonalAgentPaymentProcessSerializer
    
    def post(self, request, *args, **kwargs):
        try:
            invoice = self.get_invoice()
            serializer = PersonalAgentPaymentProcessSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            phone_number = serializer.validated_data.get('phone_number')
            transaction_Id = serializer.validated_data.get('transaction_Id')

            verify = self.verify_send_money_payment(phone_number, transaction_Id, invoice.customer_amount)
            if verify:
                return Response(
                    {
                        'status': True,
                        'message': 'Payment Verified!'
                    }
                )
            else:
                return Response(
                    {
                        'status': False,
                        'message': 'Payment not Verified!'
                    }
                )
        
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'message': str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )
    
    def get(self, request, *args, **kwargs):
        invoice = self.get_invoice()
        payment_gateway = self.get_next_payment_gateway()
        
        return Response(
            {
                'status': True,
                'message': f"""
                Send Money: {payment_gateway.details_json['phone_number']}
                Submit Your Phone Number & Transaction ID. Your Amount is {invoice.customer_amount}
                """,
                # 'invoice': InvoiceSerializer(invoice).data
            }, status=status.HTTP_200_OK
        )
    
    
    def get_invoice(self):
        invoice_payment_id = self.request.query_params.get('invoice_payment_id')
        if not invoice_payment_id:
            raise ValidationError({"invoice_payment_id": "Invoice Payment ID not provided!"})

        invoice = get_object_or_404(Invoice, invoice_payment_id=invoice_payment_id)

        if invoice.pay_status.lower() == 'paid':
            raise ValidationError({"pay_status": f"This invoice is already {invoice.pay_status} and cannot be edited."})
        elif invoice.pay_status.lower() in ['failed', 'cancelled']:
            raise ValidationError({"pay_status": f"This invoice is already {invoice.pay_status} and cannot be edited."})

        return invoice
    
    def get_next_payment_gateway(self):
        gateways = BasePaymentGateWay.objects.filter(method="bkash-personal").order_by('id')
        if not gateways.exists():
            return None
        
        last_id = cache.get("last_used_bkash_id")
        if last_id:
            next_gateway = gateways.filter(id__gt=last_id).first()
            if not next_gateway:
                next_gateway = gateways.first()
        else:
            next_gateway = gateways.first()
        cache.set("last_used_bkash_id", next_gateway.id, None)
        return next_gateway

    def verify_send_money_payment(self):
        return True
    

