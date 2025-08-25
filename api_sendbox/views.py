from .serializers import CreatePaymentSerializer, PaymentTransferSerializer
from core.utils import build_logo_url
from rest_framework.exceptions import NotFound, AuthenticationFailed
from authentication.models import APIKey
from core.models import Invoice
from rest_framework.response import Response
from rest_framework import views, status
from django.shortcuts import redirect
from django.urls import reverse
from dotenv import load_dotenv
import os
load_dotenv()



# ===============================================================================================
# ================SendBox Merchant Payment Gate API View Start==============================
# ===============================================================================================
class SendBoxCreatePayment(views.APIView):
    def authenticate_using_api_key_and_secret(self, request):
        api_key = request.headers.get("API-KEY")
        secret_key = request.headers.get("SECRET-KEY")

        if not api_key or not secret_key:
            raise AuthenticationFailed("Missing API-KEY, SECRET-KEY, or BRAND-KEY.")
        try:
            api_key = APIKey.objects.get(api_key=api_key, secret_key=secret_key, is_active=True)
        except APIKey.DoesNotExist:
            raise AuthenticationFailed("Invalid API-KEY.")
        
        self._check_domain(request, api_key.merchant)

        return api_key.merchant
    
    def _check_domain(self, request, merchant):
        request_domain = request.META.get('HTTP_HOST', '').lower()
        allowed_domains = merchant.domain_name if isinstance(merchant.domain_name, list) else [merchant.domain_name]
        
        if not any(request_domain.endswith(allowed_domain) for allowed_domain in allowed_domains):
            raise AuthenticationFailed(f"Access denied from domain {request_domain}.")
    
    def post(self, request, *args, **kwargs):
        try:
            merchant = self.authenticate_using_api_key_and_secret(request)
            post_data = request.data.copy()
            serializer = CreatePaymentSerializer(data=post_data)
            serializer.is_valid(raise_exception=True)
            serializer.save(merchant=merchant)
            invoice = serializer.instance
            
            if invoice.method:
                if invoice.method.lower() == 'bkash':
                    url = f"{reverse('get-payment')}?invoice_payment_id={invoice.invoice_payment_id}&method=bkash"
                    return redirect(url)
                elif invoice.method.lower() == 'nagad':
                    return Response(
                        {
                            'message': 'Redirect Nagad Payment Gateway URL!'
                        }
                    )
            else:
                return redirect(f"{os.getenv('PAYMENT_SITE_BASE_URL')}/payment/?invoice_payment_id={invoice.invoice_payment_id}")
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'message': str(e)
                }
            )

class SendBoxPaymentPayOutView(views.APIView):
    def authenticate_using_api_key_and_secret(self, request):
        api_key = request.headers.get("API-KEY")
        secret_key = request.headers.get("SECRET-KEY")

        if not api_key or not secret_key:
            raise AuthenticationFailed("Missing API-KEY, SECRET-KEY, or BRAND-KEY.")

        try:
            api_key = APIKey.objects.get(api_key=api_key, secret_key=secret_key, is_active=True)
        except APIKey.DoesNotExist:
            raise AuthenticationFailed("Invalid API-KEY.")
        
        return api_key.merchant
    
    def post(self, request, *args, **kwargs):
        try:
            merchant = self.authenticate_using_api_key_and_secret(request)
            serializer = PaymentTransferSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(merchant=merchant)
            return Response(
                {
                    'status': True,
                    'mesage': 'PayOut Successfully!, Status Pending!'
                }, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'message': str(e)
                }
            )

