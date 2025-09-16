from .serializers import InvoiceSerializer, PaymentTransferSerializer, WithdrawRequestSerializer, WalletTransactionSerializer, UserPaymentMethodSerializer
from .utils import CustomPaymentSectionViewsets, DataEncryptDecrypt, CustomPagenumberpagination, build_logo_url
from rest_framework.exceptions import NotFound, ValidationError, AuthenticationFailed
from authentication.models import Merchant, APIKey, UserPaymentMethod, StorePaymentMessage
from .models import Invoice, PaymentTransfer, WithdrawRequest, WalletTransaction
from rest_framework.decorators import api_view, permission_classes
from authentication.permissions import MerchantCreatePermission, StaffUpdatePermission, AdminUpdatePermission
from authentication.serializers import MerchantWalletSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import views, status
from django.shortcuts import redirect
from rest_framework import viewsets
from django.urls import reverse
from dotenv import load_dotenv
import os
import json
load_dotenv()
from django.db.models import Q, Sum, Value
from django.db.models.functions import Coalesce
from decimal import Decimal
from .filters import InvoiceFilter, WithdrawRequestFilter, PaymentTransferFilter, UserPaymentMethodFilter, WalletTransactionFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter



# ===============================================================================================
# ====================Merchant Payment Gate API View Start==================================
# ===============================================================================================
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
        
        self._check_domain(request, api_key.merchant)

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
    
    def _check_domain(self, request, merchant):
        request_domain = request.META.get('HTTP_HOST', '').lower()
        allowed_domains = merchant.domain_name if isinstance(merchant.domain_name, list) else [merchant.domain_name]
        
        if not any(request_domain.endswith(allowed_domain) for allowed_domain in allowed_domains):
            raise AuthenticationFailed(f"Access denied from domain {request_domain}.")
    
    def get_accepted_method(self):
        return ["bkash", "nagad", "rocket", "bkash-personal", "bkash-agent", "nagad-personal", "nagad-agent", "rocket-personal", "rocket-agent"]
    
    
    def post(self, request, *args, **kwargs):
        try:
            print("Payment Created Function Start....")
            merchant = self.authenticate_using_api_key_and_secret(request)
            serializer = InvoiceSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(merchant=merchant)
            invoice = serializer.instance
            if invoice.method and invoice.method.lower() in self.get_accepted_method():
                if invoice.method.lower() == "bkash":
                    base = reverse('get-payment')
                    url = f"{request.build_absolute_uri(base)}?invoice_payment_id={invoice.invoice_payment_id}&method={invoice.method}"
                    # url = f"{reverse('get-payment')}?invoice_payment_id={invoice.invoice_payment_id}&method={invoice.method}"
                    paymentURL = url
                elif invoice.method.lower() == "nagad":
                    paymentURL = f"{os.getenv('PAYMENT_SITE_BASE_URL')}?invoice_payment_id={invoice.invoice_payment_id}&method={invoice.method}"
                elif invoice.method.lower() == "rocket":
                    paymentURL = f"{os.getenv('PAYMENT_SITE_BASE_URL')}?invoice_payment_id={invoice.invoice_payment_id}&method={invoice.method}"
                else:
                    paymentURL = f"{os.getenv('PAYMENT_SITE_BASE_URL')}?invoice_payment_id={invoice.invoice_payment_id}"
            else:
                paymentURL = f"{os.getenv('PAYMENT_SITE_BASE_URL')}?invoice_payment_id={invoice.invoice_payment_id}"
            print("Payment Created Function End....")
            print("Payment URL is: ", paymentURL)
            return Response(
                {
                    "statusMessage": "Successful",
                    "paymentID": f"{invoice.invoice_payment_id}",
                    "paymentURL": paymentURL,
                    "callbackURL": f"{invoice.callback_url}",
                    "successCallbackURL": f"{invoice.callback_url}?invoice_payment_id={invoice.invoice_payment_id}&paymentStatus=success",
                    "failureCallbackURL": f"{invoice.callback_url}?invoice_payment_id={invoice.invoice_payment_id}&paymentStatus=failure",
                    "cancelledCallbackURL": f"{invoice.callback_url}?invoice_payment_id={invoice.invoice_payment_id}&paymentStatus=cancel",
                    "amount": f"{invoice.customer_amount}",
                    "paymentCreateTime": f"{invoice.created_at}",
                    "transactionStatus": "Initiated",
                    "merchantInvoiceNumber": f"{invoice.merchant.merchant_id}"
                }, status=status.HTTP_200_OK
            )
        except Exception as e:
            print("Getting Some Problem...:", e)
            return Response(
                {
                    'status': False,
                    'message': str(e)
                }
            )

