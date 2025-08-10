from rest_framework import viewsets
from authentication.permissions import IsOwnerByUser
from authentication.models import CustomUser
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.response import Response
from rest_framework import status
import os
import requests



class CustomPaymentSectionViewsets(viewsets.ModelViewSet):
    permission_classes = [IsOwnerByUser]
    pagination_class = None
    
    model = None
    create_success_message = "Created!"
    update_success_message = "Updated!"
    delete_success_message = "Deleted!"
    not_found_message = "Object Not Found!"
    ordering_by = "-id"
    
    #----------User-----------------------------------
    def get_user(self):
        pid = self.kwargs.get('pid')
        try:
            user = CustomUser.objects.get(pid=pid)
        except CustomUser.DoesNotExist:
            user = None
        return user
    
    #-------------Object Queryset-----------------------
    def get_queryset(self):
        user = self.get_user()
        if user:
            return self.model.objects.filter(user=user).order_by(self.ordering_by)
        return self.model.objects.none()
    
    #-------------Created-------------------------------
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
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
        user = self.request.user
        serializer.save(user=user)
    
    
    #-------------------Queryset List-------------------
    def list(self, request, *args, **kwargs):
        try:
            response = super().list(request, *args, **kwargs).data
            return Response(
                {
                    'status': True,
                    'count': len(response),
                    'data': response
                }, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get_object(self):
        try:
            query_set = self.get_queryset()
            return query_set.get(pk=self.kwargs.get('pk'))
        except self.model.DoesNotExist:
            raise NotFound({
                'status': False,
                'message': self.not_found_message
            })
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response(
            {
                'status': True,
                'data': self.get_serializer(instance).data
            }, status=status.HTTP_200_OK
        )
    

    def update(self, request, *args, **kwargs):
        try:
            object = self.get_object()
            serializer = self.get_serializer(object, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(
                {
                    'status': True,
                    'message': self.update_success_message,
                    'data': serializer.data
                },
                status=status.HTTP_200_OK
            )
        except ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}
            return Response(
                {
                    'status': False,
                    'error': error
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return Response(
            {
                'status': True,
                'message': self.delete_success_message,
            }, status=status.HTTP_200_OK
        )




class BKashError(Exception):
    pass

class BKashClient:
    def __init__(self):
        self.bkash_Base_URL = os.getenv("bkash_Base_URL")
        self.bkash_App_Key = os.getenv("bkash_App_Key")
        self.bkash_App_Secret_Key = os.getenv("bkash_App_Secret_Key")
        self.bkash_username = os.getenv("bkash_username")
        self.bkash_password = os.getenv("bkash_password")
    
    # ------- token helpers -------
    def _grant_token(self):
        url = f"{self.bkash_Base_URL}token/grant"
        payload = {
            "app_key": self.bkash_App_Key,
            "app_secret": self.bkash_App_Secret_Key
        }
        headers = {
            "username": self.bkash_username,
            "password": self.bkash_password,
            "Content-Type": "application/json"
        }
        
        grant_response = requests.post(url, json=payload, headers=headers)
        grant_response.raise_for_status()
        return grant_response.json()
        
        # if r.status_code != 200:
        #     raise BKashError(f"Grant token failed: {r.status_code} {r.text}")
        # body = r.json()
        # id_token = body.get("id_token")
        # refresh_token = body.get("refresh_token")
        # token_type = body.get("token_type", "Bearer")
        # if not id_token or not refresh_token:
        #     raise BKashError(f"Bad grant token response: {body}")

        # cache.set(settings.BKASH_ID_TOKEN_CACHE_KEY, f"{token_type} {id_token}", settings.BKASH_ID_TOKEN_TTL)
        # cache.set(settings.BKASH_REFRESH_TOKEN_CACHE_KEY, refresh_token, settings.BKASH_REFRESH_TOKEN_TTL)
        # return f"{token_type} {id_token}"
    
    
    

    # def _refresh_token(self, refresh_token):
    #     url = self.base + "token/refresh"
    #     data = {
    #         "app_key": self.app_key,
    #         "app_secret": self.app_secret,
    #         "refresh_token": refresh_token
    #     }
    #     headers = {
    #         "username": self.username,
    #         "password": self.password,
    #         "Content-Type": "application/json"
    #     }
    #     r = requests.post(url, json=data, headers=headers, timeout=30)
    #     if r.status_code != 200:
    #         raise BKashError(f"Refresh token failed: {r.status_code} {r.text}")
    #     body = r.json()
    #     id_token = body.get("id_token")
    #     new_refresh_token = body.get("refresh_token") or refresh_token
    #     token_type = body.get("token_type", "Bearer")
    #     cache.set(settings.BKASH_ID_TOKEN_CACHE_KEY, f"{token_type} {id_token}", settings.BKASH_ID_TOKEN_TTL)
    #     cache.set(settings.BKASH_REFRESH_TOKEN_CACHE_KEY, new_refresh_token, settings.BKASH_REFRESH_TOKEN_TTL)
    #     return f"{token_type} {id_token}"

    # def _authorization(self):
    #     token = cache.get(settings.BKASH_ID_TOKEN_CACHE_KEY)
    #     if token:
    #         return token
    #     # Try refresh
    #     refresh_token = cache.get(settings.BKASH_REFRESH_TOKEN_CACHE_KEY)
    #     if refresh_token:
    #         try:
    #             return self._refresh_token(refresh_token)
    #         except Exception:
    #             pass
    #     # Fallback to grant
    #     return self._grant_token()

    # def _headers_auth(self):
    #     return {
    #         "Authorization": self._authorization(),
    #         "X-APP-Key": self.app_key,
    #         "Content-Type": "application/json"
    #     }

    # # ------- payment endpoints -------
    # def create_payment(self, *, amount, currency, intent, merchant_invoice_number, payer_reference=None, mode="0011", agreement_id=None, callback_url=None):
    #     url = f"{self.bkash_Base_URL}create"
    #     payload = {
    #         "mode": mode,  # tokenization mode per bKash docs (sandbox often "0011")
    #         "callbackURL": callback_url,
    #         # "callbackURL": callback_url or settings.BKASH_CALLBACK_URL,
    #         "amount": str(amount),
    #         "currency": currency,
    #         "intent": intent,  # e.g. "sale"
    #         "merchantInvoiceNumber": merchant_invoice_number,
    #     }
    #     if payer_reference:
    #         payload["payerReference"] = str(payer_reference)
    #     if agreement_id:
    #         payload["agreementID"] = agreement_id

    #     r = requests.post(url, json=payload, headers=self._headers_auth())
    #     if r.status_code != 200:
    #         raise BKashError(f"Create payment failed: {r.status_code} {r.text}")
    #     return r.json()

    # def execute_payment(self, payment_id: str):
    #     url = self.base + "execute"
    #     payload = {"paymentID": payment_id}
    #     r = requests.post(url, json=payload, headers=self._headers_auth(), timeout=30)
    #     if r.status_code != 200:
    #         raise BKashError(f"Execute payment failed: {r.status_code} {r.text}")
    #     return r.json()

    # def query_payment(self, payment_id: str):
    #     url = self.base + "payment/status"
    #     payload = {"paymentID": payment_id}
    #     r = requests.post(url, json=payload, headers=self._headers_auth(), timeout=30)
    #     if r.status_code != 200:
    #         raise BKashError(f"Query payment failed: {r.status_code} {r.text}")
    #     return r.json()

    # def refund(self, *, amount, payment_id, trx_id, sku=None, reason=None):
    #     url = self.base + "payment/refund"
    #     payload = {
    #         "paymentId": payment_id,
    #         "trxID": trx_id,
    #         "amount": str(amount)
    #     }
    #     if sku:
    #         payload["sku"] = sku
    #     if reason:
    #         payload["reason"] = reason

    #     r = requests.post(url, json=payload, headers=self._headers_auth(), timeout=30)
    #     if r.status_code != 200:
    #         raise BKashError(f"Refund failed: {r.status_code} {r.text}")
    #     return r.json()



# https://tokenized.sandbox.bka.sh/v1.2.0-beta/tokenized/checkout/

def bkash_grant_token():
    bkash_Base_URL = os.getenv("bkash_Base_URL")
    bkash_App_Key = os.getenv("bkash_App_Key")
    bkash_App_Secret_Key = os.getenv("bkash_App_Secret_Key")
    bkash_username = os.getenv("bkash_username")
    bkash_password = os.getenv("bkash_password")
    url = f"{bkash_Base_URL}token/grant"
    payload = {
        "app_key": bkash_App_Key,
        "app_secret": bkash_App_Secret_Key
    }
    headers = {
        "username": bkash_username,
        "password": bkash_password,
        "Content-Type": "application/json"
    }
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()


def bkash_create_payment(id_token: str, amount, invoice_number):
    bkash_App_Key = os.getenv("bkash_App_Key")
    url = f"{os.getenv("bkash_Base_URL")}create"
    payload = {
        "mode": "0011",
        "payerReference": "INV",
        "callbackURL": "https://pay.zeonixpay.com/callback/bkash/m0kklo13pk9149mnkn8m977n762n0m70",
        "amount": str(amount),
        "currency": "BDT",
        "intent": "sale",
        "merchantInvoiceNumber": str(invoice_number),
    }
    headers = {
        "Authorization": id_token,
        "X-APP-Key": bkash_App_Key,
        "Content-Type": "application/json",
    }
    res = requests.post(url, json=payload, headers=headers)
    res.raise_for_status()
    return res.json()


def bkash_execute_payment(id_token, payment_id):
    bkash_App_Key = os.getenv("bkash_App_Key")
    url = f"{os.getenv("bkash_Base_URL")}execute"
    headers = {
        "Authorization": id_token,
        "X-APP-Key": bkash_App_Key
    }
    payload = {"paymentID": payment_id}
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()


class BkashPayment:
    def __init__(self):
        self.bkash_Base_URL = os.getenv("bkash_Base_URL")
        self.bkash_App_Key = os.getenv("bkash_App_Key")
        self.bkash_App_Secret_Key = os.getenv("bkash_App_Secret_Key")
        self.bkash_username = os.getenv("bkash_username")
        self.bkash_password = os.getenv("bkash_password")
    
    def _grant_token(self):
        url = f"{self.bkash_Base_URL}token/grant"
        payload = {
            "app_key": self.bkash_App_Key,
            "app_secret": self.bkash_App_Secret_Key
        }
        headers = {
            "username": self.bkash_username,
            "password": self.bkash_password,
            "Content-Type": "application/json"
        }
        
        grant_response = requests.post(url, json=payload, headers=headers)
        grant_response.raise_for_status()
        return grant_response.json()

    def get_id_token(self):
        return self._grant_token().get("id_token")
    
    def _create_payment(self, amount, invoice_number):
        bkash_App_Key = os.getenv("bkash_App_Key")
        url = f"{os.getenv("bkash_Base_URL")}/create"
        payload = {
            "mode": "0011",
            "payerReference": " ",
            "callbackURL": "https://pay.zeonixpay.com/callback/bkash/m0kklo13pk9149mnkn8m977n762n0m70",
            "amount": str(amount),
            "currency": "BDT",
            "intent": "sale",
            "merchantInvoiceNumber": str(invoice_number)
        }
        headers = {
            "Authorization": self.get_id_token() ,
            "X-APP-Key": bkash_App_Key
        }
        res = requests.post(url, json=payload, headers=headers)
        res.raise_for_status()
        return res.json()


