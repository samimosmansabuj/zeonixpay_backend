from django.core.cache import cache
import requests
from rest_framework import views
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from rest_framework.response import Response
from core.models import Invoice
from rest_framework.exceptions import NotFound, ValidationError
from core.utils import DataEncryptDecrypt
from urllib.parse import urlencode
from authentication.models import BasePaymentGateWay

BKASH_ID_TOKEN_CACHE_KEY = "bkash:id_token"
BKASH_REFRESH_TOKEN_CACHE_KEY = "bkash:refresh_token"
BKASH_ID_TOKEN_TTL = 55 * 60
BKASH_REFRESH_TOKEN_TTL = 24 * 60 * 60



class BKashError(Exception):
    pass

class BKashClient:
    def __init__(self, random_bkash_gateway):
        self.base = f"{random_bkash_gateway.base_url}tokenized/checkout/"
        self.app_key = str(random_bkash_gateway.details_json["app_key"])
        self.app_secret = str(random_bkash_gateway.details_json["app_secret"])
        self.username = str(random_bkash_gateway.details_json["username"])
        self.password = str(random_bkash_gateway.details_json["password"])
        self.product_name = str(random_bkash_gateway.details_json["product_name"]) if random_bkash_gateway.details_json.get("product_name") else None

    # ------- token helpers -------
    def _grant_token(self):
        url = f"{self.base}token/grant"
        data = {
            "app_key": self.app_key,
            "app_secret": self.app_secret
        }
        headers = {
            "username": self.username,
            "password": self.password,
            "Content-Type": "application/json"
        }
        
        r = requests.post(url, json=data, headers=headers, timeout=30)
        if r.status_code != 200:
            raise BKashError(f"Grant token failed: {r.status_code} {r.text}")
        body = r.json()
        id_token = body.get("id_token")
        refresh_token = body.get("refresh_token")
        token_type = body.get("token_type", "Bearer")
        if not id_token or not refresh_token:
            raise BKashError(f"Bad grant token response: {body}")

        cache.set(BKASH_ID_TOKEN_CACHE_KEY, f"{token_type} {id_token}", BKASH_ID_TOKEN_TTL)
        cache.set(BKASH_REFRESH_TOKEN_CACHE_KEY, refresh_token, BKASH_REFRESH_TOKEN_TTL)
        return f"{token_type} {id_token}"

    def _refresh_token(self, refresh_token):
        url = self.base + "token/refresh"
        data = {
            "app_key": self.app_key,
            "app_secret": self.app_secret,
            "refresh_token": refresh_token
        }
        headers = {
            "username": self.username,
            "password": self.password,
            "Content-Type": "application/json"
        }
        r = requests.post(url, json=data, headers=headers, timeout=30)
        if r.status_code != 200:
            raise BKashError(f"Refresh token failed: {r.status_code} {r.text}")
        body = r.json()
        id_token = body.get("id_token")
        new_refresh_token = body.get("refresh_token") or refresh_token
        token_type = body.get("token_type", "Bearer")
        cache.set(BKASH_ID_TOKEN_CACHE_KEY, f"{token_type} {id_token}", BKASH_ID_TOKEN_TTL)
        cache.set(BKASH_REFRESH_TOKEN_CACHE_KEY, new_refresh_token, BKASH_REFRESH_TOKEN_TTL)
        return f"{token_type} {id_token}"

    def _authorization(self):
        token = cache.get(BKASH_ID_TOKEN_CACHE_KEY)
        if token:
            return token
        
        refresh_token = cache.get(BKASH_REFRESH_TOKEN_CACHE_KEY)
        if refresh_token:
            try:
                return self._refresh_token(refresh_token)
            except Exception:
                pass
        return self._grant_token()

    def _headers_auth(self):
        return {
            "accept": "application/json",
            "Authorization": self._authorization(),
            "X-App-Key": self.app_key,
            "content-type": "application/json"
        }

    # ------- payment endpoints -------
    def create_payment(self, *, amount, intent, merchant_invoice_number, payer_reference=None, mode="0011", agreement_id=None, callback_url=None):
        url = f"{self.base}create"
        payload = {
            "mode": mode,  # tokenization mode per bKash docs (sandbox often "0011")
            "callbackURL": callback_url,
            "amount": str(amount),
            "currency": "BDT",
            "intent": intent,
            "merchantInvoiceNumber": merchant_invoice_number,
        }
        if payer_reference:
            payload["payerReference"] = self.product_name if self.product_name is not None else "01770618575"
            # payload["payerReference"] = "TokenizedCheckout"
        if agreement_id:
            payload["agreementID"] = agreement_id

        print("******* Header Auth: ", self._headers_auth())
        
        r = requests.post(url, json=payload, headers=self._headers_auth())
        if r.status_code != 200:
            raise BKashError(f"Create payment failed: {r.status_code} {r.text}")
        return r.json()

    def execute_payment(self, payment_id: str):
        url = f"{self.base}execute"
        payload = {"paymentID": payment_id}
        r = requests.post(url, json=payload, headers=self._headers_auth(), timeout=30)
        if r.status_code != 200:
            raise BKashError(f"Execute payment failed: {r.status_code} {r.text}")
        return r.json()

    def query_payment(self, payment_id: str):
        url = self.base + "payment/status"
        payload = {"paymentID": payment_id}
        r = requests.post(url, json=payload, headers=self._headers_auth(), timeout=30)
        if r.status_code != 200:
            raise BKashError(f"Query payment failed: {r.status_code} {r.text}")
        return r.json()

    def refund(self, *, amount, payment_id, trx_id, sku=None, reason=None):
        url = self.base + "payment/refund"
        payload = {
            "paymentId": payment_id,
            "trxID": trx_id,
            "amount": str(amount)
        }
        if sku:
            payload["sku"] = sku
        if reason:
            payload["reason"] = reason

        r = requests.post(url, json=payload, headers=self._headers_auth(), timeout=30)
        if r.status_code != 200:
            raise BKashError(f"Refund failed: {r.status_code} {r.text}")
        return r.json()



