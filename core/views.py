from rest_framework import generics, permissions
from .models import Invoice, PaymentTransfer, WithdrawRequest, WalletTransaction
from .serializers import InvoiceSerializer, PaymentTransferSerializer, WithdrawRequestSerializer, WalletTransactionSerializer


# Invoice Views
class InvoiceListCreateView(generics.ListCreateAPIView):
    queryset = Invoice.objects.all().order_by('-id')
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class InvoiceDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]


# Payment Transfer Views
class PaymentTransferListCreateView(generics.ListCreateAPIView):
    queryset = PaymentTransfer.objects.all().order_by('-id')
    serializer_class = PaymentTransferSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PaymentTransferDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PaymentTransfer.objects.all()
    serializer_class = PaymentTransferSerializer
    permission_classes = [permissions.IsAuthenticated]


# Withdraw Request Views
class WithdrawRequestListCreateView(generics.ListCreateAPIView):
    queryset = WithdrawRequest.objects.all().order_by('-id')
    serializer_class = WithdrawRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class WithdrawRequestDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = WithdrawRequest.objects.all()
    serializer_class = WithdrawRequestSerializer
    permission_classes = [permissions.IsAuthenticated]


# Wallet Transaction Views
class WalletTransactionListCreateView(generics.ListCreateAPIView):
    queryset = WalletTransaction.objects.all().order_by('-id')
    serializer_class = WalletTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class WalletTransactionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = WalletTransaction.objects.all()
    serializer_class = WalletTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
