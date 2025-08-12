from rest_framework import views, status
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from rest_framework.response import Response
from .models import Invoice, PaymentTransfer, WithdrawRequest, WalletTransaction
from .serializers import InvoiceSerializer, PaymentTransferSerializer, WithdrawRequestSerializer, WalletTransactionSerializer
from authentication.permissions import IsOwnerByUser
from .utils import CustomPaymentSectionViewsets, DataEncryptDecrypt
from rest_framework.exceptions import NotFound, ValidationError, AuthenticationFailed
from authentication.models import Merchant, APIKey
from .payment import bkash
import json


class InvoiceViewSet(CustomPaymentSectionViewsets):
    queryset = Invoice.objects.none
    serializer_class = InvoiceSerializer
    model = Invoice
    lookup_field = 'invoice_payment_id'
    
    create_success_message = "Invoice Created!"
    update_success_message = "Invoice Updated!"
    delete_success_message = "Invoice Deleted!"
    not_found_message = "Invoice Object Not Found!"
    ordering_by = "-id"
    
    def get_object(self):
        try:
            query_set = self.get_queryset()
            return query_set.get(invoice_payment_id=self.kwargs.get('invoice_payment_id'))
        except self.model.DoesNotExist:
            raise NotFound({
                'status': False,
                'message': self.not_found_message
            })
    
    #-------------Created-------------------------------
    def json_encrypted(self, post_data):
        url_json = {
            "success_url": post_data.get("success_url", ""),
            "cancel_url": post_data.get("cancel_url", ""),
            "failed_url": post_data.get("failed_url", ""),
        }
        object = DataEncryptDecrypt()
        encrypt_data_json = object.encrypt_data(url_json)
        post_data['data'] = json.dumps(encrypt_data_json)
        return post_data
    
    
    def create(self, request, *args, **kwargs):
        try:
            post_data = request.data.copy()
            data = self.json_encrypted(post_data)
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(
                {
                    'status': True,
                    'message': self.create_success_message,
                    'data': serializer.data
                }, status=status.HTTP_201_CREATED
            )
        except ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}
            return Response(
                {
                    'status': False,
                    'error': error
                },status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def perform_create(self, serializer):
        merchant = self.request.user.merchant
        serializer.save(merchant=merchant)
    

class GetOnlinePayment(views.APIView):
    def get(self, request, *args, **kwargs):
        invoice_payment_id = kwargs.get('invoice_payment_id')
        if not invoice_payment_id:
            return Response({
                'status': False,
                'message': "Missing 'Invoice Payment ID' parameter"
            }, status=status.HTTP_400_BAD_REQUEST)
        try:
            invoice = Invoice.objects.get(invoice_payment_id=invoice_payment_id)
        except Invoice.DoesNotExist:
            raise NotFound("Invoice with provided Invoice Payment ID not found.")
        
        method = request.query_params.get("method")
        if method == 'bkash':
            url = reverse('get-payment-bkash', kwargs={'invoice_payment_id': str(invoice_payment_id)})
            return redirect(f"{url}?redirect=1")
        elif method == 'nagad':
            return Response(
                {
                    'message': 'Redirect Nagad Payment Gateway URL!'
                }
            )
        
        payment_methods = [
            {"method": "bkash", "name": f"<a href=f'{bkash.BKASH_CALLBACK_BASE_URL}/api/v1/invoice/{invoice_payment_id}/get-payment/bkash/'>Bkash</a>"},
            {"method": "nagad", "name": "Nagad"},
            {"method": "rocket", "name": "Rocket"},
            {"method": "bank", "name": "Bank"}
        ]
        
        return Response({
            'status': True,
            'payment_methods': payment_methods
        }, status=status.HTTP_200_OK)


class CreatePayment(views.APIView):
    def authenticate_using_api_key_and_secret(self, request):
        api_key = request.headers.get("API-KEY")
        secret_key = request.headers.get("SECRET-KEY")

        if not api_key or not secret_key:
            raise AuthenticationFailed("Missing API-KEY, SECRET-KEY, or BRAND-KEY.")

        try:
            api_key = APIKey.objects.get(api_key=api_key, secret_key=secret_key, is_active=True)
        except APIKey.DoesNotExist:
            raise AuthenticationFailed("Invalid API-KEY.")

        # if not merchant.check_secret(secret_key):
        #     raise AuthenticationFailed("Invalid SECRET-KEY.")

        return api_key.merchant
        
    def json_encrypted(self, post_data):
        url_json = {
            "success_url": post_data.get("success_url", ""),
            "cancel_url": post_data.get("cancel_url", ""),
            "failed_url": post_data.get("failed_url", ""),
        }
        object = DataEncryptDecrypt()
        encrypt_data_json = object.encrypt_data(url_json)
        post_data['data'] = json.dumps(encrypt_data_json)
        return post_data
    
    def post(self, request, *args, **kwargs):
        try:
            merchant = self.authenticate_using_api_key_and_secret(request)
            post_data = request.data.copy()
            data = self.json_encrypted(post_data)
            serializer = InvoiceSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            serializer.save(merchant=merchant)
            invoice = serializer.instance
            
            if invoice.method:
                if invoice.method.lower() == 'bkash':
                    url = reverse('get-payment-bkash', kwargs={'invoice_payment_id': str(invoice.invoice_payment_id)})
                    return redirect(f"{url}?redirect=1")
                    # return redirect(f"{url}")
                elif invoice.method.lower() == 'nagad':
                    return Response(
                        {
                            'message': 'Redirect Nagad Payment Gateway URL!'
                        }
                    )
            else:
                return redirect('get-payment', invoice_payment_id=invoice.invoice_payment_id)
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'message': str(e)
                }
            )





