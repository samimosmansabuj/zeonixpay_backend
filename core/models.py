from authentication.models import CustomUser, Merchant, APIKey, MerchantWallet, UserPaymentMethod, BasePaymentGateWay
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models, transaction
import uuid, random, string
from decimal import Decimal


# ============================================Invoice/Cash In Start=======================================
class Invoice(models.Model):
    STATUS = (
        ('active', 'Active'),
        ('deactive', 'Deactive'),
        ('delete', 'Delete')
    )
    PAYMENT_STATUS = (
        ('pending', 'Pending'),
        ('unpaid', 'Unpaid'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )
    merchant = models.ForeignKey(Merchant, on_delete=models.SET_NULL, related_name='invoices', null=True)
    
    invoice_payment_id = models.CharField(max_length=50, editable=False, unique=True)
    callback_url = models.URLField(max_length=250, blank=True, null=True)
    method_payment_id = models.CharField(blank=True, null=True, max_length=100)
    
    customer_order_id = models.CharField(max_length=100, blank=True, null=True)
    customer_name = models.CharField(max_length=100)
    customer_number = models.CharField(max_length=14)
    customer_amount = models.DecimalField(max_digits=6, decimal_places=2)
    customer_email = models.EmailField(max_length=200, blank=True, null=True)
    customer_address = models.CharField(blank=True, null=True, max_length=250)
    customer_description = models.TextField(blank=True, null=True)
    method = models.CharField(max_length=50, blank=True, null=True)
    payment_gateway = models.ForeignKey(BasePaymentGateWay, on_delete=models.SET_NULL, blank=True, null=True, related_name='invoices')
    note = models.TextField(blank=True, null=True)
    
    
    status = models.CharField(max_length=15, choices=STATUS, default='active')
    pay_status = models.CharField(max_length=15, choices=PAYMENT_STATUS, default='pending')
    
    transaction_id = models.CharField(blank=True, null=True, max_length=64)
    invoice_trxn = models.CharField(blank=True, null=True, max_length=64)
    
    extras = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    ALLOWED_WHEN_PAID = frozenset(('customer_name', 'customer_number', 'customer_address'))
    
    def generate_invoice_trxn(self):
        """Generate a unique transaction ID in the format: F37LIY561560"""
        prefix = ''.join(random.choices(string.ascii_uppercase, k=3))  # 3 random letters (e.g., F37)
        suffix = ''.join(random.choices(string.digits, k=6))  # 6 random digits (e.g., 561560)
        return prefix + suffix
    
    def edit_restricted_method(self):
        if not self.pk:
            return

        original = Invoice.objects.only('pay_status').filter(pk=self.pk).first()
        if not original:
            return
        
        if original.status.lower() in ['deactive', 'delete']:
            raise ValidationError(f"This Invoice is {original.status}. Can't Update!")

        if original.pay_status == 'paid':
            changed = set()
            current = Invoice.objects.get(pk=self.pk)
            for f in self._meta.concrete_fields:
                name = f.name
                if name in ('id', 'created_at'):
                    continue
                if getattr(current, name) != getattr(self, name):
                    changed.add(name)

            if changed - self.ALLOWED_WHEN_PAID:
                raise ValidationError("This invoice is already paid and cannot be edited.")
    
    def save(self, *args, **kwargs):
        self.edit_restricted_method()
        
        if not self.invoice_payment_id:
            print(not self.invoice_payment_id)
            self.invoice_payment_id = uuid.uuid4().hex
        
        if not self.invoice_trxn:
            self.invoice_trxn = self.generate_invoice_trxn()
        
        if self.status.lower() == 'active' and self.pay_status.lower() == 'paid' and self.transaction_id:
            WalletTransaction.objects.create(
                wallet = self.merchant.merchant_wallet,
                merchant = self.merchant,
                service = self,
                amount = self.customer_amount,
                method = self.method,
                status='success',
                trx_id=self.transaction_id,
                tran_type='credit'
            )
        return super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Invoice#{self.invoice_payment_id}"

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
        ('pending', 'Pending'), ('success', 'Success'), ('rejected', 'Rejected'), ('delete', 'Delete')
    )
    merchant = models.ForeignKey(Merchant, on_delete=models.SET_NULL, related_name='payment_transfer', null=True)
    confirm_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='confirmed_payments')
    trx_id = models.CharField(max_length=50, null=True, blank=True)
    trx_uuid = models.CharField(max_length=50, editable=False, unique=True)
    receiver_name = models.CharField(max_length=100)
    receiver_number = models.CharField(max_length=14)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD)
    payment_details = models.JSONField()
    status = models.CharField(choices=STATUS, default='pending', max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True, null=True)
    
    transaction_rel = GenericRelation(
        'WalletTransaction',
        content_type_field='content_type',
        object_id_field='object_id',
        related_query_name='withdraw'
    )
    
    ALLOWED_WHEN_PAID = frozenset(('trx_id', 'status', 'confirm_by'))
    
    @property
    def wallet_transaction(self):
        return self.transaction_rel.first()
    
    def edit_restricted_method(self):
        if not self.pk:
            return

        original = PaymentTransfer.objects.only('status').filter(pk=self.pk).first()
        if not original:
            return

        if original.status.lower() in ['success', 'rejected', 'delete']:
            raise ValidationError(f"This Payment Payout is {original.status}. Can't Update!")
        
        changed = set()
        current = PaymentTransfer.objects.get(pk=self.pk)
        for f in self._meta.concrete_fields:
            name = f.name
            if name in ('id', 'created_at'):
                continue
            if getattr(current, name) != getattr(self, name):
                changed.add(name)

        if changed - self.ALLOWED_WHEN_PAID:
            raise ValidationError("Only Transaction & Status can update!")
    
    
    def _as_decimal(self, v):
        return Decimal(str(v or '0'))

    
    def verify_withdraw_amount(self):
        fee_value = self._as_decimal(getattr(self.merchant, 'payout_fees', 0))
        fees_type = (getattr(self.merchant, 'fees_type', '') or '').lower()
        is_percentage = fees_type in ('percentage', 'parcentage')
        if is_percentage:
            fee = (self.amount * fee_value) / Decimal('100')
        elif fees_type == 'flat':
            fee = fee_value
        else:
            fee = (self.amount * Decimal('10')) / Decimal('100')
        
        wallet_balance = self.merchant.merchant_wallet.balance
        return wallet_balance >= self.amount+fee
    
    def save(self, *args, **kwargs):
        if self.confirm_by and self.confirm_by.role.name.lower() != "staff":
            raise ValidationError("Only users with the 'Staff' role can confirm the payment.")
        
        self.edit_restricted_method()
        
        if not self.pk and self.verify_withdraw_amount() is False:
            raise ValidationError("Payout amount less then your Wallet balance.")
        
        if not self.trx_uuid:
            self.trx_uuid = uuid.uuid4().hex
        
        if self.trx_id and self.status == 'pending':
            self.status = 'success'
        
        ret = super().save(*args, **kwargs)
        self._sync_wallet_transaction()
        return ret
    
    def _sync_wallet_transaction(self):
        ct = ContentType.objects.get_for_model(self.__class__)
        
        defaults = {
            'wallet': self.merchant.merchant_wallet,
            'merchant': self.merchant,
            'net_amount': self.amount,
            # 'method': getattr(self.payment_method, 'method_type', None),
            'method': self.payment_method,
            'status': 'success' if str(self.status).lower() == 'success' and self.trx_id else 'pending',
            'trx_id': self.trx_id,
        }
        
        WalletTransaction.objects.update_or_create(
            wallet = self.merchant.merchant_wallet,
            merchant = self.merchant,
            content_type=ct,
            object_id=self.pk,
            tran_type = 'debit',
            defaults=defaults
        )

