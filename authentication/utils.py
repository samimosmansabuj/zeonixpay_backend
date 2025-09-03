
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework.exceptions import ValidationError, NotFound
from .permissions import IsOwnerByUser, AdminAllPermission
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.generics import CreateAPIView
from rest_framework import serializers, viewsets, exceptions
from django.contrib.auth import authenticate
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from .models import CustomUser, StorePaymentMessage
import random, string
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, JSONParser, FormParser


class CustomPagenumberpagination(PageNumberPagination):
    page_size = 2
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def paginate_queryset(self, queryset, request, view=None):
        all_items = request.query_params.get('all', 'false').lower() == 'true'
        page_size = request.query_params.get(self.page_size_query_param)
        if all_items or (page_size and page_size.isdigit() and int(page_size) == 0):
            self.all_data = queryset
            return None
        return super().paginate_queryset(queryset, request, view)
    
    def get_paginated_response(self, data):
        return Response(
            {
                'status': True,
                'count': self.page.paginator.count,
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
                'data': data
            }, status=status.HTTP_200_OK
        )


# ========================Authentication Token utils Start=============================
class CustomLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        username=data['username']
        password=data['password']
        try:
            user = CustomUser.objects.get(username=username)
            user_role = self.verify_user_role(user)
            
            if not user.check_password(password):
                raise AuthenticationFailed("Password is incorrect!", code='authorization')
            if user_role['status'] is False:
                raise AuthenticationFailed(user_role['message'], code='authorization')
        except CustomUser.DoesNotExist:
            raise AuthenticationFailed("Username is incorrect!", code='authorization')
        
        user = authenticate(username=username, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            return {
                'user': user.pid,
                'role': user.role.name,
                'refresh': str(refresh),
                'access': str(refresh.access_token)
            }
        raise serializers.ValidationError("Invalid credentials.")

class CustomTokenObtainPairView(APIView):
    serializer_class = None
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            return Response({
                'status': True,
                'message': 'Successfully Login',
                'token': serializer.validated_data
            }, status=status.HTTP_200_OK)
        except TokenError as e:
            raise InvalidToken(e.args[0])
        except ValidationError:
            return Response(
                {
                    'status': False,
                    'message': {kay: str(value[0]) for kay, value in serializer.errors.items()},
                }, status=status.HTTP_400_BAD_REQUEST
            )
        except AuthenticationFailed as e:
            return Response(
                {
                    'status': False,
                    'message': str(e)
                }, status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'message': str(e)
                }, status=status.HTTP_401_UNAUTHORIZED
            )
# ========================Authentication Token utils End===============================

