from django.db import models
from authentication.models import CustomUser, UserBrand, UserWallet
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
import uuid


# ============================================Invoice/Cash In Start=======================================
class Invoice(models.Model):
    STATUS = (
        ('active', 'Active'),
        ('deactive', 'Deactive')
    )
    PAYMENT_STATUS = (
        ('pending', 'Pending'),
        ('unpaid', 'Unpaid'),
        ('paid', 'Paid')
    )
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, related_name='invoice', null=True)
    payment_uid = models.UUIDField(default=uuid.uuid4().hex, editable=False)
    brand_id = models.ForeignKey(UserBrand, on_delete=models.SET_NULL, related_name='invoice', null=True)
    customer_name = models.CharField(max_length=100)
    customer_number = models.CharField(max_length=14)
    customer_amount = models.DecimalField(max_digits=6, decimal_places=2)
    customer_email = models.EmailField(max_length=200)
    customer_address = models.CharField(blank=True, null=True)
    customer_description = models.TextField(blank=True, null=True)
    method = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=15, choices=STATUS, default='active')
    pay_status = models.CharField(max_length=15, choices=PAYMENT_STATUS, default='pending')
    transaction_id = models.CharField(blank=True, null=True)
    extras = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if self.status == 'Active' and self.pay_status == 'Paid' and self.transaction_id:
            wallet_trxn = WalletTransaction.objects.create(
                wallet = self.user.user_wallet,
                brand = self.brand_id,
                service = self,
                amount = self.customer_amount,
                method = self.method,
                status='success',
                trx_id=self.transaction_id,
                tran_type='credit'
            )
        return super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Invoice#{self.payment_uid}"

# ============================================Invoice/Cash In End=======================================



# ===================================Payment Transfer/Refund/Cash Out Start==============================
class PaymentTransfer(models.Model):
    PAYMENT_METHOD = (
        ('bkash', 'Bkash'),
        ('nagad', 'Nagad'),
        ('rocket', 'Rocket'),
        ('bank', 'Bank'),
    )
    STATUS = (
        ('pending', 'Pending'), ('success', 'Success'), ('rejected', 'Rejected')
    )
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, related_name='payment_transfer', null=True)
    brand = models.ForeignKey(UserBrand, on_delete=models.SET_NULL, related_name='payment_transfer', null=True)
    transfer_id = models.UUIDField(default=uuid.uuid4().hex, editable=False)
    receiver_name = models.CharField(max_length=100)
    receiver_number = models.CharField(max_length=14)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    charge = models.DecimalField(max_digits=12, decimal_places=2)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD)
    payment_details = models.JSONField()
    status = models.CharField(choices=STATUS, default='pending', max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if self.status == 'Success' and self.transfer_id:
            wallet_trxn = WalletTransaction.objects.create(
                wallet = self.user.user_wallet,
                service = self,
                amount = self.net_amount,
                method = self.payment_method,
                status='success',
                trx_id=self.transaction_id,
                tran_type='debit'
            )
        return super().save(*args, **kwargs)

# ===================================Payment Transfer/Refund/Cash Out End==============================


# ======================================Withdraw Request/Cash Out Start=================================
class WithdrawRequest(models.Model):
    STATUS = (
        ('pending', 'Pending'), ('success', 'Success'), ('rejected', 'Rejected')
    )
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, related_name='withdrawrequest', blank=True, null=True)
    wallet = models.ForeignKey(UserWallet, on_delete=models.SET_NULL, related_name='withdrawrequest', blank=True, null=True)
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    charge = models.DecimalField(max_digits=12, decimal_places=2)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(choices=STATUS, default='pending', max_length=10)
    message = models.TextField(blank=True, null=True)
    trx_id = models.CharField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if self.status == 'Success' and self.trx_id:
            wallet_trxn = WalletTransaction.objects.create(
                wallet = self.wallet,
                service = self,
                amount = self.net_amount,
                method = self.method,
                status='success',
                trx_id=self.transaction_id,
                tran_type='debit'
            )
        
        return super().save(*args, **kwargs)

# ======================================Withdraw Request/Cash Out End=================================




# ========================================Wallet Transaction Start===================================
class WalletTransaction(models.Model):
    wallet = models.ForeignKey(UserWallet, on_delete=models.SET_NULL, related_name='wallet_transaction', blank=True, null=True)
    brand = models.ForeignKey(UserBrand, on_delete=models.CASCADE, related_name='wallet_transaction', blank=True, null=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, blank=True, null=True)
    object_id = models.PositiveIntegerField(blank=True, null=True)
    service = GenericForeignKey('content_type', 'object_id')
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=10, blank=True, null=True)
    status = models.CharField(choices=[('pending', 'Pending'), ('success', 'Success'), ('failed', 'Failed')], max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    trx_id = models.CharField(max_length=100, null=True, blank=True)
    tran_type = models.CharField(max_length=20, choices=(('debit', 'Debit'), ('credit', 'Credit')))
    
    def save(self, *args, **kwargs):
        wallet = self.wallet
        if self.status == 'Success':
            if self.tran_type == 'Debit':
                wallet.balance -= self.amount
            elif self.tran_type == 'Credit':
                wallet.balance += self.amount
            wallet.save()
        
        return super().save(*args, **kwargs)

# ========================================Wallet Transaction End===================================

