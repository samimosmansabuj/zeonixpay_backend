from rest_framework import views, status
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from rest_framework.response import Response
from .models import Invoice, PaymentTransfer, WithdrawRequest, WalletTransaction
from .serializers import InvoiceSerializer, PaymentTransferSerializer, WithdrawRequestSerializer, WalletTransactionSerializer
from authentication.permissions import IsOwnerByUser
from .utils import CustomPaymentSectionViewsets, DataEncryptDecrypt
from rest_framework.exceptions import NotFound, ValidationError, AuthenticationFailed
from authentication.models import Merchant
from .payment import bkash
import json


class InvoiceViewSet(CustomPaymentSectionViewsets):
    queryset = Invoice.objects.none
    serializer_class = InvoiceSerializer
    model = Invoice
    lookup_field = 'payment_uid'
    
    create_success_message = "Invoice Created!"
    update_success_message = "Invoice Updated!"
    delete_success_message = "Invoice Deleted!"
    not_found_message = "Invoice Object Not Found!"
    ordering_by = "-id"
    
    def get_object(self):
        try:
            query_set = self.get_queryset()
            return query_set.get(payment_uid=self.kwargs.get('payment_uid'))
        except self.model.DoesNotExist:
            raise NotFound({
                'status': False,
                'message': self.not_found_message
            })


class GetOnlinePayment(views.APIView):
    def get(self, request, *args, **kwargs):
        payment_uid = kwargs.get('payment_uid')
        if not payment_uid:
            return Response({
                'status': False,
                'message': "Missing 'Payment UID' parameter"
            }, status=status.HTTP_400_BAD_REQUEST)
        try:
            invoice = Invoice.objects.get(payment_uid=payment_uid)
        except Invoice.DoesNotExist:
            raise NotFound("Invoice with provided Payment UID not found.")
        
        method = request.query_params.get("method")
        if method == 'bkash':
            url = reverse('get-payment-bkash', kwargs={'payment_uid': str(payment_uid)})
            return redirect(f"{url}?redirect=1")
        elif method == 'nagad':
            return Response(
                {
                    'message': 'Redirect Nagad Payment Gateway URL!'
                }
            )
        
        payment_methods = [
            {"method": "bkash", "name": f"<a href=f'{bkash.BKASH_CALLBACK_BASE_URL}/api/v1/invoice/{payment_uid}/get-payment/bkash/'>Bkash</a>"},
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
        brand_key = request.headers.get("BRAND-KEY")

        if not api_key or not secret_key or not brand_key:
            raise AuthenticationFailed("Missing API-KEY, SECRET-KEY, or BRAND-KEY.")

        try:
            merchant = Merchant.objects.get(api_key=api_key, secret_key=secret_key, is_active=True)
        except Merchant.DoesNotExist:
            raise AuthenticationFailed("Invalid API-KEY.")

        # if not merchant.check_secret(secret_key):
        #     raise AuthenticationFailed("Invalid SECRET-KEY.")

        try:
            brand = UserBrand.objects.get(brand_key=brand_key, merchant=merchant, is_active=True)
        except UserBrand.DoesNotExist:
            raise AuthenticationFailed("Invalid BRAND-KEY for this merchant.")

        return merchant, brand
        
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
            merchant, brand = self.authenticate_using_api_key_and_secret(request)
            post_data = request.data.copy()
            data = self.json_encrypted(post_data)
            serializer = InvoiceSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            serializer.save(user=merchant.user, brand_id=brand)
            invoice = serializer.instance
            
            if invoice.method:
                if invoice.method.lower() == 'bkash':
                    url = reverse('get-payment-bkash', kwargs={'payment_uid': str(invoice.payment_uid)})
                    return redirect(f"{url}?redirect=1")
                    # return redirect(f"{url}")
                elif invoice.method.lower() == 'nagad':
                    return Response(
                        {
                            'message': 'Redirect Nagad Payment Gateway URL!'
                        }
                    )
            else:
                return redirect('get-payment', payment_uid=invoice.payment_uid)
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'message': str(e)
                }
            )





