from .serializers import InvoiceSerializer, PaymentTransferSerializer, WithdrawRequestSerializer, WalletTransactionSerializer, UserPaymentMethodSerializer
from .utils import CustomPaymentSectionViewsets, DataEncryptDecrypt, CustomPagenumberpagination
from rest_framework.exceptions import NotFound, ValidationError, AuthenticationFailed
from authentication.models import Merchant, APIKey, UserPaymentMethod
from .models import Invoice, PaymentTransfer, WithdrawRequest, WalletTransaction
from rest_framework.decorators import api_view, permission_classes
from authentication.permissions import MerchantCreatePermission
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
        
        # self._check_domain(request, api_key.merchant)

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
    
    # def _check_domain(self, request, merchant):
    #     request_domain = request.META.get('HTTP_HOST', '').lower()
    #     allowed_domains = merchant.domain_name if isinstance(merchant.domain_name, list) else [merchant.domain_name]
        
    #     if not any(request_domain.endswith(allowed_domain) for allowed_domain in allowed_domains):
    #         raise AuthenticationFailed(f"Access denied from domain {request_domain}.")
    
    def post(self, request, *args, **kwargs):
        try:
            merchant = self.authenticate_using_api_key_and_secret(request)
            post_data = request.data.copy()
            # call_back_url_json = {
            #     "success_url": post_data.get("success_url", ""),
            #     "cancel_url": post_data.get("cancel_url", ""),
            #     "failed_url": post_data.get("failed_url", "")
            # }
            # post_data['data'] = json.dumps(call_back_url_json)
            serializer = InvoiceSerializer(data=post_data)
            serializer.is_valid(raise_exception=True)
            serializer.save(merchant=merchant)
            invoice = serializer.instance
            
            if invoice.method:
                if invoice.method.lower() == 'bkash':
                    # url = f"{reverse('get-payment-bkash')}?invoice_payment_id={invoice.invoice_payment_id}"
                    # return redirect(f"{url}?redirect=1")
                    
                    url = f"{reverse('get-payment')}?invoice_payment_id={invoice.invoice_payment_id}&method=bkash"
                    return redirect(url)
                elif invoice.method.lower() == 'nagad':
                    return Response(
                        {
                            'message': 'Redirect Nagad Payment Gateway URL!'
                        }
                    )
            else:
                # return redirect(f"{reverse('get-payment')}?invoice_payment_id={invoice.invoice_payment_id}")
                
                return redirect(f"{os.getenv("PAYMENT_SITE_BASE_URL")}/payment/?invoice_payment_id={invoice.invoice_payment_id}")
                # return redirect(f"http://192.168.68.106:3000/payment/?invoice_payment_id={invoice.invoice_payment_id}")
        except Exception as e:
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
    
    def get_all_payment_method(self, invoice_payment_id):
        payment_methods = [
            {
                "method": "bkash",
                "url": f"<a href=f'{self.request.build_absolute_uri(reverse('get-payment-bkash'))}?invoice_payment_id={invoice_payment_id}&redirect=1'>Bkash</a>"
            },
            {
                "method": "bkash-personal",
                "url": f"<a href=f'{self.request.build_absolute_uri(reverse('bkash-manual-payment'))}?method=bkash-personal&invoice_payment_id={invoice_payment_id}'>Bkash Personal</a>"
            },
            {
                "method": "bkash-agent",
                "url": f"<a href=f'{self.request.build_absolute_uri(reverse('bkash-manual-payment'))}?method=bkash-agent&invoice_payment_id={invoice_payment_id}'>Bkash Agent</a>"
            },

            {
                "method": "nagad-personal",
                "url": f"<a href=f'{self.request.build_absolute_uri(reverse('nagad-manual-payment'))}?method=nagad-personal&invoice_payment_id={invoice_payment_id}'>Nagad Personal</a>"
            },
            {
                "method": "nagad-agent",
                "url": f"<a href=f'{self.request.build_absolute_uri(reverse('nagad-manual-payment'))}?method=nagad-agent&invoice_payment_id={invoice_payment_id}'>Nagad Agent</a>"
            },
            
            {
                "method": "rocket-personal",
                "url": f"<a href=f'{self.request.build_absolute_uri(reverse('rocket-manual-payment'))}?method=rocket-personal&invoice_payment_id={invoice_payment_id}'>Rocket Personal</a>"
            },
            {
                "method": "rocket-agent",
                "url": f"<a href=f'{self.request.build_absolute_uri(reverse('rocket-manual-payment'))}?method=rocket-agent&invoice_payment_id={invoice_payment_id}'>Rocket Agent</a>"
            },
            
            {"method": "bank", "url": "Bank"}
        ]
        return payment_methods
    
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
                'brand_logo': invoice.merchant.brand_logo or None
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
    
    create_success_message = "Invoice Created!"
    update_success_message = "Invoice Updated!"
    delete_success_message = "Invoice Deleted!"
    not_found_message = "No Invoice Object Found!"
    ordering_by = "-id"
    
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
    queryset = WithdrawRequest.objects.all()
    permission_classes = [IsAuthenticated, MerchantCreatePermission]
    pagination_class = None
    serializer_class = WithdrawRequestSerializer
    
    model = WithdrawRequest
    create_success_message = "Withdraw Request Submit!"
    update_success_message = "Withdraw Request status update!"
    delete_success_message = "Withdraw Request Deleted!"
    not_found_message = "No Wallet Request found!"
    create_permission_denied_message = 'Only Merchant user can Request for Withdraw!'
    ordering_by = "-created_at"
    lookup_field = 'trx_uuid'
    
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


