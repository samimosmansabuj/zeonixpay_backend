from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid


class UserRole(models.Model):
    name = models.CharField(max_length=50)
    permission = models.CharField(max_length=200, blank=True, null=True)
    
    def __str__(self):
        return self.name

# ========================================Custom User Start===================================
class CustomUser(AbstractUser):
    STATUS = (('Active', 'Active'), ('Disable', 'Disable'), ('Pending', 'Pending'))
    first_name = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=14)
    more_information = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS, default='Pending')
    role = models.ForeignKey(UserRole, on_delete=models.SET_NULL, blank=True, null=True)
    pid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    def __str__(self):
        return self.username

# ========================================User Ids Start===================================
class UserId(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='user_ids')
    referal_key = models.UUIDField(default=uuid.uuid4, editable=False)
    activation_key = models.CharField(max_length=500, blank=True, null=True)
    reset_key = models.CharField(max_length=500, blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.username} User UserIds Model"


# ========================================User Wallet Start===================================
class UserWallet(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='user_wallet')
    wallet_id = models.UUIDField(default=uuid.uuid4().hex, unique=True, editable=False)
    balance = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    withdraw_processing = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    total_withdraw = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    
    def __str__(self):
        return f"{self.user.username} User Wallet Model"


# ================================================================================
# Signal for UserIds & UserWallet model create automatically when create a user!
# ================================================================================
@receiver(post_save, sender=CustomUser)
def create_user_ids_and_wallet(sender, instance, created, **kwargs):
    if created:
        if instance.role and instance.role.name.lower() == 'merchant':
            if not hasattr(instance, 'user_ids'):
                UserId.objects.create(user=instance)
            if not hasattr(instance, 'user_wallet'):
                UserWallet.objects.create(user=instance)


# ========================================UserBrand Start===================================
class UserBrand(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='user_model')
    brand_key = models.UUIDField(default=uuid.uuid4().hex, editable=False)
    
    brand_name = models.CharField(max_length=50)
    mobile_number = models.CharField(max_length=14)
    whatsapp_number = models.CharField(max_length=14, blank=True, null=True)
    email = models.EmailField(max_length=200, blank=True, null=True)
    domain_name = models.URLField(max_length=200)
    brand_logo = models.ImageField(upload_to='brand-logo', blank=True, null=True)
    brand_details = models.JSONField()
    status = models.CharField(max_length=20, choices=(('Active', 'Active'), ('Inactive', 'Inactive')), default='Active')
    fees_type = models.CharField(max_length=10, choices=(('Flat', 'Flat'), ('Parcentage', 'Parcentage')), default='Parcentage')
    fees = models.DecimalField(max_digits=4, decimal_places=2, default=5)
    
    def __str__(self):
        return self.brand_name


# ========================================UserPaymentMethod Start===================================
class UserPaymentMethod(models.Model):
    METHOD_TYPE = (
        ('bkash', 'Bkash'),
        ('nagad', 'Nagad'),
        ('rocket', 'Rocket'),
        ('bank', 'Bank'),
    )
    STATUS = (
        ('active', 'Active'),
        ('deactive', 'Deactive'),
    )
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='payment_methods')
    brand = models.ForeignKey(UserBrand, models.SET_NULL, related_name='payment_methods', blank=True, null=True)
    method_type = models.CharField(max_length=20, choices=METHOD_TYPE)
    params = models.JSONField()
    status = models.CharField(max_length=10, choices=STATUS)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.method_type} Payment Method for {self.user.first_name} {self.user.last_name}"





