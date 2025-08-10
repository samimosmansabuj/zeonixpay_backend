from rest_framework import generics, views, status
from django.shortcuts import redirect
from rest_framework.response import Response
from .models import Invoice, PaymentTransfer, WithdrawRequest, WalletTransaction
from .serializers import InvoiceSerializer, PaymentTransferSerializer, WithdrawRequestSerializer, WalletTransactionSerializer
from authentication.permissions import IsOwnerByUser
from .utils import CustomPaymentSectionViewsets, BKashClient, bkash_grant_token, BkashPayment, bkash_create_payment, bkash_execute_payment
from rest_framework.exceptions import NotFound
from django.views.decorators.csrf import csrf_exempt


from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError
# from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse

from .models import Invoice
from .serializers import InvoiceSerializer
from .payment.bkash import BKashClient, BKashError
from .payment import bkash

import requests
from dotenv import load_dotenv
import os
load_dotenv()



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
            {"method": "bkash", "name": f"<a href='http://127.0.0.1:8000/api/v1/invoice/{payment_uid}/get-payment/bkash/'>Bkash</a>"},
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
        try:
            resp = client.create_payment(
                amount=invoice.customer_amount,
                intent="sale",
                merchant_invoice_number=str(invoice.payment_uid),
                payer_reference=str(invoice.invoice_trxn),
                mode="0011",
                callback_url=bkash.BKASH_CALLBACK_URL
            )
        except BKashError as e:
            return Response({"status": False, "message": str(e)}, status=502)

        payment_id = resp.get("paymentID")
        bkash_redirect_url = resp.get("bkashURL") or resp.get("bkashUrl") or resp.get("redirectURL")

        if payment_id:
            invoice.bkash_payment_id = payment_id
            invoice.status = "pending"
            invoice.save(update_fields=["bkash_payment_id", "status"])

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


class BKashExecutePaymentView(views.APIView):
    """
    bKash redirects the user back to your callback URL after authorization,
    typically with a paymentID. You can:
      - execute here and redirect to your invoice page, or
      - return JSON and let frontend poll/confirm.
    We'll execute and then redirect.
    """
    authentication_classes = []  # usually public
    permission_classes = []

    def get(self, request, *args, **kwargs):
        payment_id = request.query_params.get("paymentID") or request.query_params.get("paymentId")
        if not payment_id:
            return Response({"status": False, "message": "paymentID missing"}, status=400)

        # Find the invoice by payment_id (you stored it earlier)
        try:
            invoice = Invoice.objects.get(bkash_payment_id=payment_id)
        except Invoice.DoesNotExist:
            # Fallback: you might pass payment_uid in return URL and use that instead
            return Response({"status": False, "message": "Invoice not found for paymentID"}, status=404)

        client = BKashClient()
        try:
            exec_resp = client.execute_payment(payment_id)
        except BKashError as e:
            # mark failed
            invoice.status = "failed"
            invoice.save(update_fields=["status"])
            return Response({"status": False, "message": str(e)}, status=502)

        # Interpret execute response
        trx_id = exec_resp.get("trxID") or exec_resp.get("transactionID")
        status_code = exec_resp.get("statusCode") or exec_resp.get("status")  # depends on sandbox payload
        status_msg = exec_resp.get("statusMessage") or exec_resp.get("message", "")
        success = bool(trx_id) and str(status_code) in ("0000", "Success", "Completed", "200")

        if success:
            invoice.status = "paid"
            invoice.bkash_trx_id = trx_id
            invoice.save(update_fields=["status", "bkash_trx_id"])
        else:
            invoice.status = "failed"
            invoice.save(update_fields=["status"])

        # Redirect the user back to your invoice page in the frontend
        # Include any info you want the frontend to show.
        redirect_to = f"{bkash.BKASH_CALLBACK_URL}?payment_uid={invoice.payment_uid}&result={'success' if success else 'failed'}"
        return redirect(redirect_to)


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


class CreatePaymentInvoice(views.APIView):
    def post(self, request, *args, **kwargs):
        return Response(
            {
                'status': True,
                'message': 'ok'
            }
        )






# class BkashExecutePaymentView(views.APIView):
#     def get(self, request):
#         payment_id = request.query_params.get("paymentID")
#         token = bkash_grant_token().get("id_token")

#         exec_data = bkash_execute_payment(token, payment_id)

#         if exec_data.get("transactionStatus") == "Completed":
#             invoice_no = exec_data.get("merchantInvoiceNumber")
#             Invoice.objects.filter(id=invoice_no).update(status="paid")
#             return redirect("/payment-success/")
#         else:
#             return redirect("/payment-failed/")


# class CreatePaymentViewWithBkash(views.APIView):
#     def post(self, request, *args, **kwargs):
#         payment_uid = self.kwargs.get('payment_uid')
#         # payment_uid = request.data.get('payment_uid')
#         invoice = Invoice.objects.get(payment_uid=payment_uid)
#         if not invoice:
#             return Response({"status": False, "message": "Invoice not found"}, status=404)

        
#         token = bkash_grant_token().get("id_token")
#         create_payload = bkash_create_payment(token, invoice.customer_amount, invoice.payment_uid)
#         bkash_url = create_payload.get("bkashURL")
#         if not bkash_url:
#             return Response({"status": False, "message": "bKash did not return bkashURL", "detail": create_payload}, status=400)

