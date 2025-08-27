from django.contrib import admin
from django.urls import path, include, re_path
from django.shortcuts import HttpResponse
from authentication.models import BasePaymentGateWay
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve as static_serve
import os

admin.site.site_title = "ZeonixPay"
admin.site.site_header = "ZeonixPay"
admin.site.app_index = "Welcome to ZeonixPay"

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

SERVE_MEDIA = os.getenv("SERVE_MEDIA", "False").strip().lower() in ("true","1","yes")

if SERVE_MEDIA:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', static_serve, {'document_root': settings.MEDIA_ROOT}),
        re_path(r'^static/(?P<path>.*)$', static_serve, {'document_root': settings.STATIC_ROOT}),
    ]


