from rest_framework.response import Response
from dotenv import load_dotenv
from django.core.cache import cache
import os
import requests

load_dotenv()

BKASH_BASE_URL = os.getenv("BKASH_BASE_URL")
BKASH_APP_KEY = os.getenv("BKASH_APP_KEY")
BKASH_APP_SECRET = os.getenv("BKASH_APP_SECRET")
BKASH_USERNAME = os.getenv("BKASH_USERNAME")
BKASH_PASSWORD = os.getenv("BKASH_PASSWORD")
BKASH_CALLBACK_URL = os.getenv("BKASH_CALLBACK_URL")

BKASH_ID_TOKEN_CACHE_KEY = "bkash:id_token"
BKASH_REFRESH_TOKEN_CACHE_KEY = "bkash:refresh_token"
BKASH_ID_TOKEN_TTL = 55 * 60
BKASH_REFRESH_TOKEN_TTL = 24 * 60 * 60



class BKashError(Exception):
    pass

class BKashClient:
    def __init__(self):
        self.base = f"{BKASH_BASE_URL}tokenized/checkout/"
        self.app_key = BKASH_APP_KEY
        self.app_secret = BKASH_APP_SECRET
        self.username = BKASH_USERNAME
        self.password = BKASH_PASSWORD

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
        # Try refresh
        refresh_token = cache.get(BKASH_REFRESH_TOKEN_CACHE_KEY)
        if refresh_token:
            try:
                return self._refresh_token(refresh_token)
            except Exception:
                pass
        # Fallback to grant
        return self._grant_token()

    def _headers_auth(self):
        return {
            "Authorization": self._authorization(),
            "X-APP-Key": self.app_key,
            "Content-Type": "application/json"
        }

    # ------- payment endpoints -------
    def create_payment(self, *, amount, intent, merchant_invoice_number, payer_reference=None, mode="0011", agreement_id=None, callback_url=None):
        url = f"{self.base}create"
        payload = {
            "mode": mode,  # tokenization mode per bKash docs (sandbox often "0011")
            "callbackURL": callback_url or BKASH_CALLBACK_URL,
            "amount": str(amount),
            "currency": "BDT",
            "intent": intent,
            "merchantInvoiceNumber": merchant_invoice_number,
        }
        if payer_reference:
            payload["payerReference"] = str(payer_reference)
        if agreement_id:
            payload["agreementID"] = agreement_id

        r = requests.post(url, json=payload, headers=self._headers_auth(), timeout=30)
        if r.status_code != 200:
            raise BKashError(f"Create payment failed: {r.status_code} {r.text}")
        return r.json()

    def execute_payment(self, payment_id: str):
        url = self.base + "execute"
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


