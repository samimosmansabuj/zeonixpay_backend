from django.contrib import admin
from authentication.models import CustomUser, UserBrand, UserWallet, UserRole, UserId, UserPaymentMethod, Merchant

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('pid', 'username', 'email', 'phone_number', 'status', 'role')
    list_filter = ('status', 'role')
    search_fields = ('username', 'email', 'phone')


@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = ('user', 'api_key', 'secret_key', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('user', 'api_key', 'secret_key')


@admin.register(UserBrand)
class UserBrandAdmin(admin.ModelAdmin):
    list_display = ('id', 'brand_name', 'user', 'domain_name', 'status', 'fees_type', 'fees')
    list_filter = ('status', 'fees_type')
    search_fields = ('brand_name', 'user__username', 'domain_name')


@admin.register(UserWallet)
class UserWalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'wallet_id', 'balance', 'withdraw_processing', 'total_withdraw')


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'permission')


@admin.register(UserId)
class UserIdsAdmin(admin.ModelAdmin):
    list_display = ('user', 'referal_key', 'activation_key', 'reset_key')


@admin.register(UserPaymentMethod)
class UserPaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['user', 'brand', 'method_type', 'params', 'status', 'updated_at']
    list_filter = ('status', 'method_type')


