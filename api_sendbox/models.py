from django.db import models
from authentication.models import Merchant
import random, string, uuid

class SendBoxInvoice(models.Model):
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
    merchant = models.ForeignKey(Merchant, on_delete=models.SET_NULL, related_name='sendbox_invoices', null=True)
    
    invoice_payment_id = models.CharField(max_length=50, editable=False, unique=True)
    callback_url = models.URLField(max_length=255, blank=True, null=True)
    method_payment_id = models.CharField(blank=True, null=True, max_length=100)
    
    customer_order_id = models.CharField(max_length=100, blank=True, null=True)
    customer_name = models.CharField(max_length=100)
    customer_number = models.CharField(max_length=14)
    customer_amount = models.DecimalField(max_digits=6, decimal_places=2)
    customer_email = models.EmailField(max_length=200, blank=True, null=True)
    customer_address = models.CharField(blank=True, null=True, max_length=250)
    customer_description = models.TextField(blank=True, null=True)
    method = models.CharField(max_length=50, blank=True, null=True)
    
    status = models.CharField(max_length=15, choices=STATUS, default='active')
    pay_status = models.CharField(max_length=15, choices=PAYMENT_STATUS, default='pending')
    
    transaction_id = models.CharField(blank=True, null=True, max_length=64)
    invoice_trxn = models.CharField(blank=True, null=True, max_length=64)
    
    extras = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    
    def generate_invoice_trxn(self):
        """Generate a unique transaction ID in the format: F37LIY561560"""
        prefix = ''.join(random.choices(string.ascii_uppercase, k=3))  # 3 random letters (e.g., F37)
        suffix = ''.join(random.choices(string.digits, k=6))  # 6 random digits (e.g., 561560)
        return prefix + suffix
    
    def save(self, *args, **kwargs):
        if not self.invoice_payment_id:
            self.invoice_payment_id = uuid.uuid4().hex
        
        if not self.invoice_trxn:
            self.invoice_trxn = self.generate_invoice_trxn()
        
        return super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Invoice#{self.invoice_payment_id}"




class SendBoxPaymentTransfer(models.Model):
    PAYMENT_METHOD = (
        ('bkash', 'Bkash'),
        ('nagad', 'Nagad'),
        ('rocket', 'Rocket'),
        ('bank', 'Bank'),
    )
    STATUS = (
        ('pending', 'Pending'), ('success', 'Success'), ('rejected', 'Rejected'), ('delete', 'Delete')
    )
    merchant = models.ForeignKey(Merchant, on_delete=models.SET_NULL, related_name='sendbox_payment_transfer', null=True)
    trx_id = models.CharField(max_length=50, null=True, blank=True)
    trx_uuid = models.CharField(max_length=50, editable=False, unique=True)
    receiver_name = models.CharField(max_length=100)
    receiver_number = models.CharField(max_length=14)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD)
    payment_details = models.JSONField()
    status = models.CharField(choices=STATUS, default='pending', max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    
    
    def save(self, *args, **kwargs):
        if not self.trx_uuid:
            self.trx_uuid = uuid.uuid4().hex
        return super().save(*args, **kwargs)



