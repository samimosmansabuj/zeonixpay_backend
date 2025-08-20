from django.contrib import admin
from django.urls import path, include
from django.shortcuts import HttpResponse
from authentication.models import BasePaymentGateWay

def home(request):
    a = BasePaymentGateWay.objects.filter(method='bkash', is_active=True).order_by('id')
    print(a)
    try:
        if request.GET.get('paymentID') or request.GET.get('trxID') or request.GET.get('transactionStatus'):
            return HttpResponse(f"Home! (Redirect - Bkash < Website < Client {request.GET['transactionStatus']} URL)")
        return HttpResponse(f"Home! (Redirect - Bkash < Website < Client Success/Cancel/Failed URL)")
    except Exception as e:
        return HttpResponse(f"For Payment CallBack, Need paymentID from Payment Method! {e}")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', home, name='home'),
    path('api/v1/', include('authentication.urls')),
    path('api/v1/', include('core.urls')),
]





