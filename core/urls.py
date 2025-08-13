from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InvoiceViewSet, GetOnlinePayment, CreatePayment, WalletOverView, WalletTransactionViewSet, WithdrawRequestViewSet, PaymentPayOutView
from .payment.bkash import BKashCreatePaymentView, BKashCallbackView

router = DefaultRouter()
router.register(r'invoice', InvoiceViewSet, basename='invoice')


dashboard_router = DefaultRouter()
dashboard_router.register(r'wallet-transaction', WalletTransactionViewSet, basename='wallet-transaction')
dashboard_router.register(r'withdraw-request', WithdrawRequestViewSet, basename='withdraw-request')


urlpatterns = [
    # ===============================================================================================
    # ====================Merchant & Admin Dashboard API URL Start==================================
    # ===============================================================================================
    path('u/wallet/wallet-overview/', WalletOverView, name='wallet-overview'),
    path('u/wallet/', include(dashboard_router.urls)),


    # ===============================================================================================
    # ====================Merchant & Admin Dashboard API URL End===================================
    # ===============================================================================================
    
    
    path('u/<pid>/', include(router.urls)),
    
    #API For Payment m2m=================/Not Authentication Needed/===========
    path('invoice/<str:invoice_payment_id>/get-payment/', GetOnlinePayment.as_view(), name='get-payment'),
    path('invoice/<str:invoice_payment_id>/get-payment/bkash/', BKashCreatePaymentView.as_view(), name='get-payment-bkash'),
    path('payment/<str:invoice_payment_id>/bkash/callback/', BKashCallbackView.as_view(), name='bkash_callback'),
    
    #API For Payment m2m=================/API key & Secret Key Verify/===========
    path('payment/create/', CreatePayment.as_view(), name='create-payment'),
    path('payment/payout/', PaymentPayOutView.as_view(), name='payment-payout'),
    
    
    
    # path('bkash-grant-token/', bkash_grant_token, name='bkash-grant-token')
    
    
    # path('payment/bkash/callback/', BkashExecutePaymentView.as_view(), name='bkash-callback'),
    
    
    # Invoice URLs
    # path('invoices/', InvoiceViewSet.as_view(), name='invoice-list-create'),
    # path('invoices/<int:pk>/', InvoiceDetailView.as_view(), name='invoice-detail'),

    # Payment Transfer URLs
    # path('payment-transfers/', PaymentTransferListCreateView.as_view(), name='payment-transfer-list-create'),
    # path('payment-transfers/<int:pk>/', PaymentTransferDetailView.as_view(), name='payment-transfer-detail'),

    # # Withdraw Request URLs
    # path('withdraw-requests/', WithdrawRequestListCreateView.as_view(), name='withdraw-request-list-create'),
    # path('withdraw-requests/<int:pk>/', WithdrawRequestDetailView.as_view(), name='withdraw-request-detail'),

    # # Wallet Transaction URLs
    # path('wallet-transactions/', WalletTransactionListCreateView.as_view(), name='wallet-transaction-list-create'),
    # path('wallet-transactions/<int:pk>/', WalletTransactionDetailView.as_view(), name='wallet-transaction-detail'),
]