# ========================Registration or Add User utils Start=========================
class CustomUserCreateAPIView(CreateAPIView):
    error_message = "Creation Unsuccessfull!"
    success_message = "Registration Successfully Completed!"
    
    def resposne_return(self, user):
        return Response({
            'status': True,
            'message': self.success_message
        }, status=status.HTTP_201_CREATED)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            user = self.perform_create(serializer)
            return self.resposne_return(user=user)
        except ValidationError:
            return Response({
                'status': False,
                'message': [str(value[0]) for kay, value in serializer.errors.items()][0]
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'status': False,
                'message': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ========================Registration or Add User utils End===========================


class CustomMerchantUserViewsets(viewsets.ModelViewSet):
    permission_classes = [AdminAllPermission]
    pagination_class = CustomPagenumberpagination
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    lookup_field = "pid"
    
    update_success_message = "User Profile Updated!"
    delete_success_message = "User Profile Deleted!"
    not_found_message = "User Profile Object Not Found!"
    
    def get_object(self):
        try:
            return CustomUser.objects.get(pid=self.kwargs.get("pid"))
        except CustomUser.DoesNotExist:
            raise exceptions.NotFound("User not Found with this PID")
    
    def list(self, request, *args, **kwargs):
        all_items = request.query_params.get('all', 'false').lower() == 'true'
        page_size = request.query_params.get(self.pagination_class.page_size_query_param)
        
        if all_items or (page_size and page_size.isdigit() and int(page_size)==0):
            try:
                response = self.get_serializer(self.get_queryset(), many=True)
                return Response(
                    {
                        'status': True,
                        'count': len(response.data),
                        'data': response.data
                    },
                    status=status.HTTP_200_OK
                )
            except Exception as e:
                return Response(
                    {
                        'status': False,
                        'error': str(e)
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        page = self.paginate_queryset(self.get_queryset())
        if page is not None:
            response = self.get_serializer(page, many=True)
            return Response(
                {
                    'status': True,
                    'count': self.paginator.page.paginator.count,
                    'next': self.paginator.get_next_link(),
                    'previous': self.paginator.get_previous_link(),
                    'data': response.data
                },
                status=status.HTTP_200_OK
            )
        else:
            try:
                response = self.get_serializer(self.get_queryset(), many=True)
                return Response(
                    {
                        'status': True,
                        'count': len(response.data),
                        'data': response.data
                    },
                    status=status.HTTP_200_OK
                )
            except Exception as e:
                return Response(
                    {
                        'status': False,
                        'error': str(e)
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
    
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            return Response(
                {
                    "status": True,
                    "message": self.get_serializer(instance).data
                }, status=status.HTTP_200_OK
            )
        except exceptions.NotFound as e:
            return Response(
                {
                    "status": False,
                    "message": str(e)
                }, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
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
        except ValidationError as e:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}
            return Response(
                {
                    'status': False,
                    'error': error
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return Response(
            {
                'status': True,
                'message': self.delete_success_message,
            }, status=status.HTTP_200_OK
        )


class CustomOnlyAdminCreateViewsetsViews(viewsets.ModelViewSet):
    permission_classes = [AdminAllPermission]
    # filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    
    
    pagination_class = None
    model = None
    
    create_success_message = "Device Key Object Created!"
    update_success_message = "Device Key Object Updated!"
    delete_success_message = "Device Key Object Deleted!"
    not_found_message = "Device Key Object Not Found!"
    
    def handle_exception(self, exc):
        response = super().handle_exception(exc)
        if response is not None:
            detail = response.data.get("detail")
            if detail is not None:
                response.data = {"status": False, "message": self.not_found_message}
        return response
    
    def retrieve(self, request, *args, **kwargs):
        object = self.get_object()
        try:
            return Response(
                {
                    'status': True,
                    'data': self.get_serializer(object).data
                }, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'data': str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )
    
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
        except ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}
            return Response(
                {
                    'status': False,
                    'error': error
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'data': str(e)
                }, status=status.HTTP_400_BAD_REQUEST
            )
    
    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return Response(
            {
                'status': True,
                'message': self.delete_success_message,
            }, status=status.HTTP_200_OK
        )
    
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(
                {
                    'status': True,
                    'message': self.create_success_message,
                    'data': serializer.data
                }, status=status.HTTP_201_CREATED
            )
        except ValidationError:
            error = {key: str(value[0]) for key, value in serializer.errors.items()}
            return Response(
                {
                    'status': False,
                    'error': error
                },status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if queryset is None:
            return Response(
                {
                    'status': True,
                    'message': "Can't Get with this User!"
                }
            )
        
        all_items = request.query_params.get('all', 'false').lower() == 'true'
        page_size = request.query_params.get(self.pagination_class.page_size_query_param)
        
        
        if all_items or (page_size and page_size.isdigit() and int(page_size)==0):
            try:
                response = self.get_serializer(queryset, many=True)
                return Response(
                    {
                        'status': True,
                        'count': len(response.data),
                        'data': response.data
                    },
                    status=status.HTTP_200_OK
                )
            except Exception as e:
                return Response(
                    {
                        'status': False,
                        'error': str(e)
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            response = self.get_serializer(page, many=True)
            return Response(
                {
                    'status': True,
                    'count': self.paginator.page.paginator.count,
                    'next': self.paginator.get_next_link(),
                    'previous': self.paginator.get_previous_link(),
                    'data': response.data
                },
                status=status.HTTP_200_OK
            )
        else:
            try:
                response = self.get_serializer(queryset, many=True)
                return Response(
                    {
                        'status': True,
                        'count': len(response.data),
                        'data': response.data
                    },
                    status=status.HTTP_200_OK
                )
            except Exception as e:
                return Response(
                    {
                        'status': False,
                        'error': str(e)
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            

    


# ==========================Generate Utils Method Start================================
def genereate_merchant_id(model):
        unique = False
        while not unique:
            merchant_id = ''.join(random.choices(string.digits, k=6))
            if not model.objects.filter(merchant_id=merchant_id).exists():
                unique = True
                return merchant_id

# ==========================Generate Utils Method End================================