class PaymentPayOutView(views.APIView):
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
                    "status": True,
                    "payoutID": f"{serializer.instance.trx_uuid}",
                    "method": f"{serializer.instance.payment_method}",
                    "amount": f"{serializer.instance.amount}",
                    "payoutCreateTime": f"{serializer.instance.created_at}",
                    "transactionStatus": f"{serializer.instance.status}",
                    "merchantId": f"{serializer.instance.merchant.merchant_id}"
                }, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'message': str(e)
                }
            )

class GetOnlinePayment(views.APIView):
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

class VerifyPayment(views.APIView):
    def post(self, request, *args, **kwargs):
        status_params = request.data.get("status")
        invoice_payment_id = request.data.get("invoice_payment_id")
        if not invoice_payment_id:
            return Response(
                {
                    "status": False,
                    "message": "Invoice Payment ID must be given!"
                }, status=status.HTTP_400_BAD_REQUEST
            )
        elif not status_params:
            return Response(
                {
                    "status": False,
                    "message": "Status must be given!"
                }, status=status.HTTP_400_BAD_REQUEST
            )
        elif invoice_payment_id and status:
            if not Invoice.objects.filter(invoice_payment_id=invoice_payment_id).exists():
                return Response(
                    {
                        "status": False,
                        "message": "Invalid Invoice Payment ID!"
                    }, status=status.HTTP_400_BAD_REQUEST
                )
            else:
                invoice = Invoice.objects.get(invoice_payment_id=invoice_payment_id)
                callback_url = f"{invoice.callback_url}?invoice_payment_id={invoice.invoice_payment_id}&trxID={invoice.transaction_id}&amount={invoice.customer_amount}&paymentStatus={invoice.pay_status}&created_at={invoice.created_at}"
                return Response(
                    {
                        "status": True if invoice.pay_status == "Paid" else False,
                        "data": {
                            "invoice_payment_id": invoice.invoice_payment_id,
                            "trxID": invoice.transaction_id,
                            "amount": invoice.customer_amount,
                            "transactionStatus": "Complete" if invoice.pay_status == "paid" else "Incomplete",
                            "client_callback_url": callback_url if invoice.callback_url else None
                        }
                    }, status=status.HTTP_200_OK
                )
        else:
            return Response(
                {
                    "status": False,
                    "message": "Something wrong!"
                }, status=status.HTTP_400_BAD_REQUEST
            )

# ===============================================================================================
# ====================Merchant Payment Gate API View Start==================================
# # ===============================================================================================









# ===============================================================================================
# ====================Merchant & Admin Dashboard API View Start==================================
# ===============================================================================================

