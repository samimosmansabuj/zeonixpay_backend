from django.urls import path
from .views import (
    RegisterMerchantView,
    MerchantLoginView,
    UserProfileView,
    UserBrandView,
    UserBrandDetailView,
    UserPaymentMethodView,
    UserPaymentMethodDetailView,
    AdminLoginView,
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # Registration URLs=======================================================================
    path('auth/merchant/register/', RegisterMerchantView.as_view(), name='merchant-register'),
    # path('auth/admin/register/', RegisterAdminOrStaffView.as_view(), name='admin-register'),
    
    # Login URL===============================================================================
    path('auth/merchant/login/', MerchantLoginView.as_view(), name='merchant-login'),
    path('auth/admin/login/', AdminLoginView.as_view(), name='admin-login'),
    
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # User Profile URL
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    
    # User Brand URLs
    path('brands/', UserBrandView.as_view(), name='user-brand-list-create'),
    path('brands/<int:pk>/', UserBrandDetailView.as_view(), name='user-brand-detail'),
    
    # User Payment Method URLs
    path('payment-methods/', UserPaymentMethodView.as_view(), name='user-payment-method-list-create'),
    path('payment-methods/<int:pk>/', UserPaymentMethodDetailView.as_view(), name='user-payment-method-detail'),
]

