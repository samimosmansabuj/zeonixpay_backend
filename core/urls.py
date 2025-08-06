from django.urls import path
from .views import (
    InvoiceListCreateView, InvoiceDetailView,
    PaymentTransferListCreateView, PaymentTransferDetailView,
    WithdrawRequestListCreateView, WithdrawRequestDetailView,
    WalletTransactionListCreateView, WalletTransactionDetailView,
)

urlpatterns = [
    # Invoice URLs
    path('invoices/', InvoiceListCreateView.as_view(), name='invoice-list-create'),
    path('invoices/<int:pk>/', InvoiceDetailView.as_view(), name='invoice-detail'),

    # Payment Transfer URLs
    path('payment-transfers/', PaymentTransferListCreateView.as_view(), name='payment-transfer-list-create'),
    path('payment-transfers/<int:pk>/', PaymentTransferDetailView.as_view(), name='payment-transfer-detail'),

    # Withdraw Request URLs
    path('withdraw-requests/', WithdrawRequestListCreateView.as_view(), name='withdraw-request-list-create'),
    path('withdraw-requests/<int:pk>/', WithdrawRequestDetailView.as_view(), name='withdraw-request-detail'),

    # Wallet Transaction URLs
    path('wallet-transactions/', WalletTransactionListCreateView.as_view(), name='wallet-transaction-list-create'),
    path('wallet-transactions/<int:pk>/', WalletTransactionDetailView.as_view(), name='wallet-transaction-detail'),
]

