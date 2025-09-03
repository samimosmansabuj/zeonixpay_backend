from django.shortcuts import render, HttpResponse, get_object_or_404, redirect
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import PersonalAgentPaymentProcessSerializer
from rest_framework import status, views
from core.models import Invoice
from rest_framework.exceptions import ValidationError
from authentication.models import BasePaymentGateWay
from django.core.cache import cache
from authentication.models import StorePaymentMessage
from django.db import transaction
from django.db.models import Q
import os
from dotenv import load_dotenv
load_dotenv()

PROVIDER_SOURCES = {
    "bkash": ["bKash", "BKASH"],
    "nagad": ["NAGAD"],
    "rocket": ["16216"],
}

class PersonalAgentPaymentBaseView(views.APIView):
    provider = None
    serializer_class = None

    # ---------- entry points ----------
    def post(self, request, *args, **kwargs):
        try:
            method = request.query_params.get('method')
            if not method:
                return Response(
                    {
                        "status": False,
                        "message": f"Payment method ({self.provider}-personal or {self.provider}-agent) not provided!"
                    }
                )
            self._assert_method_matches_provider(method)

            invoice = self._get_invoice()

            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            txid = str(serializer.validated_data.get('transaction_Id') or "").strip()
            if not txid:
                raise Exception({"transaction_Id": "Transaction ID is required."})

            with transaction.atomic():
                self._verify_payment(txid, invoice)
                self._mark_invoice_paid(invoice, txid, method)

            # redirect_url = f"{os.getenv("PAYMENT_REDIRECT_PAGE_BASE_URL")}?status=success&invoice_payment_id={invoice.invoice_payment_id}"
            return Response(
                {
                    "status": True,
                    "message": "Payment has been successfully completed.",
                    "invoice_payment_id": invoice.invoice_payment_id
                },
                status=status.HTTP_200_OK,
            )
            # redirect_url = f"{os.getenv("PAYMENT_REDIRECT_PAGE_BASE_URL")}?status=success"
            # return redirect(redirect_url)
            
        except ValidationError:
            erorr_message = [str(value[0]) for key, value in serializer.errors.items()][0]
            return Response(
                {
                    "status": False,
                    "message": erorr_message
                }, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )

    def get(self, request, *args, **kwargs):
        try:
            method = request.query_params.get('method')
            if not method:
                return Response(
                    {
                        "status": False,
                        "message": f"Payment method ({self.provider}-personal or {self.provider}-agent) not provided!"
                    }
                )
            self._assert_method_matches_provider(method)

            invoice = self._get_invoice()

            gateway = self._get_next_gateway(method)
            invoice.payment_gateway = gateway
            invoice.method_payment_id = None
            invoice.save(update_fields=["payment_gateway", "method_payment_id"])

            number = gateway.details_json['phone_number'] if gateway else None
            not_avail = {
                "bkash-personal": "Bkash Send Money Method Not Available Right Now, Try Another Method!",
                "bkash-agent":    "Bkash Cashout Method Not Available Right Now, Try Another Method!",
                "nagad-personal": "Nagad Send Money Method Not Available Right Now, Try Another Method!",
                "nagad-agent":    "Nagad Cashout Method Not Available Right Now, Try Another Method!",
                "rocket-personal":"Rocket Send Money Method Not Available Right Now, Try Another Method!",
                "rocket-agent":   "Rocket Cashout Method Not Available Right Now, Try Another Method!",
            }[method]

            msg_verb = "Send Money" if method.endswith("personal") else "Cashout"
            return Response(
                {
                    "status": True,
                    "data": {
                        "Method": method.title(),
                        "Number": number if number else not_avail,
                        "Message": f"Submit Your Phone Number & Transaction ID. {msg_verb} Amount is {invoice.customer_amount}",
                    }
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )

    # ---------- helpers ----------
    def _assert_method_matches_provider(self, method: str) -> str:
        m = (method or "").strip().lower()
        allowed = {f"{self.provider}-personal", f"{self.provider}-agent"}
        if m not in allowed:
            raise Exception(f"{m} Invalid Method")
        return m

    def _get_invoice(self):
        invoice_payment_id = self.request.query_params.get('invoice_payment_id')
        if not invoice_payment_id:
            raise ValidationError({"invoice_payment_id": "Invoice Payment ID not provided!"})

        if Invoice.objects.filter(invoice_payment_id=invoice_payment_id).exists():
            invoice = get_object_or_404(Invoice, invoice_payment_id=invoice_payment_id)

            if (invoice.pay_status or "").lower() in ("paid", "failed", "cancelled"):
                raise Exception(f"This invoice is already {invoice.pay_status} and cannot be edited.")
            return invoice
        else:
            raise Exception("Not Invoice Found with this Payment ID!")

    def _get_next_gateway(self, method: str):
        qs = BasePaymentGateWay.objects.filter(method=method).order_by('id')
        if not qs.exists():
            return None
        cache_key = f"last_used_{method}_id"
        last_id = cache.get(cache_key)
        if last_id:
            nxt = qs.filter(id__gt=last_id).first() or qs.first()
        else:
            nxt = qs.first()
        cache.set(cache_key, nxt.id, None)
        return nxt

    def _verify_payment(self, transaction_id: str, invoice):
        src_q = Q()
        for token in PROVIDER_SOURCES[self.provider]:
            src_q |= Q(message_from__icontains=token)

        def fetch_one(qs):
            try:
                return qs.select_for_update().get()
            except StorePaymentMessage.DoesNotExist:
                return None
            except StorePaymentMessage.MultipleObjectsReturned:
                raise Exception("Exist Multiple Object With this Transaction ID, Please contact support team!")

        msg = fetch_one(
            StorePaymentMessage.objects.filter(src_q, trx_id=transaction_id)
        )
        if msg and msg.message_amount != invoice.customer_amount:
            raise Exception("Amount doesn't match with this Trx_ID!")
        
        if msg is None:
            msg = fetch_one(
                StorePaymentMessage.objects.filter(src_q, message__icontains=transaction_id)
            )

        if msg is None:
            raise Exception("Not Found Trx_ID with your Transaction ID and Amount!")

        if msg.is_verified:
            raise Exception("With this Transaction ID and Amount is already verified, Try again!")

        msg.is_verified = True
        msg.verified_invoice = invoice
        msg.save(update_fields=["is_verified", "verified_invoice"])
        return True
        # raise Exception("No Return")

    def _mark_invoice_paid(self, invoice, transaction_id: str, method: str):
        invoice.pay_status = "paid"
        invoice.transaction_id = transaction_id
        if not invoice.method:
            invoice.method = method
        invoice.save(update_fields=["pay_status", "transaction_id", "method"])

    def _build_success_redirect(self, invoice):
        cb = invoice.callback_url
        if isinstance(cb, dict):
            url = cb.get("success_url") or cb.get("success") or ""
        else:
            url = str(cb or "")
        if not url:
            return ""  # or keep None
        # append param safely
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}transactionStatus=success"



class BkashPersonalAgentPaymentView(PersonalAgentPaymentBaseView):
    provider = "bkash"
    serializer_class = PersonalAgentPaymentProcessSerializer

class NagadPersonalAgentPaymentView(PersonalAgentPaymentBaseView):
    provider = "nagad"
    serializer_class = PersonalAgentPaymentProcessSerializer

class RocketPersonalAgentPaymentView(PersonalAgentPaymentBaseView):
    provider = "rocket"
    serializer_class = PersonalAgentPaymentProcessSerializer





