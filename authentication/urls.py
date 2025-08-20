from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import *


router = DefaultRouter()
router.register(r'payment-gateways', BasePaymentGateWayViewSet, basename='payment-gateways')
router.register(r"sms-device-keys", SmsDeviceKeyViewSet, basename="sms-device-key")
router.register(r"store-payment-messages", StorePaymentMessageViewSet, basename="store-payment-message")


urlpatterns = [
    # Registration URLs=======================================================================
    path('auth/merchant/register/', MerchantRegisterView.as_view(), name='merchant-register'),
    path('auth/admin/register/', AdminOrStaffRegisterView.as_view(), name='admin-register'),
    
    # Login URL===============================================================================
    path('auth/merchant/login/', MerchantLoginView.as_view(), name='merchant-login'),
    path('auth/admin/login/', AdminLoginView.as_view(), name='admin-login'),
    
    # Token Related===========================================================================
    path('auth/token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', CustomTokenVerifyView.as_view(), name='token_verify'),
    path('auth/token/logout/', CustomLogOutView.as_view(), name='token_logout'),
    
    
    # User Profile URL
    path('user/profile/', UserProfileView.as_view(), name='user-profile'),
    path('user/profile/merchant/', UserMerchantProfileView.as_view(), name='user-profile-merchant'),
    path('profile/update/', UpdateUserMerchantAPIView.as_view(), name='user-merchant-profile-update'),
    path("api/keys/", APIKeyListOrDetailsAPIView.as_view(), name="api-key-list"),
    path("api/keys/<int:pk>/", APIKeyDetailAPIView.as_view(), name="api-key-detail"),
    
    
    path('admin/', include(router.urls)),
    path("store-payment-messages/", StorePaymentMessageCreateView.as_view(), name="store-payment-message-create"),
    path("device-verify/", VerifyDeviceKeyAPIView.as_view(), name="device-verify"),
    
]

