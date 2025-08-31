from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import datetime
from django.db import models

import uuid, secrets, random, string, re



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
    pid = models.CharField(max_length=50, editable=False, unique=True)
    
    def save(self, *args, **kwargs):
        if not self.pid:
            self.pid = uuid.uuid4().hex
        return super().save(*args, **kwargs)
    
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



# ================================================================================
# Signal for UserIds & UserWallet model create automatically when create a user!
# ================================================================================
@receiver(post_save, sender=CustomUser)
def create_user_ids(sender, instance, created, **kwargs):
    if created:
        if instance.role and instance.role.name.lower() == 'merchant':
            if not hasattr(instance, 'user_ids'):
                UserId.objects.create(user=instance)


# ======================================================================================================
# ========================================User Merchant Model Start===================================
class Merchant(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='merchant')
    merchant_id = models.CharField(max_length=100, editable=False, unique=True)
    
    brand_name = models.CharField(max_length=50)
    whatsapp_number = models.CharField(max_length=14, blank=True, null=True)
    domain_name = models.URLField(max_length=200, blank=True, null=True)
    brand_logo = models.ImageField(upload_to='brand-logo', blank=True, null=True)
    status = models.CharField(max_length=20, choices=(('Active', 'Active'), ('Inactive', 'Inactive')), default='Active')
    fees_type = models.CharField(max_length=10, choices=(('Flat', 'Flat'), ('Parcentage', 'Parcentage')), default='Parcentage')
    deposit_fees = models.DecimalField(max_digits=4, decimal_places=2, default=5)
    payout_fees = models.DecimalField(max_digits=4, decimal_places=2, default=5)
    withdraw_fees = models.DecimalField(max_digits=4, decimal_places=2, default=5)
    is_active = models.BooleanField(default=True)
    
    def genereate_merchant_id(self):
        # unique = False
        while True:
            merchant_id = ''.join(random.choices(string.digits, k=6))
            if not Merchant.objects.filter(merchant_id=merchant_id).exists():
                # unique = True
                return merchant_id
    
    def save(self, *args, **kwargs):
        if not self.merchant_id:
            self.merchant_id = self.genereate_merchant_id()
        return super().save(*args, **kwargs)
    
    def __str__(self):
        return self.brand_name

class APIKey(models.Model):
    merchant = models.OneToOneField(Merchant, on_delete=models.CASCADE, related_name='api_keys')
    api_key = models.CharField(max_length=128, unique=True, blank=True, null=True)
    secret_key = models.CharField(max_length=128, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def set_secret(self, raw: str):
        self.secret_key = make_password(raw)

    def check_secret(self, raw: str) -> bool:
        return check_password(raw, self.secret_key)

    def save(self, *args, **kwargs):
        if not self.api_key:
            self.api_key = secrets.token_urlsafe(32)

        if not self.secret_key:
            raw_secret = secrets.token_urlsafe(32)
            self.set_secret(raw_secret)

        super().save(*args, **kwargs)

    def __str__(self):
        return f'API credential for {self.merchant.brand_name}'

class MerchantWallet(models.Model):
    merchant = models.OneToOneField(Merchant, on_delete=models.CASCADE, related_name='merchant_wallet')
    wallet_id = models.CharField(max_length=250, editable=False, unique=True)
    balance = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    withdraw_processing = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    total_withdraw = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    
    @property
    def available_balance(self):
        return (self.balance or 0) - (self.withdraw_processing or 0)
    
    def save(self, *args, **kwargs):
        if not self.wallet_id:
            self.wallet_id = uuid.uuid4().hex
        return super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.merchant.brand_name} Merchant Wallet Model"

@receiver(post_save, sender=Merchant)
def create_api_key_and_wallet_for_merchant(sender, instance, created, **kwargs):
    if created:
        if not hasattr(instance, 'api_keys'):
            APIKey.objects.create(merchant=instance)
        if not hasattr(instance, 'merchant_wallet'):
            MerchantWallet.objects.create(merchant=instance)


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
    merchant = models.ForeignKey(Merchant, models.SET_NULL, related_name='payment_methods', blank=True, null=True)
    method_type = models.CharField(max_length=20, choices=METHOD_TYPE)
    params = models.JSONField()
    status = models.CharField(max_length=10, choices=STATUS)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if self.is_primary and self.merchant:
            UserPaymentMethod.objects.filter(
                merchant=self.merchant
            ).exclude(pk=self.pk).update(is_primary=False)
        return super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.method_type} Payment Method for {self.merchant.brand_name}"