class InvoiceViewSet(CustomPaymentSectionViewsets):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated, MerchantCreatePermission]
    pagination_class = CustomPagenumberpagination
    model = Invoice
    lookup_field = 'invoice_payment_id'
    
    search_fields = [
        'invoice_payment_id', 'customer_name', 'customer_number',
        'customer_email', 'customer_address', 'customer_description',
        'transaction_id', 'invoice_trxn', 'method', 'note'
    ]
    ordering_fields = ['created_at', 'customer_amount', 'status', 'pay_status', 'id']
    filterset_class = InvoiceFilter
    
    create_success_message = "Invoice Created!"
    update_success_message = "Invoice Updated!"
    delete_success_message = "Invoice Deleted!"
    not_found_message = "No Invoice Object Found!"
    # ordering_by = "-id"
    
    def get_total_amount(self, queryset):
        total_amount = queryset.aggregate(total=Sum("customer_amount"))["total"] or 0
        status_sums = (
            queryset.values("pay_status")
            .annotate(total=Sum("customer_amount"))
            .order_by()
        )
        reseult = {
            "total_amount": total_amount,
            "paid_amount": 0,
            "pending_amount": 0,
            "unpaid_amount": 0,
            "failed_amount": 0,
            "cancelled_amount": 0,
        }
        for row in status_sums:
            key = f"{row['pay_status']}_amount"
            reseult[key] = row["total"] or 0
        
        return reseult
    
    def get_queryset(self):
        merchant = self.get_merchant()
        if merchant:
            return self.model.objects.filter(merchant=merchant).order_by(self.ordering_by)
        else:
            if self.get_user().role.name.lower() == 'admin':
                return self.queryset
            elif self.get_user().role.name.lower() == 'staff':
                staff_all_device = self.get_user().staff_device_key.all()
                verified_invoices = StorePaymentMessage.objects.filter(
                    device__in=staff_all_device,
                    is_verified=True,
                    verified_invoice__isnull=False
                ).values_list('verified_invoice', flat=True).distinct()
                return self.model.objects.filter(id__in=verified_invoices)
            else:
                return None
    
    def get_object(self):
        try:
            return self.get_queryset().get(invoice_payment_id=self.kwargs.get('invoice_payment_id'))
        except self.model.DoesNotExist:
            raise NotFound(self.not_found_message)
    
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
            # call_back_url_json = {
            #     "success_url": post_data.get("success_url", ""),
            #     "cancel_url": post_data.get("cancel_url", ""),
            #     "failed_url": post_data.get("failed_url", "")
            # }
            # post_data['data'] = json.dumps(call_back_url_json)
            # data = self.json_encrypted(post_data)
            serializer = self.get_serializer(data=post_data)
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

    def destroy_response(self, object):
        if object.status.lower() == 'active' and object.pay_status.lower() in ['pending', 'unpaid']:
            object.status = 'delete'
            object.save()
            return True , Response(
                {
                    'status': True,
                    'message': self.delete_success_message,
                }, status=status.HTTP_200_OK
            )
        return f"This Invoice is {object.status}. Can't Delete!", None

