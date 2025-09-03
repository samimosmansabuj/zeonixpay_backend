from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import *


router = DefaultRouter()
router.register(r'payment-gateways', BasePaymentGateWayViewSet, basename='payment-gateways')
router.register(r"sms-device-keys", SmsDeviceKeyViewSet, basename="sms-device-key")
router.register(r"store-payment-messages", StorePaymentMessageViewSet, basename="store-payment-message")

router.register(r"user", AdminStaffUserList, basename="admin-staff-user")
router.register(r"merchant", MerchatUserList, basename="merchant-user")


urlpatterns = [
    # Registration URLs=======================================================================
    path('auth/merchant/register/', MerchantRegisterView.as_view(), name='merchant-register'),
    path('auth/admin/register/', AdminOrStaffRegisterView.as_view(), name='admin-register'),
    
    # Login URL===============================================================================
    path('auth/merchant/login/', MerchantLoginView.as_view(), name='merchant-login'),
    path('auth/admin/login/', AdminLoginView.as_view(), name='admin-login'),
    path('auth/staff/login/', StaffLoginView.as_view(), name='staff-login'),
    
    # Token Related===========================================================================
    path('auth/token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', CustomTokenVerifyView.as_view(), name='token_verify'),
    path('auth/token/logout/', CustomLogOutView.as_view(), name='token_logout'),
    
    
    # User Profile URL
    path('user/profile/', UserProfileView.as_view(), name='user-profile'),
    path('user/merchant-profile/', OnlyMerchantProfileAPIView.as_view(), name='merchant-profile-update'),
    
    path('user/approved/<str:pid>/', userApproval, name="user-approved"),
    path('user/password-reset/', userPasswordReset, name="current-user-password-reset"),
    path('user/password-reset/<str:pid>/', userPasswordReset, name="user-password-reset"),
    
    
    path("app/keys/", APIKeyListOrDetailsAPIView.as_view(), name="api-key-list"),
    path("app/keys/<int:pk>/", APIKeyDetailAPIView.as_view(), name="api-key-detail"),
    
    
    
    path('admin/', include(router.urls)),
    
    #Device API
    path("store-payment-messages/", StorePaymentMessageCreateView.as_view(), name="store-payment-message-create"),
    path("device-verify/", VerifyDeviceKeyAPIView.as_view(), name="device-verify"),
    
]

