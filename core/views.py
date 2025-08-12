from rest_framework import views, status
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from rest_framework.response import Response
from .models import Invoice, PaymentTransfer, WithdrawRequest, WalletTransaction
from .serializers import InvoiceSerializer, PaymentTransferSerializer, WithdrawRequestSerializer, WalletTransactionSerializer
from authentication.permissions import IsOwnerByUser
from .utils import CustomPaymentSectionViewsets, DataEncryptDecrypt
from rest_framework.exceptions import NotFound, ValidationError, AuthenticationFailed
from authentication.models import Merchant, UserBrand
from .payment.bkash import BKashClient, BKashError
from .payment import bkash



# Invoice Views
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


# ===============================================================================================
class BKashCreatePaymentView(views.APIView):
    def _create_and_maybe_redirect(self, request, payment_uid: str):
        if not payment_uid:
            raise ValidationError({"payment_uid": "This field is required."})
        try:
            invoice = Invoice.objects.get(payment_uid=payment_uid)
        except Invoice.DoesNotExist:
            raise NotFound("Invoice not found.")

        client = BKashClient()
        callback_url = f"{bkash.BKASH_CALLBACK_BASE_URL}{reverse('bkash_callback', kwargs={'payment_uid': str(payment_uid)})}"
        print(callback_url)
        try:
            resp = client.create_payment(
                amount=invoice.customer_amount,
                intent="sale",
                merchant_invoice_number=str(invoice.payment_uid),
                payer_reference=str(invoice.invoice_trxn),
                mode="0011",
                callback_url=callback_url
            )
        except BKashError as e:
            return Response({"status": False, "message": str(e)}, status=502)

        payment_id = resp.get("paymentID")
        bkash_redirect_url = resp.get("bkashURL") or resp.get("bkashUrl") or resp.get("redirectURL")

        if payment_id:
            invoice.bkash_payment_id = payment_id
            invoice.pay_status = "pending"
            invoice.save(update_fields=["bkash_payment_id", "pay_status"])

        if request.query_params.get("redirect") in ("1", "true", "yes"):
            if bkash_redirect_url:
                return redirect(bkash_redirect_url)
            return Response({"status": False, "message": "No bKash redirect URL returned."}, status=502)
        
        return Response({
            "status": True,
            "paymentID": payment_id,
            "redirectURL": bkash_redirect_url,
            "raw": resp
        }, status=200)
    
    def get(self, request, *args, **kwargs):
        return self._create_and_maybe_redirect(request, kwargs.get("payment_uid"))
    
    def post(self, request, *args, **kwargs):
        return self._create_and_maybe_redirect(request, kwargs.get("payment_uid") or request.data.get("payment_uid"))


class BKashCallbackView(views.APIView):
    def get(self, request, *args, **kwargs):
        payment_uid = kwargs.get('payment_uid')
        payment_id = request.GET.get("paymentID")
        status = request.GET.get("status")
        # signature = request.GET.get("signature")

        if not payment_id or not status:
            raise ValidationError("Missing paymentID or status.")
        
        client = BKashClient()
        try:
            response = client.execute_payment(payment_id=payment_id)
        except BKashError as e:
            return Response({"status": False, "message": str(e)}, status=502)

        invoice = get_object_or_404(Invoice, bkash_payment_id=payment_id, payment_uid=payment_uid)

        # Success: Payment completed successfully
        if status == "success" and response.get("transactionStatus") == "Completed":
            invoice.pay_status = "paid"
            invoice.save()
            return Response({
                "status": True,
                "message": "Payment has been successfully completed.",
                "data": response
            }, status=200)
        
        # Failure: Payment failed
        elif status == "failure":
            invoice.pay_status = "failed"
            invoice.save()
            return Response({
                "status": False,
                "message": "Payment failed. Please try again.",
                "data": response
            }, status=400)
        
        # Cancel: Payment was canceled
        elif status == "cancel":
            print(invoice.status)
            invoice.pay_status = "cancelled"
            invoice.save()
            print(invoice.status)
            return Response({
                "status": False,
                "message": "Payment was canceled by the user.",
                "data": response
            }, status=400)
        
        # Unknown status: In case status is something unexpected
        else:
            return Response({
                "status": False,
                "message": "Unknown status received. Please contact support.",
                "data": response
            }, status=400)



class BKashQueryPaymentView(views.APIView):
    def get(self, request, *args, **kwargs):
        payment_id = request.query_params.get("paymentID")
        if not payment_id:
            return Response({"status": False, "message": "paymentID missing"}, status=400)
        client = BKashClient()
        try:
            data = client.query_payment(payment_id)
        except BKashError as e:
            return Response({"status": False, "message": str(e)}, status=502)
        return Response({"status": True, "data": data})


class BKashRefundView(views.APIView):
    def post(self, request, *args, **kwargs):
        payment_id = request.data.get("paymentID")
        trx_id = request.data.get("trxID")
        amount = request.data.get("amount")
        if not (payment_id and trx_id and amount):
            raise ValidationError({"detail": "paymentID, trxID and amount are required."})
        client = BKashClient()
        try:
            data = client.refund(amount=amount, payment_id=payment_id, trx_id=trx_id, sku=request.data.get("sku"), reason=request.data.get("reason"))
        except BKashError as e:
            return Response({"status": False, "message": str(e)}, status=502)
        return Response({"status": True, "data": data})
# ===============================================================================================


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
            "success_url": post_data.get("success_url"),
            "cancel_url": post_data.get("cancel_url"),
            "failed_url": post_data.get("failed_url"),
        }
        object = DataEncryptDecrypt()
        encrypted_data = object.encrypt_data(url_json)
        post_data['data'] = str(encrypted_data)
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





