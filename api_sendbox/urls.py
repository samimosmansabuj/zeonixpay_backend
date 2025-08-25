from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import *

urlpatterns = [
    path('payment/create/', SendBoxCreatePayment.as_view(), name='sendbox-create-payment'),
    path('payment/payout/', SendBoxPaymentPayOutView.as_view(), name='sendbox-payment-payout'),
    path('get-payment/', SendBoxGetOnlinePayment.as_view(), name='get-payment'),
]