class WithdrawRequestViewSet(CustomPaymentSectionViewsets):
    queryset = WithdrawRequest.objects.none()
    permission_classes = [IsAuthenticated, MerchantCreatePermission]
    update_permission_classes = [IsAuthenticated, AdminUpdatePermission]
    serializer_class = WithdrawRequestSerializer
    
    search_fields = ['trx_id', 'trx_uuid', 'message', 'note']
    ordering_fields = ['created_at', 'updated_at', 'amount', 'status', 'id']
    filterset_class = WithdrawRequestFilter
    
    model = WithdrawRequest
    create_success_message = "Withdraw Request Submit!"
    update_success_message = "Withdraw Request status update!"
    delete_success_message = "Withdraw Request Deleted!"
    not_found_message = "No Wallet Request found!"
    create_permission_denied_message = 'Only Merchant user can Request for Withdraw!'
    ordering_by = "-created_at"
    lookup_field = 'trx_uuid'
    
    def get_permissions(self):
        print(self.action)
        if self.action in ["update", "partial_update"]:
            return [permission() for permission in self.update_permission_classes]
        return [permission() for permission in self.permission_classes]
    
    def get_total_amount(self, queryset):
        total_amount = queryset.aggregate(total=Sum("amount"))["total"] or 0
        status_sums = (
            queryset.values("status")
            .annotate(total=Sum("amount"))
            .order_by()
        )
        reseult = {
            "total_amount": total_amount,
            "pending_amount": 0,
            "success_amount": 0,
            "rejected_amount": 0,
            "delete_amount": 0
        }
        for row in status_sums:
            key = f"{row['status']}_amount"
            reseult[key] = row["total"] or 0
        
        return reseult
    
    def get_object(self):
        try:
            return self.get_queryset().get(trx_uuid=self.kwargs.get('trx_uuid'))
        except self.model.DoesNotExist:
            raise NotFound(self.not_found_message)

    def destroy_response(self, object):
        if object.status.lower() == 'pending':
            object.status = 'delete'
            object.save()
            return True , Response(
                {
                    'status': True,
                    'message': self.delete_success_message,
                }, status=status.HTTP_200_OK
            )
        return f"This Withdrawal Request is {object.status}. Can't Delete!", None

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            user = request.user
            if user.role.name == 'Admin':
                serializer = self.get_serializer(instance, data=request.data, partial=True)
            elif user.role.name == 'Merchant':
                data = request.data.copy()
                if "status" in data or "trx_id" in data:
                    return Response(
                        {
                            "status": False,
                            "message": "Merchant users cannot update status or trx_id."
                        }, status=status.HTTP_400_BAD_REQUEST
                    )
                serializer = self.get_serializer(instance, data=data, partial=True)
            else:
                return Response(
                    {
                        "status": False,
                        "message": "You do not have permission to update this request."
                    }, status=status.HTTP_400_BAD_REQUEST
                )

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
        
        except NotFound as e:
            return Response(
                {
                    'status': False,
                    'error': str(e)
                },
                status=status.HTTP_404_NOT_FOUND
            ) 
        
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'message': str(e),
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UserPaymentMethodView(CustomPaymentSectionViewsets):
    queryset = UserPaymentMethod.objects.none
    permission_classes = [IsAuthenticated, MerchantCreatePermission]
    serializer_class = UserPaymentMethodSerializer
    
    search_fields = ['method_type']
    ordering_fields = ['created_at', 'status', 'is_primary', 'id']
    filterset_class = UserPaymentMethodFilter
    
    model = UserPaymentMethod
    create_success_message = "Payment Method Created!"
    update_success_message = "Payment Method Updated!"
    delete_success_message = "Payment Method Deleted!"
    not_found_message = "No Payment Method Found!"
    create_permission_denied_message = 'Only Merchant user can Add Payment Method!'
    ordering_by = "-created_at"
    lookup_field = 'pk'
    
    
    def get_total_amount(self, queryset):
        return None
    
    def get_queryset(self):
        merchant = self.get_merchant()
        if merchant:
            return self.model.objects.filter(merchant=merchant).order_by(self.ordering_by)
        else:
            return self.model.objects.none()
    
    def get_object(self):
        try:
            return self.get_queryset().get(pk=self.kwargs.get('pk'))
        except self.model.DoesNotExist:
            raise NotFound(self.not_found_message)
    
    
    @action(methods=['patch', 'put'], detail=True, url_path='set-primary')
    def set_primary(self, request, *args, **kwargs):
        try:
            object = self.get_object()
            object.is_primary = True
            object.save()
            return Response(
                {
                    'status': True,
                    'message': "Primary Payment Method Set Successfully!"
                }, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'message': str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(methods=['patch', 'put'], detail=True, url_path='set-active-deactive')
    def active_deactive(self, request, *args, **kwargs):
        try:
            object = self.get_object()
            if object.status.lower() == 'active':
                object.status = 'deactive'
                message = "Payment Method Deactive Successfully!"
            elif object.status.lower() == 'deactive':
                object.status = 'active'
                message = "Payment Method Active Successfully!"
            object.save()
            return Response(
                {
                    'status': True,
                    'message': message
                }, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'message': str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )
    
    
    def destroy(self, request, *args, **kwargs):
        try:
            object = self.get_object()
            object.delete()
            return Response(
                {
                    'status': True,
                    'message': self.delete_success_message
                }, status=status.HTTP_200_OK
            )
        except NotFound as e:
            return Response(
                {
                    'status': False,
                    'error': str(e)
                },
                status=status.HTTP_404_NOT_FOUND
            ) 
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'message': str(e),
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class PayOutViewSet(CustomPaymentSectionViewsets):
    queryset = PaymentTransfer.objects.all()
    permission_classes = [IsAuthenticated, StaffUpdatePermission]
    serializer_class = PaymentTransferSerializer
    
    search_fields = [
        'trx_id', 'trx_uuid', 'receiver_name', 'receiver_number', 'note'
    ]
    ordering_fields = ['created_at', 'amount', 'status', 'payment_method', 'id']
    filterset_class = PaymentTransferFilter
    
    model = PaymentTransfer
    create_success_message = "Payout Created!"
    update_success_message = "Payout Updated!"
    delete_success_message = "Payout Deleted!"
    not_found_message = "No Payout Found!"
    create_permission_denied_message = 'Only Merchant user can request for Payout!'
    ordering_by = "-created_at"
    lookup_field = 'trx_uuid'
    
    def get_total_amount(self, queryset):
        total_amount = queryset.aggregate(total=Sum("amount"))["total"] or 0
        status_sums = (
            queryset.values("status")
            .annotate(total=Sum("amount"))
            .order_by()
        )
        reseult = {
            "total_amount": total_amount,
            "pending_amount": 0,
            "success_amount": 0,
            "rejected_amount": 0,
            "delete_amount": 0
        }
        for row in status_sums:
            key = f"{row['status']}_amount"
            reseult[key] = row["total"] or 0
        
        return reseult
    
    def get_queryset(self):
        merchant = self.get_merchant()
        if merchant:
            return self.model.objects.filter(merchant=merchant).order_by(self.ordering_by)
        else:
            if self.get_user().role.name.lower() == 'admin':
                return self.queryset
            elif self.get_user().role.name.lower() == 'staff':
                
                return self.model.objects.filter(Q(confirm_by=self.get_user()) | Q(status="pending"))
            else:
                return None
    
    def create(self, request, *args, **kwargs):
        return Response(
            {
                'status': False,
                'message': 'Payout Request not accept manually!'
            }
        )
    
    def perform_update(self, serializer):
        if self.request.user.role.name.lower() == "staff":
            trx_id = serializer.validated_data.get("trx_id")
            status = serializer.validated_data.get("status")
            if trx_id and status.lower() == "success":
                return serializer.save(confirm_by=self.request.user)
            return serializer.save()
        elif self.request.user.role.name.lower() == "admin":
            selected_confirm_by = serializer.validated_data.get('confirm_by')            
            if selected_confirm_by is None:
                raise Exception("Confirm By field cannot be None.")
            
            if selected_confirm_by.role.name.lower() != "staff":
                raise Exception("Admin must select a Confirm By Staff user to assign the confirm payout.")
            return serializer.save()
        else:
            raise Exception("Only Staff can confirm payout.")
    
    def get_object(self):
        try:
            return PaymentTransfer.objects.get(trx_uuid=self.kwargs.get('trx_uuid'))
        except PaymentTransfer.DoesNotExist:
            raise NotFound(self.not_found_message)
    
    def destroy_response(self, object):
        if object.status.lower() == 'pending':
            object.status = 'delete'
            object.save()
            return True , Response(
                {
                    'status': True,
                    'message': self.delete_success_message,
                }, status=status.HTTP_200_OK
            )
        return f"This Payout Request is {object.status}. Can't Delete!", None

class WalletTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WalletTransaction.objects.none()
    serializer_class = WalletTransactionSerializer
    pagination_class = CustomPagenumberpagination
    permission_classes = [IsAuthenticated]
    lookup_field = 'trx_uuid'

    #filtering section====
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['merchant__brand_name', 'trx_id', 'method', 'tran_type']
    # ordering_fields = ['created_at', 'updated_at', 'amount', 'status', 'id']
    filterset_class = WalletTransactionFilter
    
    model = WalletTransaction
    ordering_by = "-created_at"
    
    def get_merchant(self):
        user = self.request.user
        return Merchant.objects.get(user=user) if Merchant.objects.filter(user=user).exists() else None
    
    def get_queryset(self):
        merchant = self.get_merchant()
        user = self.request.user
        if merchant:
            return self.model.objects.filter(merchant=merchant).order_by(self.ordering_by)
        else:
            if user.role.name.lower() == 'admin':
                return self.model.objects.all().order_by(self.ordering_by)
            elif user.role.name.lower() == 'staff':
                payment_transfer_qs = PaymentTransfer.objects.filter(confirm_by=user).values('id')
                payment_transfer_qs = Q(content_type__model='paymenttransfer', object_id__in=payment_transfer_qs)
                
                verified_invoices = StorePaymentMessage.objects.filter(
                    device__in=user.staff_device_key.all(),
                    is_verified=True,
                    verified_invoice__isnull=False
                ).values_list('verified_invoice', flat=True).distinct()
                invoice_qs = Invoice.objects.filter(id__in=verified_invoices).values('id')
                invoice_qs = Q(content_type__model='invoice', object_id__in=invoice_qs)
                
                combined_qs = payment_transfer_qs | invoice_qs
                return self.model.objects.filter(combined_qs).order_by(self.ordering_by)
            else:
                return None
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if queryset is None:
            return Response(
                {
                    'status': True,
                    'message': "Can't Get Wallet Transaction with this User!"
                }
            )
        
        all_items = request.query_params.get('all', 'false').lower() == 'true'
        page_size = request.query_params.get(self.pagination_class.page_size_query_param)
        
        
        if all_items or (page_size and page_size.isdigit() and int(page_size)==0):
        # if all_items:
            try:
                response = self.get_serializer(queryset, many=True)
                return Response(
                    {
                        'status': True,
                        'count': len(response.data),
                        'data': response.data
                    },
                    status=status.HTTP_200_OK
                )
            except Exception as e:
                return Response(
                    {
                        'status': False,
                        'error': str(e)
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            response = self.get_serializer(page, many=True)
            return Response(
                {
                    'status': True,
                    'count': self.paginator.page.paginator.count,
                    'next': self.paginator.get_next_link(),
                    'previous': self.paginator.get_previous_link(),
                    'data': response.data
                },
                status=status.HTTP_200_OK
            )
        else:
            try:
                response = self.get_serializer(queryset, many=True)
                return Response(
                    {
                        'status': True,
                        'count': len(response.data),
                        'data': response.data
                    },
                    status=status.HTTP_200_OK
                )
            except Exception as e:
                return Response(
                    {
                        'status': False,
                        'error': str(e)
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
    
    def get_object(self):
        try:
            return self.get_queryset().get(trx_uuid=self.kwargs.get('trx_uuid'))
        except self.model.DoesNotExist:
            raise NotFound("Wallet Transaction not found!")
        except Exception as e:
            raise ValidationError(str(e))
    
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_serializer(self.get_object()).data
            return Response(
                {
                    'status': True,
                    'data': instance
                }, status=status.HTTP_200_OK
            )
        except NotFound as e:
            return Response(
                {
                    'status': False,
                    'message': str(e)
                }
            )
        except ValidationError as e:
            return Response(
                {
                    'status': False,
                    'message': str(e[0])
                }
            )



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def WalletOverView(request):
    user = request.user
    role = (getattr(getattr(user, 'role', None), 'name', '') or '').lower()
    
    wallet_data = None
    dashboard = None
    zero = Value(Decimal('0.00'))
    
    if role == "merchant":
        merchant = Merchant.objects.filter(user=user).select_related('merchant_wallet').first()
        if not merchant:
            return Response({'status': True, 'wallet': None, 'dashboard_accountant_card': None})
        
        if getattr(merchant, 'merchant_wallet', None):
            wallet_data = MerchantWalletSerializer(merchant.merchant_wallet).data
                
        invoice_total = Invoice.objects.filter(merchant=merchant)\
            .exclude(status__iexact='delete')\
            .aggregate(total=Coalesce(Sum('customer_amount'), zero))['total']
        
        pending_invoice_total = Invoice.objects.filter(merchant=merchant)\
            .exclude(status__iexact='delete')\
            .filter(pay_status__in=['pending', 'unpaid'])\
            .aggregate(total=Coalesce(Sum('customer_amount'), zero))['total']
        
        withdraw_total = WithdrawRequest.objects.filter(merchant=merchant)\
            .exclude(status__iexact='delete')\
            .aggregate(total=Coalesce(Sum('amount'), zero))['total']
        
        payout_total = PaymentTransfer.objects.filter(merchant=merchant)\
            .exclude(status__iexact='delete')\
            .aggregate(total=Coalesce(Sum('amount'), zero))['total']
        
        dashboard = {
            "invoice_amount": invoice_total,
            "pending_invoice_amount": pending_invoice_total,
            "withdrawrequest_amount": withdraw_total,
            "payout_amount": payout_total,
        }
        
        return Response(
            {
                'status': True,
                'wallet': wallet_data,
                'dashboard_accountant_card': dashboard
            }
        )
    elif role == "staff":
        confirmed_payout_amount = (PaymentTransfer.objects
                                   .filter(confirm_by=user)
                                   .exclude(status__iexact='delete')
                                   .aggregate(total=Coalesce(Sum('amount'), zero))['total'])
        
        staff_devices = user.staff_device_key.all()
        verified_invoice_ids = (StorePaymentMessage.objects
                                .filter(device__in=staff_devices, is_verified=True)
                                .exclude(verified_invoice__isnull=True)
                                .values_list('verified_invoice', flat=True)
                                .distinct())
        verified_invoice_amount = (Invoice.objects
                                   .filter(id__in=verified_invoice_ids)
                                   .exclude(status__iexact='delete')
                                   .aggregate(total=Coalesce(Sum('customer_amount'), zero))['total'])
        dashboard = {
            "confirmed_payout_amount": confirmed_payout_amount,
            "verified_invoice_amount": verified_invoice_amount,
        }
        return Response({'status': True, 'wallet': None, 'dashboard_accountant_card': dashboard})
    elif role == "admin":        
        withdraw_total = WithdrawRequest.objects.exclude(status__iexact='delete')\
            .aggregate(total=Coalesce(Sum('amount'), zero))['total']

        payout_total = PaymentTransfer.objects.exclude(status__iexact='delete')\
            .aggregate(total=Coalesce(Sum('amount'), zero))['total']

        pending_withdraw_total = WithdrawRequest.objects.filter(status__iexact='pending')\
            .aggregate(total=Coalesce(Sum('amount'), zero))['total']

        pending_payout_total = PaymentTransfer.objects.filter(status__iexact='pending')\
            .aggregate(total=Coalesce(Sum('amount'), zero))['total']

        wallet_fee_total = WalletTransaction.objects.aggregate(total=Coalesce(Sum('fee'), zero))['total']

        dashboard = {
            "withdrawrequest_amount": withdraw_total,
            "paymenttransfer_amount": payout_total,
            "pending_withdrawrequest_amount": pending_withdraw_total,
            "pending_paymenttransfer_amount": pending_payout_total,
            "wallettransaction_fee_amount": wallet_fee_total,
        }

        return Response({
            'status': True,
            'wallet': None,
            'dashboard_accountant_card': dashboard
        })
    else:
        return Response(
            {
                'status': True,
                'data': "Wrong User!"
            }
        )


# ===============================================================================================
# ====================Merchant & Admin Dashboard API View End===================================
# ===============================================================================================

