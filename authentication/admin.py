from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.html import format_html
from django.contrib import admin

from .models import (
    UserRole,
    CustomUser,
    UserId,
    Merchant,
    APIKey,
    MerchantWallet,
    UserPaymentMethod,
    BasePaymentGateWay, StorePaymentMessage, SmsDeviceKey
)


# ---------- Simple admins ----------
@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "permission")
    search_fields = ("name", "permission")


@admin.register(UserId)
class UserIdAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "referal_key", "activation_key", "reset_key")
    search_fields = ("user__username", "referal_key", "activation_key", "reset_key")
    autocomplete_fields = ("user",)
    readonly_fields = ("referal_key",)


# ---------- CustomUser with inline for UserId ----------
class UserIdInline(admin.StackedInline):
    model = UserId
    can_delete = False
    fk_name = "user"
    extra = 0


@admin.register(CustomUser)
class CustomUserAdmin(DjangoUserAdmin):
    inlines = [UserIdInline]

    # What shows in the list view
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "phone_number",
        "status",
        "role",
        "is_staff",
        "pid",
    )
    list_filter = ("status", "role", "is_staff", "is_superuser", "is_active")
    search_fields = ("username", "email", "first_name", "last_name", "phone_number")
    readonly_fields = ("pid",)

    # Add our custom fields to the fieldsets used by DjangoUserAdmin
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Personal info",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "phone_number",
                    "more_information",
                )
            },
        ),
        (
            "Status & Role",
            {
                "fields": (
                    "status",
                    "role",
                    "pid",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "password1",
                    "password2",
                    "first_name",
                    "last_name",
                    "email",
                    "phone_number",
                    "status",
                    "role",
                    "is_staff",
                    "is_superuser",
                    "is_active",
                ),
            },
        ),
    )


# ---------- Merchant and related one-to-ones ----------
class APIKeyInline(admin.StackedInline):
    model = APIKey
    can_delete = False
    extra = 0
    readonly_fields = ("api_key", "secret_key", "created_at")


class MerchantWalletInline(admin.StackedInline):
    model = MerchantWallet
    can_delete = False
    extra = 0
    readonly_fields = ("wallet_id", "balance", "withdraw_processing", "total_withdraw")


@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    inlines = [APIKeyInline, MerchantWalletInline]

    list_display = (
        "brand_name",
        "user",
        "merchant_id",
        "status",
        "fees_type",
        "fees",
        "is_active",
        "domain_name",
    )
    search_fields = ("brand_name", "domain_name", "user__username", "user__email", "whatsapp_number")
    list_filter = ("status", "fees_type", "is_active")
    autocomplete_fields = ("user",)
    readonly_fields = ("merchant_id", "is_active")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "user",
                    "merchant_id",
                    "brand_name",
                    "brand_logo",
                    "domain_name",
                    "whatsapp_number",
                )
            },
        ),
        (
            "Status & Fees",
            {
                "fields": (
                    "status",
                    "fees_type",
                    "fees",
                    "is_active",
                )
            },
        ),
    )


# ---------- APIKey & MerchantWallet standalone admins (optional, still useful) ----------
@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ("merchant", "api_key", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("merchant__brand_name", "merchant__user__username", "api_key")
    autocomplete_fields = ("merchant",)
    readonly_fields = ("api_key", "secret_key", "created_at")


@admin.register(MerchantWallet)
class MerchantWalletAdmin(admin.ModelAdmin):
    list_display = ("merchant", "wallet_id", "balance", "withdraw_processing", "total_withdraw")
    search_fields = ("merchant__brand_name", "merchant__user__username", "wallet_id")
    autocomplete_fields = ("merchant",)
    readonly_fields = ("wallet_id",)


# ---------- Payment methods ----------
@admin.register(UserPaymentMethod)
class UserPaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("method_type", "merchant", "status", "created_at", "updated_at")
    list_filter = ("method_type", "status", "created_at")
    search_fields = ("merchant__brand_name", "merchant__user__username")
    autocomplete_fields = ("merchant",)

    # Pretty-print JSON safely in detail view
    readonly_fields = ("_pretty_params",)
    fields = ("merchant", "method_type", "status", "params", "_pretty_params", "created_at", "updated_at")
    readonly_fields = ("_pretty_params", "created_at", "updated_at")

    def _pretty_params(self, obj):
        if not obj or not obj.params:
            return "-"
        import json
        return format_html("<pre style='white-space:pre-wrap;max-width:100%;'>{}</pre>", json.dumps(obj.params, indent=2))

    _pretty_params.short_description = "Params (pretty)"








@admin.register(BasePaymentGateWay)
class BasePaymentGateWayAdmin(admin.ModelAdmin):
    list_display = ("id", "method", "method_uuid", "base_url", "callback_base_url", "created_at", "updated_at")
    list_filter = ("method", "created_at")
    search_fields = ("method", "method_uuid", "base_url", "callback_base_url")
    ordering = ("-created_at",)
    readonly_fields = ("method_uuid", "created_at", "updated_at")


@admin.register(SmsDeviceKey)
class SmsDeviceKeyAdmin(admin.ModelAdmin):
    list_display = ("id", "device_name", "device_key", "is_active", "create_at", "updated_ta")
    list_filter = ("is_active", "create_at")
    search_fields = ("device_name", "device_key")
    ordering = ("-create_at",)


@admin.register(StorePaymentMessage)
class StorePaymentMessageAdmin(admin.ModelAdmin):
    list_display = ("message_from", "message", "trx_id", "message_amount", "payment_number", "message_date", "is_verified", "create_at")
    list_filter = ("message_date", "device", "create_at")
    search_fields = ("payment_number", "device__device_name", "message")
    ordering = ("-create_at",)