# ===================================Payment Transfer/Refund/Cash Out End==============================


# ======================================Withdraw Request/Cash Out Start=================================
class WithdrawRequest(models.Model):
    STATUS = (
        ('pending', 'Pending'), ('success', 'Success'), ('rejected', 'Rejected'), ('delete', 'Delete')
    )
    merchant = models.ForeignKey(Merchant, on_delete=models.SET_NULL, related_name='withdrawrequest', blank=True, null=True)
    payment_method = models.ForeignKey(UserPaymentMethod, on_delete=models.SET_NULL, related_name='withdrawal', blank=True, null=True)
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(choices=STATUS, default='pending', max_length=10)
    message = models.TextField(blank=True, null=True)
    trx_id = models.CharField(max_length=50, null=True, blank=True)
    trx_uuid = models.CharField(max_length=50, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    note = models.TextField(blank=True, null=True)
    
    transaction_rel = GenericRelation(
        'WalletTransaction',
        content_type_field='content_type',
        object_id_field='object_id',
        related_query_name='withdraw'
    )
    
    @property
    def wallet_transaction(self):
        return self.transaction_rel.first()
    
    def edit_restricted_method(self):
        if not self.pk:
            return

        original = WithdrawRequest.objects.only('status').filter(pk=self.pk).first()
        if not original:
            return

        if original.status.lower() in ['success', 'rejected', 'delete']:
            raise ValidationError(f"This Withdrawal Request is {original.status}. Can't Update!")
    
    def _as_decimal(self, v):
        return Decimal(str(v or '0'))

    
    def verify_withdraw_amount(self):
        fee_value = self._as_decimal(getattr(self.merchant, 'withdraw_fees', 0))
        fees_type = (getattr(self.merchant, 'fees_type', '') or '').lower()
        is_percentage = fees_type in ('percentage', 'parcentage')
        if is_percentage:
            fee = (self.amount * fee_value) / Decimal('100')
        elif fees_type == 'flat':
            fee = fee_value
        else:
            fee = (self.amount * Decimal('10')) / Decimal('100')
        
        wallet_balance = self.merchant.merchant_wallet.balance
        print(wallet_balance)
        return wallet_balance >= self.amount+fee
    
    def save(self, *args, **kwargs):
        self.edit_restricted_method()
        
        if not self.pk and self.verify_withdraw_amount() is False:
            raise ValidationError("Withdraw amount exceeds your wallet balance.")
        
        if not self.trx_uuid:
            self.trx_uuid = uuid.uuid4().hex
                
        
        if self.trx_id and self.status == 'pending':
            self.status = 'success'
        
        ret = super().save(*args, **kwargs)
        self._sync_wallet_transaction()
        return ret

    def _sync_wallet_transaction(self):
        ct = ContentType.objects.get_for_model(self.__class__)
        
        if str(self.status).lower() == "rejected":
            status__ = "failed"
        elif str(self.status).lower() == "pending" and self.trx_id is None:
            status__ = "pending"
        else:
            status__ = "success"
        
        defaults = {
            'wallet':   self.merchant.merchant_wallet,
            'merchant': self.merchant,
            'net_amount':   self.amount,
            'method':   getattr(self.payment_method, 'method_type', None),
            'status':   status__,
            'trx_id':   self.trx_id,
        }
        
        WalletTransaction.objects.update_or_create(
            wallet = self.merchant.merchant_wallet,
            merchant = self.merchant,
            content_type=ct,
            object_id=self.pk,
            tran_type = 'debit',
            defaults=defaults
        )
    
# ======================================Withdraw Request/Cash Out End=================================




# ========================================Wallet Transaction Start===================================
class WalletTransaction(models.Model):
    wallet = models.ForeignKey(MerchantWallet, on_delete=models.SET_NULL, related_name='wallet_transaction', blank=True, null=True)
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='wallet_transaction', blank=True, null=True)
    ip_address = models.CharField(max_length=32, blank=True, null=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, blank=True, null=True)
    object_id = models.PositiveIntegerField(blank=True, null=True)
    service = GenericForeignKey('content_type', 'object_id')
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    previous_balance = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    current_balance = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    method = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(choices=[('pending', 'Pending'), ('success', 'Success'), ('failed', 'Failed')], max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    trx_id = models.CharField(max_length=50, null=True, blank=True)
    trx_uuid = models.CharField(max_length=50, editable=False, unique=True)
    tran_type = models.CharField(max_length=20, choices=(('debit', 'Debit'), ('credit', 'Credit')))
        
    def _as_decimal(self, v):
        return Decimal(str(v or '0'))

    def _get_original(self):
        if not self.pk:
            return None
        try:
            return type(self).objects.get(pk=self.pk)
        except type(self).DoesNotExist:
            return None
    
    def edit_restricted_method(self):
        if not self.pk:
            return

        original = WalletTransaction.objects.only('status').filter(pk=self.pk).first()
        if not original:
            return

        if original.status.lower() in ['success', 'failed']:
            raise ValidationError(f"This Wallet Transaction is {original.status}. Can't Update!")
    
    def save_user_ip_address(self, request=None):
        if request and not self.ip_address:
            ip = request.META.get('HTTP_X_FORWARDED_FOR')
            if ip:
                ip = ip.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR', '')
            self.ip_address = ip
    
    def _which_fee_bucket(self):
        tran = (self.tran_type or '').lower()
        model_name = None
        if self.content_type:
            model_name = (self.content_type.model or '').lower()
        elif self.service is not None:
            model_name = self.service.__class__.__name__.lower()

        if model_name:
            model_name = model_name.replace('_', '')

        if tran == 'credit' and model_name == 'invoice':
            return 'deposit'
        if tran == 'debit' and model_name in ('paymenttransfer',):
            return 'payout'
        if tran == 'debit' and model_name in ('withdrawrequest',):
            return 'withdraw'
        return None

    
    def credit_fees_disbursement(self):
        fee_value = self._as_decimal(getattr(self.merchant, 'deposit_fees', 0))
        fees_type = (getattr(self.merchant, 'fees_type', '') or '').lower()
        is_percentage = fees_type in ('percentage', 'parcentage')
        if is_percentage:
            self.fee = (self.amount * fee_value) / Decimal('100')
        elif fees_type == 'flat':
            self.fee = fee_value
        else:
            self.fee = (self.amount * Decimal('10')) / Decimal('100')
        self.net_amount = self.amount - self.fee
    
    def fees_disbursement(self):
        if not self.merchant:
            self.fee = Decimal('0')
            self.net_amount = self.amount
            return

        bucket = self._which_fee_bucket()

        if bucket == 'deposit':
            self.credit_fees_disbursement()
        else:
            if bucket == 'payout':
                fee_value = self._as_decimal(getattr(self.merchant, 'payout_fees', 0))
            elif bucket == 'withdraw':
                fee_value = self._as_decimal(getattr(self.merchant, 'withdraw_fees', 0))
            else:
                fee_value = 5
            
            fees_type = (getattr(self.merchant, 'fees_type', '') or '').lower()
            is_percentage = fees_type in ('percentage', 'parcentage')
            
            if is_percentage:
                self.fee = (self.net_amount * fee_value) / Decimal('100')
            elif fees_type == 'flat':
                self.fee = fee_value
            else:
                self.fee = (self.amount * Decimal('10')) / Decimal('100')
            
            self.amount = self.net_amount + self.fee
    
    @transaction.atomic
    def save(self, *args, **kwargs):
        creating = self._state.adding or not self.pk
        
        if not self.trx_uuid:
            self.trx_uuid = uuid.uuid4().hex
        
        self.edit_restricted_method()
        self.save_user_ip_address(kwargs.pop('request', None))
        
        original = self._get_original()
        prev_status = (original.status.lower() if original and original.status else None)
        prev_amount = (self._as_decimal(original.amount) if original else None)
               
        new_status = (self.status or '').lower()
        new_tran   = (self.tran_type or '').lower()
        
        wallet = self.wallet
        if not wallet:
            raise ValidationError("Wallet is required for a transaction.")
        
        # old_balance = wallet.balance
        if creating or not self.previous_balance:
            old_balance_for_record = wallet.balance
        else:
            old_balance_for_record = self.previous_balance  # freeze from first write
        
        # ---------- FEES ----------
        self.fees_disbursement()
        
        
        # ---------- STATE TRANSITIONS (debit case) ----------
        if new_tran == 'debit':
            if not original:
                if new_status == 'pending':
                    if wallet.balance < self.amount:
                        raise ValidationError("Insufficient available balance to place a pending hold.")
                    wallet.balance -= self.amount
                    wallet.withdraw_processing += self.amount

                elif new_status == 'success':
                    if wallet.balance < self.amount:
                        raise ValidationError("Insufficient balance for successful debit.")
                    wallet.balance -= self.amount
                    wallet.total_withdraw += self.amount

                elif new_status == 'failed':
                    pass
            else:
                if prev_status == 'pending':
                    if new_status == 'pending':
                        diff = (self.amount - prev_amount)
                        if diff > 0 and wallet.available_balance < diff:
                            raise ValidationError("Insufficient available balance to increase pending hold.")
                        wallet.balance -= diff
                        wallet.withdraw_processing += diff

                    elif new_status == 'success':
                        if self.amount != prev_amount:
                            raise ValidationError("Amount cannot change when finalizing to success. Cancel & recreate.")
                        wallet.withdraw_processing -= prev_amount
                        wallet.total_withdraw += prev_amount

                    elif new_status == 'failed':
                        wallet.withdraw_processing -= prev_amount
                        wallet.balance += prev_amount
                        

                elif prev_status in ('success', 'failed'):
                    raise ValidationError(f"Cannot update a {prev_status} transaction.")

                elif prev_status is None:
                    pass
            
            wallet.save()
        
        # ---------- CREDIT case ----------
        elif new_tran == 'credit':
            if not original:
                if new_status == 'success':
                    wallet.balance += self.net_amount
                    wallet.save()
            else:
                if prev_status == 'pending' and new_status == 'success':
                    wallet.balance += self.net_amount
                    wallet.save()
                elif prev_status in ('success', 'failed'):
                    raise ValidationError(f"Cannot update a {prev_status} transaction.")

        if creating or not self.previous_balance:
            self.previous_balance = old_balance_for_record  # set once
        self.current_balance = wallet.balance
        
        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            if creating:
                kwargs.pop('update_fields', None)
            else:
                update_fields = set(update_fields)
                update_fields.update({'fee', 'net_amount', 'amount', 'current_balance'})
                if not self.previous_balance:
                    update_fields.add('previous_balance')
                kwargs['update_fields'] = update_fields

        return super().save(*args, **kwargs)
        
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['content_type', 'object_id'], name='uniq_wallet_txn_per_service')
        ]
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]
# ========================================Wallet Transaction End===================================

