from django.urls import path, include
from .views import MerchantRegisterView, AdminOrStaffRegisterView, MerchantLoginView, AdminLoginView, UserProfileView, UserBrandView, UserPaymentMethodView, CustomTokenRefreshView, CustomTokenVerifyView, CustomLogOutView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'brands', UserBrandView, basename='user-brands')
router.register(r'payment-methods', UserPaymentMethodView, basename='user-payment-method')


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
    path('merchant/profile/', UserProfileView.as_view(), name='user-profile'),
    path('merchant/<str:pid>/', include(router.urls)),
    
    # # User Payment Method URLs
    # path('payment-methods/', UserPaymentMethodView.as_view(), name='user-payment-method-list-create'),
]