class UserPaymentMethodView(CustomPaymentSectionViewsets):
    queryset = UserPaymentMethod.objects.none
    permission_classes = [IsAuthenticated, MerchantCreatePermission]
    pagination_class = None
    serializer_class = UserPaymentMethodSerializer
    
    model = UserPaymentMethod
    create_success_message = "Payment Method Created!"
    update_success_message = "Payment Method Updated!"
    delete_success_message = "Payment Method Deleted!"
    not_found_message = "No Payment Method Found!"
    create_permission_denied_message = 'Only Merchant user can Add Payment Method!'
    ordering_by = "-created_at"
    lookup_field = 'pk'
    
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


class WalletTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WalletTransaction.objects.none
    serializer_class = WalletTransactionSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'trx_uuid'
    
    model = WalletTransaction
    ordering_by = "-created_at"
    
    def get_merchant(self):
        user = self.request.user
        merchant = Merchant.objects.get(user=user) if Merchant.objects.filter(user=user).exists() else None
        if merchant:
            return merchant
        else:
            return None
    
    def get_queryset(self):
        merchant = self.get_merchant()
        if merchant:
            return self.model.objects.filter(merchant=merchant).order_by(self.ordering_by)
        else:
            user = self.request.user
            if user.role.name.lower() == 'admin':
                return self.model.objects.all()
            else:
                return None
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if queryset is None:
            return Response(
                {
                    'status': True,
                    'message': "Can't Get Wallet Transaction with this User!"
                }
            )
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                'status': True,
                'count': len(serializer.data),
                'data': serializer.data
            }
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
            instance = self.get_object()
            return Response(
                {
                    'status': True,
                    'data': self.get_serializer(instance).data
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


class PayOutViewSet(CustomPaymentSectionViewsets):
    queryset = PaymentTransfer.objects.all()
    permission_classes = [IsAuthenticated, MerchantCreatePermission]
    pagination_class = None
    serializer_class = PaymentTransferSerializer
    
    model = PaymentTransfer
    create_success_message = "Payout Created!"
    update_success_message = "Payout Updated!"
    delete_success_message = "Payout Deleted!"
    not_found_message = "No Payout Found!"
    create_permission_denied_message = 'Only Merchant user can request for Payout!'
    ordering_by = "-created_at"
    lookup_field = 'trx_uuid'
    
    def create(self, request, *args, **kwargs):
        return Response(
            {
                'status': False,
                'message': 'Payout Request not accept manually!'
            }
        )
    
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
        return f"This Payout Request is {object.status}. Can't Delete!", None

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def WalletOverView(request):
    user = request.user
    if user.merchant:
        wallet = user.merchant.merchant_wallet
        serializer = MerchantWalletSerializer(wallet)
        return Response(
            {
                'status': True,
                'data': serializer.data
            }
        )
    else:
        return Response(
            {
                'status': True,
                'data': None
            }
        )

# ===============================================================================================
# ====================Merchant & Admin Dashboard API View End===================================
# ===============================================================================================

