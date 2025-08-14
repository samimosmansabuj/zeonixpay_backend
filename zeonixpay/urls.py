from django.contrib import admin
from django.urls import path, include
from django.shortcuts import HttpResponse

def home(request):
    if request.GET['paymentID'] or request.GET['trxID'] or request.GET['transactionStatus']:
        return HttpResponse(f"Home! (Redirect - Bkash < Website < Client {request.GET['transactionStatus']} URL)")
    return HttpResponse(f"Home! (Redirect - Bkash < Website < Client Success/Cancel/Failed URL)")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', home, name='home'),
    path('api/v1/', include('authentication.urls')),
    path('api/v1/', include('core.urls')),
]





