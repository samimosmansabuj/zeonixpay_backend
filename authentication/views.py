from .serializers import CustomUserSerializer, RegistrationSerializer, MerchantLoginSerializer, AdminLoginSerializer, MerchantRegistrationSerializer, MerchantSerializer, UserSerializer, BasePaymentGateWaySerializer, StorePaymentMessageSerializer, SmsDeviceKeySerializer, APIKeySerializer, MerchantUserListSerializer
from .models import UserRole, Merchant, BasePaymentGateWay, StorePaymentMessage, SmsDeviceKey, APIKey, CustomUser
from .utils import CustomTokenObtainPairView, CustomUserCreateAPIView, CustomOnlyAdminCreateViewsetsViews, CustomPagenumberpagination, CustomMerchantUserViewsets
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from .permissions import AdminCreatePermission, AdminAllPermission
from rest_framework import generics, status, exceptions, viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from .authentication import DeviceAuthentication
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import QuerySet
from django.http import Http404
from rest_framework.parsers import MultiPartParser, JSONParser, FormParser
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



# ======================================================================================================
# ========================================User Merchant Views Start=======================
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
            }, status=status.HTTP_200_OK
        )
    
    def put(self, request, *args, **kwargs):
        try:
            serializer = CustomUserSerializer(self.get_object(), data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                {
                    "status": True,
                    "message": "User Data Successfully Updated!"
                }, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )

class OnlyMerchantProfileAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = MerchantSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user.merchant if self.request.user.merchant else None
    
    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        return Response(
            {
                'status': True,
                'data': response.data
            }, status=status.HTTP_200_OK
        )
    
    
    def put(self, request, *args, **kwargs):
        merchant = request.user.merchant
        serializer = MerchantSerializer(merchant, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(
            {
                "status": True,
                "message": "Merchant Data Successfully Updated!"
            }, status=status.HTTP_200_OK
        )


@api_view(["POST"])
@permission_classes([AdminCreatePermission])
def userApproval(request, pid):
    if not request.user.is_authenticated:
        return Response(
            {"status": False, "message": "Authentication Failed"}, 
            status=status.HTTP_401_UNAUTHORIZED
        )

    if request.user.role.name.lower() != 'admin':
        return Response(
            {"status": False, "message": "Only admin user approved!"}, 
            status=status.HTTP_406_NOT_ACCEPTABLE
        )
    
    try:
        user = CustomUser.objects.get(pid=pid)
    except CustomUser.DoesNotExist:
        return Response(
            {"status": False, "message": "Wrong User Personal ID"}, 
            status=status.HTTP_404_NOT_FOUND
        )

    status_value = request.data.get("status", "").lower()
    
    if status_value not in ['active', 'disable']:
        return Response(
            {"status": False, "message": "Wrong status value!"}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    if user.status.lower() == status_value:
        return Response(
            {"status": True, "message": f"User already {user.status}!"}, 
            status=status.HTTP_200_OK
        )

    user.status = status_value.capitalize()
    user.save()

    return Response(
        {"status": True, "message": f"User {user.status}!"}, 
        status=status.HTTP_200_OK
    )

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def userPasswordReset(request, pid=None):
    if not request.user.is_authenticated:
        return Response(
            {"status": False, "message": "Authentication Failed"}, 
            status=status.HTTP_401_UNAUTHORIZED
        )

    reset_password = request.data.get("reset_password", None)
    if reset_password is None:
        return Response(
            {
                "status": False,
                "message": "Reset Password Field is empty!"
            }, status=status.HTTP_400_BAD_REQUEST
        )
    
    if pid and request.user.role.name.lower() == 'admin':
        try:
            user = CustomUser.objects.get(pid=pid)
        except CustomUser.DoesNotExist:
            return Response(
                {"status": False, "message": "Wrong User Personal ID"}, 
                status=status.HTTP_404_NOT_FOUND
            )
    else:
        user = request.user
    
    user.set_password(reset_password)
    user.save(update_fields=["password"])
    return Response(
        {"status": True, "message": "Password reset successful."},
        status=status.HTTP_200_OK
    )


class APIKeyListOrDetailsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_merchant(self, request):
        user = request.user
        return getattr(user, "merchant", None)
    
    def get_resource(self, request):
        merchant = self.get_merchant(request)
        if merchant:
            return get_object_or_404(APIKey, merchant=merchant)
        elif self.request.user.role.name.lower() == "admin":
            return APIKey.objects.all().order_by("-created_at")
        return None

    def get(self, request, *args, **kwargs):
        resource = self.get_resource(request)
        if resource is None:
            msg = "No API Key available for this merchant!" if self.get_merchant(request) \
                  else "Not API Key available for this user!"
            return Response({"status": True, "message": msg}, status=status.HTTP_200_OK)
        
        many = isinstance(resource, QuerySet)
        serializer = APIKeySerializer(resource, many=many)
        
        if many:
            return Response(
                {"status": True, "count": resource.count(), "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        else:
            return Response({"status": True, "data": serializer.data}, status=status.HTTP_200_OK)
    
    def post(self, request, *args, **kwargs):
        try:
            resource = self.get_resource(request)
        except Http404:
            merchant = self.get_merchant(request)
            if merchant:
                APIKey.objects.create(merchant=merchant, is_active=True)
                return Response({"status": True, "message": "New APIKey Generate..."}, status=status.HTTP_200_OK)
            resource = None
        
        if resource is None:
            return Response({"status": False, "message": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        
        if isinstance(resource, QuerySet):
            raw_key = request.data.get("api_key")
            if not raw_key:
                return Response({"status": False, "message": "Need APIKey..."}, status=status.HTTP_400_BAD_REQUEST)
            api_key_obj = get_object_or_404(resource, api_key=raw_key)
            target_merchant = api_key_obj.merchant
            APIKey.objects.filter(merchant=target_merchant).delete()
            APIKey.objects.create(merchant=target_merchant, is_active=True)
            return Response({"status": True, "message": "New APIKey Generate..."}, status=status.HTTP_200_OK)
        
        api_key_obj = resource
        target_merchant = api_key_obj.merchant
        api_key_obj.delete()
        APIKey.objects.create(merchant=target_merchant, is_active=True)
        return Response({"status": True, "message": "New APIKey Generate..."}, status=status.HTTP_200_OK)
    
    
    def _coerce_bool(self, val):
        if isinstance(val, bool):
            return val
        if val is None:
            return None
        return str(val).strip().lower() in ("true", "1", "yes", "y", "on")
    
    def patch(self, request, *args, **kwargs):
        try:
            resource = self.get_resource(request)
        except Http404:
            if self.get_merchant(request):
                return Response(
                    {"status": False, "message": "No API Key available for this merchant!"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(
                {"status": False, "message": "Not allowed."},
                status=status.HTTP_403_FORBIDDEN,
            )
        
        if resource is None:
            return Response(
                {"status": False, "message": "Not allowed."},
                status=status.HTTP_403_FORBIDDEN,
            )
        
        is_active_in = self._coerce_bool(request.data.get("is_active"))
        
        if isinstance(resource, QuerySet):
            raw_key = request.data.get("api_key")
            if not raw_key:
                return Response(
                    {"status": False, "message": "Need APIKey..."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            api_key_obj = get_object_or_404(resource, api_key=raw_key)
            if is_active_in is not None:
                api_key_obj.is_active = is_active_in
                api_key_obj.save(update_fields=["is_active"])
            return Response(
                {
                    "status": True,
                    "message": f"APIKey is {'Active' if api_key_obj.is_active else 'Deactive'}"
                },
                status=status.HTTP_200_OK,
            )
        
        api_key_obj = resource
        if is_active_in is not None:
            api_key_obj.is_active = is_active_in
            api_key_obj.save(update_fields=["is_active"])
        return Response(
            {
                "status": True,
                "message": f"APIKey is {'Active' if api_key_obj.is_active else 'Deactive'}"
            },
            status=status.HTTP_200_OK,
        )

class APIKeyDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_merchant(self, request):
        user = request.user
        return getattr(user, "merchant", None)

    def get(self, request, pk, *args, **kwargs):
        merchant = self.get_merchant(request)
        try:
            if merchant:
                api_key = get_object_or_404(APIKey, merchant=merchant, pk=pk)
            elif request.user.role.name.lower() == "admin":
                api_key = get_object_or_404(APIKey, pk=pk)
            else:
                raise exceptions.NotFound("APIKey Object not found!")

            serializer = APIKeySerializer(api_key)
            return Response({"status": True, "data": serializer.data}, status=status.HTTP_200_OK)
        except exceptions.NotFound as e:
            return Response({"status": False, "message": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"status": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)



class AdminStaffUserList(CustomMerchantUserViewsets):
    queryset = CustomUser.objects.filter(role__name="Admin")
    serializer_class = CustomUserSerializer

class MerchatUserList(CustomMerchantUserViewsets):
    queryset = CustomUser.objects.filter(role__name="Merchant")
    serializer_class = MerchantUserListSerializer
    
    def update(self, request, *args, **kwargs):
        try:
            object = self.get_object()
            serializer = self.get_serializer(object, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(
                {
                    'status': True,
                    'message': self.update_success_message,
                    'data': serializer.data
                },
                status=status.HTTP_200_OK
            )
        except exceptions.ValidationError as e:
            detail = getattr(e, "detail", None)
            def first(err):
                if isinstance(err, list):
                    if not err:
                        return []
                    return first(err[0]) if any(isinstance(err[0], (dict, list)) for _ in [0]) else str(err[0])
                if isinstance(err, dict):
                    return {k: first(v) for k, v in err.items()}
                return str(err)
            return Response({'status': False, 'error': first(detail) if detail is not None else {}}, status=status.HTTP_400_BAD_REQUEST)

# ========================================User Merchant Views End==========================
# ======================================================================================================



# ======================================================================================================
# ===============Site Payment Gate, And Payment Message Store and Device Management Start==========
class BasePaymentGateWayViewSet(viewsets.ModelViewSet):
    queryset = BasePaymentGateWay.objects.all().order_by('-created_at')
    serializer_class = BasePaymentGateWaySerializer
    permission_classes = [AdminAllPermission]
    lookup_field = 'method_uuid'

    def get_queryset(self):
        queryset = super().get_queryset()
        method = self.request.query_params.get('method')
        if method:
            queryset = queryset.filter(method=method)
        return queryset


class SmsDeviceKeyViewSet(CustomOnlyAdminCreateViewsetsViews):
    queryset = SmsDeviceKey.objects.all().order_by("-create_at")
    serializer_class = SmsDeviceKeySerializer
    permission_classes = [AdminAllPermission]
    # filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["device_key"]
    ordering_fields = ["create_at", "updated_ta"]
    lookup_field = 'device_key'
    
    create_success_message = "Device Key Object Created!"
    update_success_message = "Device Key Object Updated!"
    delete_success_message = "Device Key Object Deleted!"
    not_found_message = "Device Key Object Not Found!"


class StorePaymentMessageViewSet(CustomOnlyAdminCreateViewsetsViews):
    queryset = StorePaymentMessage.objects.all().order_by("-create_at")
    serializer_class = StorePaymentMessageSerializer
    # filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["payment_number", "message"]
    ordering_fields = ["message_date", "create_at"] 
    
    create_success_message = "Message Store Object Created!"
    update_success_message = "Message Store Object Updated!"
    delete_success_message = "Message Store Object Deleted!"
    not_found_message = "Message Store Object Not Found!"


# -----------------------------------------------------------------------------------------------------------
class StorePaymentMessageCreateView(generics.CreateAPIView):
    queryset = StorePaymentMessage.objects.all()
    serializer_class = StorePaymentMessageSerializer
    authentication_classes = [DeviceAuthentication]
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            device = getattr(request.user, "device", None)
            serializer.save(device=device)
            return Response({"status": True, "data": serializer.data}, status=status.HTTP_201_CREATED)
        except exceptions.ValidationError:
            return Response(
                {
                    'status': False,
                    'message': next(iter(serializer.errors.values()))[0],
                },status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'message': str(e),
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class VerifyDeviceKeyAPIView(APIView):
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):
        device_key = request.headers.get("X-Device-Key") or request.data.get("device_key")
        pin = request.headers.get("X-Device-Pin") or request.data.get("pin")
        if not device_key:
            return Response(
                {"status": False, "message": "Device key is required (X-Device-Key header or device_key in body)."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not pin:
            return Response(
                {"status": False, "message": "Pin is required (X-Device-Pin header or pin in body)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        device = SmsDeviceKey.objects.filter(device_key=device_key).first()
        exists = device is not None
        pin_ok = device.check_pin(pin) if device else False
        active = device.is_active if device else False

        payload = {
            "verified": True,
        }
        if exists:
            payload["device"] = {
                "device_name": device.device_name,
                "device_key": device.device_key,
                "is_active": device.is_active,
                "create_at": device.create_at,
                "updated_ta": device.updated_ta,
            }
        
        if not exists:
            return Response(
                {
                    'verified': False,
                    'message': 'Invalid Device Key!'
                }, status=status.HTTP_401_UNAUTHORIZED
            )
        elif pin_ok is False:
            return Response(
                {
                    'verified': False,
                    'message': 'Wrong PIN!'
                }, status=status.HTTP_401_UNAUTHORIZED
            )
        if active is False:
            return Response(
                {
                    'verified': False,
                    'message': 'Device is not Active!'
                }, status=status.HTTP_401_UNAUTHORIZED
            )
        return Response(payload, status=status.HTTP_200_OK)

# -----------------------------------------------------------------------------------------------------------
# ===============Site Payment Gate, And Payment Message Store and Device Management End==========
# ======================================================================================================


