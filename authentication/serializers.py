from .models import CustomUser, UserRole, UserId, UserPaymentMethod, Merchant, MerchantWallet, BasePaymentGateWay, SmsDeviceKey, StorePaymentMessage, APIKey
from django.contrib.auth.hashers import make_password
from .utils import CustomLoginSerializer
from rest_framework import serializers
from django.db import transaction
from rest_framework.exceptions import ValidationError


# ========================Authentication Token Serializer Start================================
class MerchantLoginSerializer(CustomLoginSerializer):
    def verify_user_role(self, user):
        if user.status in ['Pending', 'Disable']:
            return {'status': False, 'message': f'Your account is {user.status}!'}
        
        if user.role and user.role.name == 'Merchant':
            return {'status': True, 'message': 'Merchant user'}
        return {'status': False, 'message': 'This is merchant account credentials!'}

class AdminLoginSerializer(CustomLoginSerializer):
    def verify_user_role(self, user):
        if user.status in ['Pending', 'Disable']:
            return {'status': False, 'message': f'Your account is {user.status}!'}
        
        if user.role and user.role.name in ['Admin']:
            return {'status': True, 'message': 'Admin user'}
        return {'status': False, 'message': 'This is admin account credentials!'}

class StaffLoginSerializer(CustomLoginSerializer):
    def verify_user_role(self, user):
        if user.status in ['Pending', 'Disable']:
            return {'status': False, 'message': f'Your account is {user.status}!'}
        
        if user.role and user.role.name in ['Staff']:
            return {'status': True, 'message': 'Staff user'}
        return {'status': False, 'message': 'This is staff account credentials!'}

# ========================Authentication Token Serializer End================================


# ========================Registration/Account Create Serializer Start=============================
class RegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 'password', 'role']
    
    def validate_username(self, value):
        if CustomUser.objects.filter(username=value).exists():
            raise serializers.ValidationError('username already exists.', code='unique')
        return value

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError('email already exists.', code='unique')
        return value
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data['password'] = make_password(password)
        user = CustomUser.objects.create(**validated_data)
        return user

class MerchantRegistrationSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(
        required=True,
        error_messages={"required": "Brand Name is required."}
    )
    whatsapp_number = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    domain_name = serializers.URLField(
        required=False,
    )
    brand_logo = serializers.FileField(required=False, allow_null=True)

    username = serializers.CharField(
        required=True,
        error_messages={"required": "Username is required."}
    )
    email = serializers.EmailField(
        required=True,
        error_messages={"required": "Email is required."}
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        error_messages={"required": "Password is required."}
    )
    first_name = serializers.CharField(
        required=True,
        error_messages={"required": "First Name is required."}
    )
    last_name = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    phone_number = serializers.CharField(
        required=True,
        error_messages={"required": "Phone Number is required."}
    )

    class Meta:
        model = CustomUser
        fields = (
            # user
            "username", "email", "password", "first_name", "last_name", "phone_number",
            # merchant
            "brand_name", "whatsapp_number", "domain_name", "brand_logo",
        )

    def validate_username(self, value):
        if CustomUser.objects.filter(username=value).exists():
            raise serializers.ValidationError("username already exists.", code="unique")
        return value

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("email already exists.", code="unique")
        return value

    def create(self, validated_data):
        merchant_fields = {
            "brand_name": validated_data.pop("brand_name"),
            "whatsapp_number": validated_data.pop("whatsapp_number", None),
            "domain_name": validated_data.pop("domain_name", None),
            "brand_logo": validated_data.pop("brand_logo", None),
            "brand_logo": validated_data.pop("brand_logo", None),
        }

        password = validated_data.pop("password")
        validated_data["password"] = make_password(password)

        with transaction.atomic():
            user = CustomUser.objects.create(**validated_data)

            Merchant.objects.create(
                user=user,
                **merchant_fields
            )
        return user

# ========================Registration/Account Create Serializer End=============================

        


# ======================================================================================================
# ========================================User Merchant Serializers Start=======================
class MerchantWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = MerchantWallet
        fields = ['balance', 'withdraw_processing', 'total_withdraw']

class UserIdSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserId
        fields = '__all__'

class UserPaymentMethodSerializer(serializers.ModelSerializer):
    # user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False)
    class Meta:
        model = UserPaymentMethod
        fields = '__all__'

class APIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = '__all__'

# ========================================User Merchant Serializers End==========================
# ======================================================================================================



# ======================================================================================================
# ========================================User Merchant Model Start================================
class BasePaymentGateWaySerializer(serializers.ModelSerializer):
    class Meta:
        model = BasePaymentGateWay
        fields = "__all__"
        read_only_fields = ['method_uuid', 'created_at', 'updated_at']


class StorePaymentMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorePaymentMessage
        fields = "__all__"
        read_only_fields = ["id", "create_at"]

class SmsDeviceKeySerializer(serializers.ModelSerializer):
    # payment_messages = StorePaymentMessageSerializer(many=True, read_only=True)
    class Meta:
        model = SmsDeviceKey
        fields = "__all__"
        read_only_fields = ["create_at", "updated_ta", "device_key"]

# ========================================User Merchant Model End================================
# ======================================================================================================




class MerchantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Merchant
        fields = ['brand_name', 'whatsapp_number', 'domain_name', 'brand_logo', 'status', 'fees_type', 'deposit_fees', 'payout_fees', 'withdraw_fees', 'is_active']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'phone_number', 'more_information', 'status', 'role']



# ========================Important Base Serializer Start=============================
class UserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRole
        fields = '__all__'

class CustomUserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'phone_number', 'status', 'role', 'pid']
    
    def get_role(self, obj):
        return obj.role.name if obj.role else None

class MerchantUserListSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    merchant = MerchantSerializer(required=False, allow_null=True)
    
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'phone_number', 'status', 'role', 'pid', 'merchant']
        depth = 1
    
    def get_role(self, obj):
        return obj.role.name if obj.role else None
    
    def update(self, instance, validated_data):
        merchant_data = validated_data.pop("merchant", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        request = self.context.get("request")
        
        if merchant_data is not None:
            if not hasattr(instance, "merchant") or instance.merchant is None:
                raise ValidationError({"merchant": "Merchant profile does not exist for this user."})
            
            uploaded_logo = None
            if request and hasattr(request, "FILES"):
                uploaded_logo = request.FILES.get("merchant.brand_logo") or request.FILES.get("brand_logo")
            if uploaded_logo is not None:
                merchant_data["brand_logo"] = uploaded_logo

            m_serializer = MerchantSerializer(
                instance.merchant,
                data=merchant_data,
                partial=True
            )
            m_serializer.is_valid(raise_exception=True)
            m_serializer.save()
        
        return instance
        
        # return super().update(instance, validated_data)


