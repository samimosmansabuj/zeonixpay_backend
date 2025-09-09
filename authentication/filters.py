import django_filters
from django_filters import rest_framework as filters
from .models import CustomUser, SmsDeviceKey

class CustomUserFilter(filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=CustomUser.STATUS)
    class Meta:
        model = CustomUser
        fields = ["status"]

class SmsDeviceKeyFilter(django_filters.FilterSet):
    is_active = django_filters.BooleanFilter(field_name='is_active')
    class Meta:
        model = SmsDeviceKey
        fields = ['is_active']



