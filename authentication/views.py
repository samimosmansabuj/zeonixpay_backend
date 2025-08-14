from rest_framework import generics, status, exceptions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import PermissionDenied
from .models import CustomUser, UserPaymentMethod, UserId, UserRole, Merchant, MerchantWallet
from .serializers import CustomUserSerializer, RegistrationSerializer, MerchantLoginSerializer, UserPaymentMethodSerializer, AdminLoginSerializer, MerchantRegistrationSerializer, MerchantSerializer, UserSerializer
from .utils import CustomTokenObtainPairView, CustomUserCreateAPIView, CustomMerchantUserViewsets
from .permissions import AdminCreatePermission
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view, permission_classes


# ========================Registration/Account Create Views Start===============================
class MerchantRegisterView(CustomUserCreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = MerchantRegistrationSerializer
    error_message = 'Registration Unsuccessfull!'
    success_message = "Registration Successfully Completed!"

    def perform_create(self, serializer):
        try:
            role = UserRole.objects.get(name='Merchant')
            user = serializer.save(role=role)
            return user
        except UserRole.DoesNotExist:
            raise exceptions.NotFound("Merchant role nout Found!")

class AdminOrStaffRegisterView(CustomUserCreateAPIView):
    permission_classes = [AdminCreatePermission]
    serializer_class = RegistrationSerializer
    error_message = 'User Add Unsuccessfull!'
    success_message = "User Successfully Added!"

    def perform_create(self, serializer):
        user = serializer.save()
        return user

# ========================Registration/Account Create Views End===============================

# ========================Authentication Token Views Start================================
class AdminLoginView(CustomTokenObtainPairView):
    serializer_class = AdminLoginSerializer
    
class MerchantLoginView(CustomTokenObtainPairView):
    serializer_class = MerchantLoginSerializer
# ========================Authentication Token Views End================================

# ========================Token Handling Views Start================================
class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            return Response({
                'status': True,
                'message': 'Token refreshed successfully',
                'token': serializer.validated_data
            }, status=status.HTTP_200_OK)
        except exceptions.ValidationError:
            error = {kay: str(value[0]) for kay, value in serializer.errors.items()}
            return Response({
                'status': False,
                'message': 'Token refresh failed',
                'errors': error
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'status': False,
                'message': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CustomTokenVerifyView(TokenVerifyView):
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            return Response(
                {
                    'status': True,
                    'messgae': 'Token is valid!'
                }, status=status.HTTP_200_OK
            )
        except exceptions.ValidationError:
            error = {kay: str(value[0]) for kay, value in serializer.errors.items()}
            return Response(
                {
                    'status': False,
                    'message': 'Token is invalid!',
                    'errors': error
                },status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'message': str(e),
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CustomLogOutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response(
                    {
                        'status': False,
                        'message': 'Please input refresh token!',
                    }, status=status.HTTP_400_BAD_REQUEST
                )
            
            token = RefreshToken(refresh_token)
            token.blacklist()
            # request.user.auth_token_set.all().delete()
            return Response(
                {
                    'status': True,
                    'message': 'Logout Successfully!'
                }, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'message': 'Invalid Token!',
                    'error': str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )

# ========================Token Handling Views End================================



# User Profile Views
class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
    
    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        return Response(
                {
                    'status': True,
                    'data': response.data
                }
            )

class UserMerchantProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = MerchantSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        try:
            return Merchant.objects.get(user=self.request.user)
        except Merchant.DoesNotExist:
            return Response(
                {
                    'status': False,
                    'message': 'Merchant Profile Not Created!'
                }, status=status.HTTP_404_NOT_FOUND
            )
    
    def retrieve(self, request, *args, **kwargs):
        if self.request.user.role.name == 'Merchant':
            response = super().retrieve(request, *args, **kwargs)
            return Response(
                    {
                        'status': True,
                        'data': response.data
                    }
                )
        else:
            return Response(
                {
                    'status': False,
                    'message': 'This is not a merchant account!'
                }, status=status.HTTP_400_BAD_REQUEST
            )


class UpdateUserMerchantAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def put(self, request, *args, **kwargs):
        user = request.user
        user_serializer = UserSerializer(user, data=request.data.get('user', {}), partial=True)
        
        if user_serializer.is_valid():
            user_serializer.save()
        else:
            return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if hasattr(user, 'merchant') and user.merchant:
            merchant_serializer = MerchantSerializer(user.merchant, data=request.data.get('merchant', {}), partial=True)
            if merchant_serializer.is_valid():
                merchant_serializer.save()
            else:
                return Response(merchant_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(
            {
                "status": True,
                "message": "Updated successfully"
            }, status=status.HTTP_200_OK
        )