# ========================================User Merchant Model End===================================
# ======================================================================================================



# ======================================================================================================
# ===============Site Payment Gate, And Payment Message Store and Device Management Start==========
class BasePaymentGateWay(models.Model):
    METHOD = (
        ('bkash', 'bkash'),
        ('bkash-agent', 'bkash-agent'),
        ('bkash-personal', 'bkash-personal'),
        
        ('nagad', 'nagad'),
        ('nagad-agent', 'nagad-agent'),
        ('nagad-personal', 'nagad-personal'),
        
        ('rocket', 'rocket'),
        ('rocket-agent', 'rocket-agent'),
        ('rocket-personal', 'rocket-personal'),
        
        ('bkash-sendbox', 'bkash-sendbox'),
        ('nagad-sendbox', 'nagad-sendbox'),
        ('rocke-sendboxt', 'rocket-sendbox'),
        
        ('bank', 'bank'),
        ('crypto', 'crypto')
    )
    
    method = models.CharField(max_length=20, choices=METHOD)
    method_uuid = models.CharField(max_length=255, unique=True, editable=False)
    
    base_url = models.URLField(max_length=255, blank=True, null=True)
    details_json = models.JSONField(blank=True, null=True)
    callback_base_url = models.URLField(max_length=255)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    is_active = models.BooleanField(default=True)
    
    def save(self, *args, **kwargs):
        if not self.method_uuid:
            self.method_uuid = uuid.uuid4().hex
        return super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.method} - {self.method_uuid} | {self.details_json}"


class SmsDeviceKey(models.Model):
    device_name = models.CharField(max_length=50)
    device_key = models.CharField(max_length=100)
    device_pin = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    create_at = models.DateTimeField(auto_now_add=True)
    updated_ta = models.DateTimeField(auto_now=True)
    
    def set_pin(self, raw_pin: str):
        self.device_pin = make_password(raw_pin)

    def check_pin(self, raw_pin: str) -> bool:
        return check_password(raw_pin, self.device_pin)
    
    def save(self, *args, **kwargs):
        if self.device_pin and not self.device_pin.startswith("pbkdf2_"):
            self.device_pin = make_password(self.device_pin)
        
        if not self.device_key:
            self.device_key = uuid.uuid4().hex
        return super().save(*args, **kwargs)
    
    def __str__(self):
        return self.device_key