# ===============================================================================================
def get_next_payment_gateway(method):
    gateways = BasePaymentGateWay.objects.filter(method=method, is_active=True).order_by('id')
    if not gateways.exists():
        print("**********", gateways)
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


class BKashCreatePaymentView(views.APIView):
    def _create_and_maybe_redirect(self, request, invoice_payment_id: str):
        if not invoice_payment_id:
            raise ValidationError({"invoice_payment_id": "This field is required."})
        try:
            invoice = Invoice.objects.get(invoice_payment_id=invoice_payment_id)
        except Invoice.DoesNotExist:
            raise NotFound("Invoice not found.")
        
        if invoice.pay_status.lower() == 'paid':
            return Response(
                {
                    'status': False,
                    'message': f"This invoice is already {invoice.pay_status} and cannot be edited."
                }
            )
        elif invoice.pay_status.lower() in ['failed', 'cancelled']:
            return Response(
                {
                    'status': False,
                    'message': f"This invoice is already {invoice.pay_status} and cannot be edited."
                }
            )
        
        random_bkash_gateway = get_next_payment_gateway(method='bkash')
        if random_bkash_gateway is None:
            return Response(
                {
                    'status': False,
                    'message': 'No Bkash Payment Method Found!'
                }
            )
        
        
        invoice.payment_gateway = random_bkash_gateway
        invoice.save(update_fields=["payment_gateway"])
        client = BKashClient(invoice.payment_gateway)
        # callback_url = f"{invoice.payment_gateway.callback_base_url}?invoice_payment_id={invoice_payment_id}"
        callback_url = f"{invoice.payment_gateway.callback_base_url}{reverse('bkash_callback', kwargs={'invoice_payment_id': str(invoice_payment_id)})}"
        try:
            resp = client.create_payment(
                amount=invoice.customer_amount,
                intent="sale",
                merchant_invoice_number=str(invoice.invoice_payment_id),
                payer_reference=str(invoice.invoice_trxn),
                mode="0011",
                callback_url=callback_url
            )
        except BKashError as e:
            return Response({"status": False, "message": str(e)}, status=502)

        payment_id = resp.get("paymentID")
        bkash_redirect_url = resp.get("bkashURL") or resp.get("bkashUrl") or resp.get("redirectURL")

        if payment_id:
            invoice.method_payment_id = payment_id
            invoice.pay_status = "pending"
            invoice.save(update_fields=["method_payment_id", "pay_status"])

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
        return self._create_and_maybe_redirect(request, request.GET.get("invoice_payment_id"))


class BKashCallbackView(views.APIView):
    def decrypt_data(self, data_json):
        encrypt_decrypt = DataEncryptDecrypt(data_json['key'])
        decrypt_data_json = encrypt_decrypt.decrypt_data(data_json['code'])
        return decrypt_data_json
    
    def get(self, request, *args, **kwargs):
        invoice_payment_id = kwargs.get('invoice_payment_id')
        payment_id = request.GET.get("paymentID")
        status = request.GET.get("status")
        # signature = request.GET.get("signature")
        
        invoice = get_object_or_404(Invoice, method_payment_id=payment_id, invoice_payment_id=invoice_payment_id)

        if not payment_id or not status:
            raise ValidationError("Missing paymentID or status.")
        
        client = BKashClient(invoice.payment_gateway)
        try:
            response = client.execute_payment(payment_id=payment_id)
        except BKashError as e:
            return Response({"status": False, "message": str(e)}, status=502)
        
        
        # if type(invoice.data) is str:
        #     client_callback_url = self.decrypt_data(json.loads(invoice.data))
        # else:
        #     client_callback_url = self.decrypt_data(invoice.data)
        client_callback_url = invoice.data

        # Success: Payment completed successfully
        if status == "success" and response.get("transactionStatus") == "Completed":
            invoice.pay_status = "paid"
            invoice.transaction_id = response.get("trxID")
            if not invoice.method:
                invoice.method = 'bkash'
            invoice.save()
            
            query_string = urlencode(response)
            redirect_url = f"{client_callback_url['success_url' or 'success']}?{query_string}"
            # return redirect(redirect_url)
            
            return Response({
                "status": True,
                "message": "Payment has been successfully completed.",
                "Execute API Response": response,
                'client_callback_url': redirect_url
            }, status=200)
        
        # Failure: Payment failed
        elif status == "failure":
            # print(client_callback_url)
            invoice.pay_status = "failed"
            invoice.save()
            return Response({
                "status": False,
                "message": "Payment failed. Please try again.",
                "Execute API Response": response,
                'client_callback_url': client_callback_url['failed_url' or 'failed']
            }, status=400)
        
        # Cancel: Payment was canceled
        elif status == "cancel":
            invoice.pay_status = "cancelled"
            invoice.save()
            return Response({
                "status": False,
                "message": "Payment was canceled by the user.",
                "Execute API Response": response,
                'client_callback_url': client_callback_url['cancel_url' or 'cancel']
            }, status=400)
        
        
        
        
        # Unknown status: In case status is something unexpected
        else:
            return Response({
                "status": False,
                "message": "Unknown status received. Please contact support.",
                "Execute API Response": response
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