#         return Response({"status": True, "redirect_url": bkash_url, "payment_id": create_payload.get("paymentID")}, status=200)

        # client = BkashPayment()
        # create_data = client._create_payment(amount=100, invoice_number=555)
        # if create_data.get("bkashURL"):
        #     return Response({"redirect_url": create_data["bkashURL"]})
        # return Response({"status": False, "message": create_data}, status=400)
        
        # client = BKashClient()
        # grant_token = client._grant_token()
        
        # token = bkash_grant_token.get("id_token")
        # create_data = bkash_create_payment
        
        
        
        
        # return Response(
        #     {
        #         'status': True,
        #         'message': "ok",
        #         "data": create_payment
        #     }, status=status.HTTP_200_OK
        # )
        
        



# class CreatePaymentView(views.APIView):
#     def post(self, request, *args, **kwargs):
        
#         grant_response = requests.post(grant_token_url, headers=headers, data=data)
        
#         if grant_response.status_code != 200:
#             return Response({
#                 'status': False,
#                 'message': "Failed to grant token"
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#         grant_token = grant_response.json().get('token')

#         # Step 2: Create Payment (Sale or Authorize)
#         payment_create_url = "https://checkout.sandbox.bka.sh/v1.2.0-beta/checkout/payment/create"
#         payment_data = {
#             "amount": str(invoice.customer_amount),
#             "currency": "BDT",
#             "intent": "sale",  # Sale intent for a direct payment
#             "merchantInvoiceNumber": invoice.payment_uid,
#             "merchantAssociationInfo": "Merchant info",
#         }
#         payment_headers = {
#             'Authorization': f'Bearer {grant_token}',
#             'X-APP-Key': settings.BKASH_APP_KEY
#         }
#         payment_response = requests.post(payment_create_url, headers=payment_headers, data=payment_data)

#         if payment_response.status_code != 200:
#             return Response({
#                 'status': False,
#                 'message': "Failed to create payment"
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#         payment_info = payment_response.json()
#         payment_id = payment_info.get('paymentID')

#         # Step 3: Execute Payment
#         execute_payment_url = f"https://checkout.sandbox.bka.sh/v1.2.0-beta/checkout/payment/execute/{payment_id}"
#         execute_response = requests.post(execute_payment_url, headers=payment_headers)

#         if execute_response.status_code == 200:
#             # Redirect the user after successful payment
#             return Response({
#                 'status': True,
#                 'message': "Payment successful",
#                 'payment_details': execute_response.json()
#             }, status=status.HTTP_200_OK)
#         else:
#             return Response({
#                 'status': False,
#                 'message': "Payment execution failed"
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)






# class InvoiceDetailView(generics.RetrieveUpdateDestroyAPIView):
#     queryset = Invoice.objects.all()
#     serializer_class = InvoiceSerializer
#     permission_classes = [permissions.IsAuthenticated]


# Payment Transfer Views
# class PaymentTransferListCreateView(generics.ListCreateAPIView):
#     queryset = PaymentTransfer.objects.all().order_by('-id')
#     serializer_class = PaymentTransferSerializer
#     permission_classes = [permissions.IsAuthenticated]

#     def perform_create(self, serializer):
#         serializer.save(user=self.request.user)


# class PaymentTransferDetailView(generics.RetrieveUpdateDestroyAPIView):
#     queryset = PaymentTransfer.objects.all()
#     serializer_class = PaymentTransferSerializer
#     permission_classes = [permissions.IsAuthenticated]


# # Withdraw Request Views
# class WithdrawRequestListCreateView(generics.ListCreateAPIView):
#     queryset = WithdrawRequest.objects.all().order_by('-id')
#     serializer_class = WithdrawRequestSerializer
#     permission_classes = [permissions.IsAuthenticated]

#     def perform_create(self, serializer):
#         serializer.save(user=self.request.user)


# class WithdrawRequestDetailView(generics.RetrieveUpdateDestroyAPIView):
#     queryset = WithdrawRequest.objects.all()
#     serializer_class = WithdrawRequestSerializer
#     permission_classes = [permissions.IsAuthenticated]


# # Wallet Transaction Views
# class WalletTransactionListCreateView(generics.ListCreateAPIView):
#     queryset = WalletTransaction.objects.all().order_by('-id')
#     serializer_class = WalletTransactionSerializer
#     permission_classes = [permissions.IsAuthenticated]

#     def perform_create(self, serializer):
#         serializer.save(user=self.request.user)


# class WalletTransactionDetailView(generics.RetrieveUpdateDestroyAPIView):
#     queryset = WalletTransaction.objects.all()
#     serializer_class = WalletTransactionSerializer
#     permission_classes = [permissions.IsAuthenticated]



