from rest_framework import generics, status, exceptions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .models import CustomUser, UserBrand, UserPaymentMethod, UserWallet, UserId, UserRole
from .serializers import CustomUserSerializer, RegistrationSerializer, MerchantLoginSerializer, UserBrandSerializer, UserPaymentMethodSerializer, AdminLoginSerializer
from .utils import CustomTokenObtainPairView, CustomUserCreateAPIView

# Registration Views
class RegisterMerchantView(CustomUserCreateAPIView):
    serializer_class = RegistrationSerializer
    error_message = 'Registration Unsuccessfull!'

    def perform_create(self, serializer):
        try:
            role = UserRole.objects.get(name='Merchant')
            user = serializer.save(role=role)
            return user
        except UserRole.DoesNotExist:
            raise exceptions.NotFound("Merchant role nout Found!")

# class RegisterAdminOrStaffView(generics.CreateAPIView):
#     queryset = CustomUser.objects.all()
#     serializer_class = RegistrationSerializer

#     def perform_create(self, serializer):
#         user = serializer.save()
#         user.role = UserRole.objects.get(name='admin') 
#         user.save()




# ========================Authentication Token Serializer Start================================
class AdminLoginView(CustomTokenObtainPairView):
    serializer_class = AdminLoginSerializer
    
class MerchantLoginView(CustomTokenObtainPairView):
    serializer_class = MerchantLoginSerializer
# ========================Authentication Token Serializer End================================






# User Profile Views
class UserProfileView(generics.RetrieveUpdateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


# User Brand Views (for merchants)
class UserBrandView(generics.ListCreateAPIView):
    queryset = UserBrand.objects.all()
    serializer_class = UserBrandSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserBrandDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = UserBrand.objects.all()
    serializer_class = UserBrandSerializer
    permission_classes = [IsAuthenticated]


# User Payment Method Views
class UserPaymentMethodView(generics.ListCreateAPIView):
    queryset = UserPaymentMethod.objects.all()
    serializer_class = UserPaymentMethodSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserPaymentMethodDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = UserPaymentMethod.objects.all()
    serializer_class = UserPaymentMethodSerializer
    permission_classes = [IsAuthenticated]