class SendBoxGetOnlinePayment(views.APIView):
    def use_method_for_auto_redirect(self, method, invoice_payment_id):
        if method == 'bkash':
            url = reverse('get-payment-bkash')
            return redirect(f"{url}?invoice_payment_id={invoice_payment_id}&redirect=1")
        elif method == 'bkash-personal':
            return Response(
                {
                    'message': 'Bkash Personal Payment Process',
                    'url': f"{self.request.build_absolute_uri(reverse('bkash-manual-payment'))}?method={method}&invoice_payment_id={invoice_payment_id}"
                }, status=status.HTTP_200_OK
            )
        elif method == 'bkash-agent':
            return Response(
                {
                    'message': 'Bkash Agent Payment Process',
                    'url': f"{self.request.build_absolute_uri(reverse('bkash-manual-payment'))}?method={method}&invoice_payment_id={invoice_payment_id}"
                }, status=status.HTTP_200_OK
            )
        elif method == 'nagad':
            return Response(
                {
                    'message': 'Redirect Nagad Payment Gateway URL!'
                }, status=status.HTTP_200_OK
            )
        elif method == 'nagad-personal':
            return Response(
                {
                    'message': 'Nagad Personal Payment Process',
                    'url': f"{self.request.build_absolute_uri(reverse('nagad-manual-payment'))}?method={method}&invoice_payment_id={invoice_payment_id}"
                }, status=status.HTTP_200_OK
            )
        elif method == 'nagad-agent':
            return Response(
                {
                    'message': 'Nagad Agent Payment Process',
                    'url': f"{self.request.build_absolute_uri(reverse('nagad-manual-payment'))}?method={method}&invoice_payment_id={invoice_payment_id}"
                }, status=status.HTTP_200_OK
            )
        else:
            return Response({
                'status': True,
                'payment_methods': self.get_all_payment_method(invoice_payment_id)
            }, status=status.HTTP_200_OK)
    
    def _abs(self, name):
        return self.request.build_absolute_uri(reverse(name))
    
    def get_all_payment_method(self, invoice_payment_id):
        return [
            {
                "method": "bkash",
                "url": f"{self._abs('get-payment-bkash')}?invoice_payment_id={invoice_payment_id}&redirect=1"
            },
            {
                "method": "bkash-personal",
                "url": f"{self._abs('bkash-manual-payment')}?method=bkash-personal&invoice_payment_id={invoice_payment_id}"
            },
            {
                "method": "bkash-agent",
                "url": f"{self._abs('bkash-manual-payment')}?method=bkash-agent&invoice_payment_id={invoice_payment_id}"
            },
            {
                "method": "nagad-personal",
                "url": f"{self._abs('nagad-manual-payment')}?method=nagad-personal&invoice_payment_id={invoice_payment_id}"
            },
            {
                "method": "nagad-agent",
                "url": f"{self._abs('nagad-manual-payment')}?method=nagad-agent&invoice_payment_id={invoice_payment_id}"
            },
            {
                "method": "rocket-personal",
                "url": f"{self._abs('rocket-manual-payment')}?method=rocket-personal&invoice_payment_id={invoice_payment_id}"
            },
            {
                "method": "rocket-agent",
                "url": f"{self._abs('rocket-manual-payment')}?method=rocket-agent&invoice_payment_id={invoice_payment_id}"
            },
            {"method": "bank", "url": "Bank"}
        ]
    
    def get(self, request, *args, **kwargs):    
        invoice_payment_id = request.GET.get('invoice_payment_id')
        if not invoice_payment_id:
            return Response({
                'status': False,
                'message': "Missing 'Invoice Payment ID' parameter"
            }, status=status.HTTP_400_BAD_REQUEST)
        try:
            invoice = Invoice.objects.get(invoice_payment_id=invoice_payment_id)
        except Invoice.DoesNotExist:
            raise NotFound("Invoice with provided Invoice Payment ID not found.")
        
        print("brand_logo: ", invoice.merchant.brand_logo)
        
        status_verify = self.status_verify(invoice)
        if status_verify:
            return status_verify
        
        method = request.query_params.get("method")
        if method:
            return self.use_method_for_auto_redirect(method, invoice_payment_id)
                
        return Response({
            'status': True,
            'invoice': {
                "amount": invoice.customer_amount
            },
            'mechant_info': {
                'brand_name': invoice.merchant.brand_name,
                'brand_logo': build_logo_url(request, getattr(invoice.merchant, 'brand_logo', None))
            },
            'payment_methods': self.get_all_payment_method(invoice_payment_id)
        }, status=status.HTTP_200_OK)
    
    def status_verify(self, invoice):
        if invoice.pay_status.lower() in ['paid', 'failed', 'cancelled']:
            return Response(
                {
                    'status': False,
                    'message': f"This invoice is already {invoice.pay_status} and cannot be edited."
                }, status=status.HTTP_406_NOT_ACCEPTABLE
            )
        return False


# ===============================================================================================
# ================SendBox Merchant Payment Gate API View Start==============================
# # ===============================================================================================

