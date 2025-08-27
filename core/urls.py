from .views import InvoiceViewSet, GetOnlinePayment, CreatePayment, WalletOverView, WalletTransactionViewSet, WithdrawRequestViewSet, PaymentPayOutView, UserPaymentMethodView, PayOutViewSet, VerifyPayment
from .payment.personal_payment import BkashPersonalAgentPaymentView, NagadPersonalAgentPaymentView, RocketPersonalAgentPaymentView
from .payment.bkash import BKashCreatePaymentView, BKashCallbackView, BKashQueryPaymentView
from rest_framework.routers import DefaultRouter
from django.urls import path, include




invoice_router = DefaultRouter()
invoice_router.register(r'invoices', InvoiceViewSet, basename='invoices')

wallet_router = DefaultRouter()
wallet_router.register(r'wallet-transaction', WalletTransactionViewSet, basename='wallet-transaction')
wallet_router.register(r'withdraw-request', WithdrawRequestViewSet, basename='withdraw-request')
wallet_router.register(r'payment-methods', UserPaymentMethodView, basename='payment-methods')
wallet_router.register(r'pay-outs', PayOutViewSet, basename='pay-outs')


urlpatterns = [
    # ===============================================================================================
    # ====================Merchant & Admin Dashboard API URL Start==================================
    # ===============================================================================================
    path('u/wallet/wallet-overview/', WalletOverView, name='wallet-overview'),
    path('u/wallet/', include(wallet_router.urls)),
    path('u/invoice/', include(invoice_router.urls)),

    # ===============================================================================================
    # ====================Merchant & Admin Dashboard API URL End===================================
    # ===============================================================================================
    
    
    
    #API For Payment m2m=================/API key & Secret Key Verify/===========
    path('payment/create/', CreatePayment.as_view(), name='create-payment'),
    path('payment/payout/', PaymentPayOutView.as_view(), name='payment-payout'),
    path('payment/verify/', VerifyPayment.as_view(), name='payment-payout'),
    # ---------------------------SendBox-------------------------------------
    
    #API For Payment m2m=================/Not Authentication Needed/===========
    path('get-payment/', GetOnlinePayment.as_view(), name='get-payment'),
    
    #Bkash Payment Gate URL list==============
    path('get-payment/bkash/', BKashCreatePaymentView.as_view(), name='get-payment-bkash'),
    path('bkash/payment/verify/', BKashQueryPaymentView.as_view(), name='bkash-payment-verify'),
    path('payment/<str:invoice_payment_id>/bkash/callback/', BKashCallbackView.as_view(), name='bkash_callback'),
    
    #Personal Payment URL List==========
    path('get-payment/bkash-payment/', BkashPersonalAgentPaymentView.as_view(), name='bkash-manual-payment'),
    path('get-payment/nagad-payment/', NagadPersonalAgentPaymentView.as_view(), name='nagad-manual-payment'),
    path('get-payment/rocket-payment/', RocketPersonalAgentPaymentView.as_view(), name='rocket-manual-payment'),
    
]

