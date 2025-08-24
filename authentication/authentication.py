from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import SmsDeviceKey

class DeviceUser:
    def __init__(self, device):
        self.device = device
    @property
    def is_authenticated(self):
        return True

class DeviceAuthentication(BaseAuthentication):
    header_key = "X-Device-Key"
    header_pin = "X-Device-Pin"

    def authenticate(self, request):
        key = request.headers.get(self.header_key)
        pin = request.headers.get(self.header_pin)

        if not key or not pin:
            raise AuthenticationFailed("Missing device credentials.")

        try:
            device = SmsDeviceKey.objects.get(device_key=key, is_active=True)
        except SmsDeviceKey.DoesNotExist:
            raise AuthenticationFailed("Invalid or inactive device key.")

        if hasattr(device, "check_pin"):
            if not device.check_pin(pin):
                raise AuthenticationFailed("Invalid device PIN.")
        else:
            if device.device_pin != pin:
                raise AuthenticationFailed("Invalid device PIN.")

        return (DeviceUser(device), device)