class StorePaymentMessage(models.Model):
    device = models.ForeignKey(SmsDeviceKey, on_delete=models.SET_NULL, related_name='payment_messages', null=True, blank=True)
    message_from = models.CharField(max_length=20)
    message = models.TextField(blank=True, null=True)
    payment_number = models.CharField(max_length=20, blank=True, null=True)
    trx_id = models.CharField(max_length=50, blank=True, null=True)
    message_amount = models.DecimalField(decimal_places=2, max_digits=9, blank=True, null=True)
    message_date = models.DateTimeField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    create_at = models.DateTimeField(auto_now_add=True)
    
    def extract_bkash_message(self):
        #Extract Amount From Message============
        amount_pattern = r"Tk (\d{1,3}(?:,\d{3})*(?:\.\d{2})?)"
        amount_match = re.search(amount_pattern, self.message)
        if amount_match:
            self.message_amount = amount_match.group(1).replace(',', '')
        
        #Extract TrxID From Message============
        trxid_pattern = r"TrxID (\S+)"
        trxid_match = re.search(trxid_pattern, self.message)
        if trxid_match:
            self.trx_id = trxid_match.group(1)
        
        #Extract Payment number From Message============
        phone_pattern = r"from (\d{11})"
        phone_match = re.search(phone_pattern, self.message)
        if phone_match:
            self.payment_number = phone_match.group(1)
        
        
        # Print the raw message to check for format discrepancies
        self.message = self.message.replace('\xa0', ' ')
        date_pattern = r"\s*at\s*(\d{2}/\d{2}/\d{4} \d{2}:\d{2})"
        date_match = re.search(date_pattern, self.message)
        
        if date_match:
            try:
                self.message_date = datetime.strptime(date_match.group(1), "%d/%m/%Y %H:%M")
                print("Extracted Date:", self.message_date)
            except ValueError:
                print("Date format error.")
        else:
            print("Date not found in message.")

        return self.message
    
    def extract_nagad_message(self):
        #Extract Amount From Message============
        amount_pattern = r"Amount: Tk ([\d,]+(?:\.\d{1,2})?)"
        amount_match = re.search(amount_pattern, self.message)
        if amount_match:
            self.message_amount = amount_match.group(1).replace(',', '')
        
        #Extract TrxID From Message============
        trxid_pattern = r"TxnID: (\S+)"
        trxid_match = re.search(trxid_pattern, self.message)
        if trxid_match:
            self.trx_id = trxid_match.group(1)
        
        #Extract Payment number From Message============
        phone_pattern = r"(?:Customer|Receiver):\s*(\d{11})"
        phone_match = re.search(phone_pattern, self.message)
        if phone_match:
            self.payment_number = phone_match.group(1)
        
        #Extract Date From Message============
        text = self.message.replace('\xa0', ' ')
        date_pattern = r"(\d{2}/\d{2}/\d{4} \d{2}:\d{2})"
        date_match = re.search(date_pattern, text)
        if date_match:
            try:
                self.message_date = datetime.strptime(date_match.group(1), "%d/%m/%Y %H:%M")
            except ValueError:
                print("Date format error.")
        
        return self.message
    
    def extract_rocket_message(self):
        #Extract Amount From Message============
        amount_pattern = r"Tk([\d,]+(?:\.\d{1,2})?)"
        amount_match = re.search(amount_pattern, self.message)
        if amount_match:
            self.message_amount = amount_match.group(1).replace(',', '')

        #Extract TrxID From Message============
        trxid_pattern = r"TxnId:(\S+)"
        trxid_match = re.search(trxid_pattern, self.message)
        if trxid_match:
            self.trx_id = trxid_match.group(1)
        
        #Extract Payment number From Message============
        phone_pattern = r"from (\S+)"
        phone_match = re.search(phone_pattern, self.message)
        if phone_match:
            self.payment_number = phone_match.group(1)
        
        #Extract Date From Message============
        date_pattern = r"Date\s*:\s*(\d{1,2})-([A-Za-z]{3})-(\d{2,4})\s+(\d{1,2}:\d{2}(?::\d{2})?)\s*([ap]m)\.?"
        date_match = re.search(date_pattern, self.message)
        if date_match:
            day, mon, year, timestr, ampm = date_match.groups()
            mon = mon.title(); ampm = ampm.upper()
            datestr = f"{day}-{mon}-{year} {timestr} {ampm}"
            has_seconds = timestr.count(':') == 2
            year_fmt = "%Y" if len(year) == 4 else "%y"
            time_fmt = "%I:%M:%S" if has_seconds else "%I:%M"
            fmt = f"%d-%b-{year_fmt} {time_fmt} %p"
            try:
                self.message_date = datetime.strptime(datestr, fmt)
            except ValueError:
                print("Date format error.")
        
        return self.message

    def extract_message_body(self):
        if not self.message and not self.message_from:
            return None
        if self.message_from.lower() == "bkash":
            return self.extract_bkash_message()
        elif self.message_from.lower() == "nagad":
            return self.extract_nagad_message()
        elif self.message_from.lower() == "16216":
            return self.extract_rocket_message()

        

    def save(self, *args, **kwargs):
        self.extract_message_body()

        return super().save(*args, **kwargs)

# ===============Site Payment Gate, And Payment Message Store and Device Management End==========
# ======================================================================================================






class URLConfiguration(models.Model):
    api_base_url = models.URLField(blank=True, null=True, max_length=255)
    payment_site_base_url = models.URLField(blank=True, null=True, max_length=255)
    frontend_base_url = models.URLField(blank=True, null=True, max_length=255)

