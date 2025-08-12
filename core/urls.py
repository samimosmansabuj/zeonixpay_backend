from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InvoiceViewSet, GetOnlinePayment, BKashCreatePaymentView, CreatePayment, BKashCallbackView

router = DefaultRouter()
router.register(r'invoice', InvoiceViewSet, basename='invoice')


urlpatterns = [
    path('<pid>/', include(router.urls)),
    
    path('invoice/<str:payment_uid>/get-payment/', GetOnlinePayment.as_view(), name='get-payment'),
    path('invoice/<str:payment_uid>/get-payment/bkash/', BKashCreatePaymentView.as_view(), name='get-payment-bkash'),
    
    
    path('payment/create/', CreatePayment.as_view(), name='create-payment'),
    path('payment/<str:payment_uid>/bkash/callback/', BKashCallbackView.as_view(), name='bkash_callback'),
    
    
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

