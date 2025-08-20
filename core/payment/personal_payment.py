from django.shortcuts import render, HttpResponse, get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import PersonalAgentPaymentProcessSerializer
from rest_framework import status, views
from core.models import Invoice
from rest_framework.exceptions import ValidationError
from authentication.models import BasePaymentGateWay
from django.core.cache import cache
from authentication.models import StorePaymentMessage





class BkashPersonalAgentPaymentView(views.APIView):
    serializer_class = PersonalAgentPaymentProcessSerializer
    
    def post(self, request, *args, **kwargs):
        payment_method = self.request.query_params.get('method')
        if not payment_method:
            raise ValidationError({"payment_method": "Payment method (bkash-personal or bkash-agent) not provided!"})
        
        try:
            invoice = self.get_invoice()
            serializer = PersonalAgentPaymentProcessSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            transaction_Id = serializer.validated_data.get('transaction_Id')
            
            if payment_method == 'bkash-agent':
                verify = self.verify_cashout_payment(transaction_Id, invoice)
            elif payment_method == 'bkash-personal':
                verify = self.verify_send_money_payment(transaction_Id, invoice)
            else:
                return Response(
                    {
                        'status': False,
                        'message': 'Invalid Payment Method!'
                    }, status=status.HTTP_400_BAD_REQUEST
                )
            
            if verify:
                invoice.pay_status = "paid"
                invoice.transaction_id = transaction_Id
                if not invoice.method:
                    invoice.method = payment_method
                invoice.save()
                
                client_callback_url = invoice.data
                redirect_url = f"{client_callback_url['success_url' or 'success']}?transactionStatus=success"
                
                return Response(
                    {
                        'status': True,
                        'message': "Payment has been successfully completed.",
                        'callback_url': redirect_url
                    }, status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {
                        'status': False,
                        'message': 'Payment not Verified!'
                    }, status=status.HTTP_400_BAD_REQUEST
                )
        except ValidationError as e:
            try:
                error_messages = []
                for field, errors in e.detail.items():
                    for error in errors:
                        error_messages.append(error)
            except:
                error_messages = e.detail
            return Response(
                {
                    'status': False,
                    'message': ''.join(error_messages)
                }, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'message': f"An unexpected error occurred: {str(e)}"
                }, status=status.HTTP_400_BAD_REQUEST
            )
    
    def get(self, request, *args, **kwargs):
        payment_method = self.request.query_params.get('method')
        if not payment_method:
            raise ValidationError({"payment_method": "Payment method (bkash-personal or bkash-agent) not provided!"})
        invoice = self.get_invoice()
        
        if payment_method == 'bkash-agent':
            payment_gateway = self.get_next_payment_gateway_bkash_agent()
            invoice.payment_gateway = payment_gateway
            invoice.method_payment_id = None
            invoice.save()
            return Response(
                {
                    'status': True,
                    "data": {
                        "Method": f"{payment_method.title()}",
                        "Cash-out Number": f"{payment_gateway.details_json['phone_number'] if payment_gateway is not None else "Bkash Cashout Method Not Available Right Now, Try Another Method!"}",
                        "Message": f"Submit Your Phone Number & Transaction ID. Cashout Amount is {invoice.customer_amount}"
                    }
                    # 'invoice': InvoiceSerializer(invoice).data
                }, status=status.HTTP_200_OK
            )
        elif payment_method == 'bkash-personal':
            payment_gateway = self.get_next_payment_gateway_bkash_personal()
            invoice.payment_gateway = payment_gateway
            invoice.method_payment_id = None
            invoice.save()
            return Response(
                {
                    'status': True,
                    "data": {
                        "Method": f"{payment_method.title()}",
                        "Cash-out Number": f"{payment_gateway.details_json['phone_number'] if payment_gateway is not None else "Bkash Send Money Method Not Available Right Now, Try Another Method!"}",
                        "Message": f"Submit Your Phone Number & Transaction ID. Cashout Amount is {invoice.customer_amount}"
                    }
                    # 'invoice': InvoiceSerializer(invoice).data
                }, status=status.HTTP_200_OK
            )
        else:
            return Response(
                {
                    'status': False,
                    'message': "Invalid method select! use (bkash-personal or bkash-agent)"
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
    
    def get_next_payment_gateway_bkash_personal(self):
        gateways = BasePaymentGateWay.objects.filter(method="bkash-personal").order_by('id')
        if not gateways.exists():
            return None
        
        last_id = cache.get("last_used_bkash_personal_id")
        if last_id:
            next_gateway = gateways.filter(id__gt=last_id).first()
            if not next_gateway:
                next_gateway = gateways.first()
        else:
            next_gateway = gateways.first()
        cache.set("last_used_bkash_personal_id", next_gateway.id, None)
        return next_gateway
    
    def get_next_payment_gateway_bkash_agent(self):
        gateways = BasePaymentGateWay.objects.filter(method="bkash-agent").order_by('id')
        if not gateways.exists():
            return None
        
        last_id = cache.get("last_used_bkash_agent_id")
        if last_id:
            next_gateway = gateways.filter(id__gt=last_id).first()
            if not next_gateway:
                next_gateway = gateways.first()
        else:
            next_gateway = gateways.first()
        cache.set("last_used_bkash_agent_id", next_gateway.id, None)
        return next_gateway

    def verify_send_money_payment(self, transaction_Id, invoice):
        if StorePaymentMessage.objects.filter(message_amount=invoice.customer_amount, trx_id=transaction_Id).exists():
            bkash_payment_messages = get_object_or_404(StorePaymentMessage, message_amount=invoice.customer_amount, trx_id=transaction_Id)
            if bkash_payment_messages.is_verified == True:
                raise ValidationError("With this Transaction ID and Amount is already verified, Try again!")
            else:
                bkash_payment_messages.is_verified = True
                bkash_payment_messages.save()
                return True
        else:
            raise ValidationError("Not Found Trx_ID with your Transaction ID and Amount!")
    
    def verify_cashout_payment(self, transaction_Id, invoice):
        if StorePaymentMessage.objects.filter(message_amount=invoice.customer_amount, trx_id=transaction_Id).exists():
            bkash_payment_messages = get_object_or_404(StorePaymentMessage, message_amount=invoice.customer_amount, trx_id=transaction_Id)
            if bkash_payment_messages.is_verified == True:
                raise ValidationError("With this Transaction ID and Amount is already verified, Try again!")
            else:
                bkash_payment_messages.is_verified = True
                bkash_payment_messages.save()
                return True
        else:
            raise ValidationError("Not Found Trx_ID with your Transaction ID!")




class NagadPersonalAgentPaymentView(views.APIView):
    serializer_class = PersonalAgentPaymentProcessSerializer
    
    def post(self, request, *args, **kwargs):
        payment_method = self.request.query_params.get('method')
        if not payment_method:
            raise ValidationError({"payment_method": "Payment method (nagad-personal or nagad-agent) not provided!"})
        
        try:
            invoice = self.get_invoice()
            serializer = PersonalAgentPaymentProcessSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            transaction_Id = serializer.validated_data.get('transaction_Id')
            
            if payment_method == 'nagad-agent':
                verify = self.verify_cashout_payment(transaction_Id, invoice)
            elif payment_method == 'nagad-personal':
                verify = self.verify_send_money_payment(transaction_Id, invoice)
            else:
                return Response(
                    {
                        'status': False,
                        'message': 'Worng Payment method!'
                    }, status=status.HTTP_400_BAD_REQUEST
                )
            
            if verify:
                invoice.pay_status = "paid"
                invoice.transaction_id = transaction_Id
                if not invoice.method:
                    invoice.method = payment_method
                invoice.save()
                
                client_callback_url = invoice.data
                redirect_url = f"{client_callback_url['success_url' or 'success']}?transactionStatus=success"
                
                return Response(
                    {
                        'status': True,
                        'message': "Payment has been successfully completed.",
                        'callback_url': redirect_url
                    }, status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {
                        'status': False,
                        'message': 'Payment not Verified!'
                    }, status=status.HTTP_400_BAD_REQUEST
                )
        
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'message': str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )
    
    def get(self, request, *args, **kwargs):
        payment_method = self.request.query_params.get('method')
        if not payment_method:
            raise ValidationError({"payment_method": "Payment method (nagad-personal or nagad-agent) not provided!"})
        invoice = self.get_invoice()

        if payment_method == 'nagad-agent':
            payment_gateway = self.get_next_payment_gateway_nagad_agent()
            invoice.payment_gateway = payment_gateway
            invoice.method_payment_id = None
            invoice.save()
            return Response(
                {
                    "status": True,
                    "data": {
                        "Method": f"{payment_method.title()}",
                        "Cash-out Number": f"{payment_gateway.details_json['phone_number'] if payment_gateway is not None else "Nagad Cashout Method Not Available Right Now, Try Another Method!"}",
                        "Message": f"Submit Your Phone Number & Transaction ID. Cashout Amount is {invoice.customer_amount}"
                    }
                }, status=status.HTTP_200_OK
            )
        elif payment_method == 'nagad-personal':
            payment_gateway = self.get_next_payment_gateway_nagad_personal()
            invoice.payment_gateway = payment_gateway
            invoice.method_payment_id = None
            invoice.save()
            return Response(
                {
                    "status": True,
                    "data": {
                        "Method": f"{payment_method.title()}",
                        "Send Money Number": f"{payment_gateway.details_json['phone_number'] if payment_gateway is not None else "Nagad Send Money Method Not Available Right Now, Try Another Method!"}",
                        "Message": f"Submit Your Phone Number & Transaction ID. Send Money Amount is {invoice.customer_amount}"
                    }
                }, status=status.HTTP_200_OK
            )
        else:
            return Response(
                {
                    'status': False,
                    'message': "Invalid method select!"
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
    
    def get_next_payment_gateway_nagad_personal(self):
        gateways = BasePaymentGateWay.objects.filter(method="nagad-personal").order_by('id')
        if not gateways.exists():
            return None
        
        last_id = cache.get("last_used_nagad_personal_id")
        if last_id:
            next_gateway = gateways.filter(id__gt=last_id).first()
            if not next_gateway:
                next_gateway = gateways.first()
        else:
            next_gateway = gateways.first()
        cache.set("last_used_nagad_personal_id", next_gateway.id, None)
        return next_gateway
    
    def get_next_payment_gateway_nagad_agent(self):
        gateways = BasePaymentGateWay.objects.filter(method="nagad-agent").order_by('id')
        if not gateways.exists():
            return None
        
        last_id = cache.get("last_used_nagad_agent_id")
        if last_id:
            next_gateway = gateways.filter(id__gt=last_id).first()
            if not next_gateway:
                next_gateway = gateways.first()
        else:
            next_gateway = gateways.first()
        cache.set("last_used_nagad_agent_id", next_gateway.id, None)
        return next_gateway

    def verify_send_money_payment(self, transaction_Id, invoice):
        return True
    
    def verify_cashout_payment(self, transaction_Id, invoice):
        return True




class RocketPersonalAgentPaymentView(views.APIView):
    serializer_class = PersonalAgentPaymentProcessSerializer
    
    def post(self, request, *args, **kwargs):
        payment_method = self.request.query_params.get('method')
        if not payment_method:
            raise ValidationError({"payment_method": "Payment method (nagad-personal or nagad-agent) not provided!"})
        
        try:
            invoice = self.get_invoice()
            serializer = PersonalAgentPaymentProcessSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            transaction_Id = serializer.validated_data.get('transaction_Id')
            
            if payment_method == 'nagad-agent':
                verify = self.verify_cashout_payment(transaction_Id, invoice)
            elif payment_method == 'nagad-personal':
                verify = self.verify_send_money_payment(transaction_Id, invoice)
            else:
                return Response(
                    {
                        'status': False,
                        'message': 'Worng Payment method!'
                    }, status=status.HTTP_400_BAD_REQUEST
                )
            
            if verify:
                invoice.pay_status = "paid"
                invoice.transaction_id = transaction_Id
                if not invoice.method:
                    invoice.method = payment_method
                invoice.save()
                
                client_callback_url = invoice.data
                redirect_url = f"{client_callback_url['success_url' or 'success']}?transactionStatus=success"
                
                return Response(
                    {
                        'status': True,
                        'message': "Payment has been successfully completed.",
                        'callback_url': redirect_url
                    }, status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {
                        'status': False,
                        'message': 'Payment not Verified!'
                    }, status=status.HTTP_400_BAD_REQUEST
                )
        
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'message': str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )
    
    def get(self, request, *args, **kwargs):
        payment_method = self.request.query_params.get('method')
        if not payment_method:
            raise ValidationError({"payment_method": "Payment method (rocket-personal or rocket-agent) not provided!"})
        invoice = self.get_invoice()

        if payment_method == 'rocket-agent':
            payment_gateway = self.get_next_payment_gateway_rocket_agent()
            invoice.payment_gateway = payment_gateway
            invoice.method_payment_id = None
            invoice.save()
            return Response(
                {
                    "status": True,
                    "data": {
                        "Method": f"{payment_method.title()}",
                        "Cash-out Number": f"{payment_gateway.details_json['phone_number'] if payment_gateway is not None else "Rocket Cashout Method Not Available Right Now, Try Another Method!"}",
                        "Message": f"Submit Your Phone Number & Transaction ID. Cashout Amount is {invoice.customer_amount}"
                    }
                    # 'invoice': InvoiceSerializer(invoice).data
                }, status=status.HTTP_200_OK
            )
        elif payment_method == 'rocket-personal':
            payment_gateway = self.get_next_payment_gateway_rocket_personal()
            invoice.payment_gateway = payment_gateway
            invoice.method_payment_id = None
            invoice.save()
            return Response(
                {
                    "status": True,
                    "data": {
                        "Method": f"{payment_method.title()}",
                        "Send Money Number": f"{payment_gateway.details_json['phone_number'] if payment_gateway is not None else "Rocket Send Money Method Not Available Right Now, Try Another Method!"}",
                        "Message": f"Submit Your Phone Number & Transaction ID. Send Money Amount is {invoice.customer_amount}"
                    }
                }, status=status.HTTP_200_OK
            )
        else:
            return Response(
                {
                    'status': False,
                    'message': "Invalid method select!"
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
    
    def get_next_payment_gateway_rocket_personal(self):
        gateways = BasePaymentGateWay.objects.filter(method="rocket-personal").order_by('id')
        if not gateways.exists():
            return None
        
        last_id = cache.get("last_used_rocket_personal_id")
        if last_id:
            next_gateway = gateways.filter(id__gt=last_id).first()
            if not next_gateway:
                next_gateway = gateways.first()
        else:
            next_gateway = gateways.first()
        cache.set("last_used_rocket_personal_id", next_gateway.id, None)
        return next_gateway
    
    def get_next_payment_gateway_rocket_agent(self):
        gateways = BasePaymentGateWay.objects.filter(method="rocket-agent").order_by('id')
        if not gateways.exists():
            return None
        
        last_id = cache.get("last_used_rocket_agent_id")
        if last_id:
            next_gateway = gateways.filter(id__gt=last_id).first()
            if not next_gateway:
                next_gateway = gateways.first()
        else:
            next_gateway = gateways.first()
        cache.set("last_used_rocket_agent_id", next_gateway.id, None)
        return next_gateway

    def verify_send_money_payment(self, transaction_Id, invoice):
        return True
    
    def verify_cashout_payment(self, transaction_Id, invoice):
        return True



