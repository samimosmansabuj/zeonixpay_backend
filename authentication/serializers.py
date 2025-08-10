from rest_framework import serializers
from .models import CustomUser, UserRole, UserId, UserWallet, UserBrand, UserPaymentMethod
from .utils import CustomLoginSerializer
from django.contrib.auth.hashers import make_password


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
        
        if user.role and user.role.name in ['Admin', 'Staff']:
            return {'status': True, 'message': 'Admin/Staff user'}
        return {'status': False, 'message': 'This is admin or staff account credentials!'}

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

# ========================Registration/Account Create Serializer End=============================





class UserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRole
        fields = '__all__'


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'phone_number', 'status', 'role', 'pid']








class UserWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserWallet
        fields = '__all__'


class UserIdSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserId
        fields = '__all__'


class UserBrandSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False)
    class Meta:
        model = UserBrand
        fields = '__all__'


class UserPaymentMethodSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False)
    class Meta:
        model = UserPaymentMethod
        fields = '__all__'
    
    # def validate_brand(self, attrs):
    #     brand = attrs.user
    #     return attrs
    
    # def validate(self, attrs):
    #     return super().validate(attrs)

