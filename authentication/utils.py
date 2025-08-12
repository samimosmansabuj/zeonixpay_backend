from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.views import APIView
from rest_framework import serializers, viewsets
from .models import CustomUser, UserBrand
from rest_framework.generics import CreateAPIView
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError, NotFound
from rest_framework.response import Response
from .permissions import IsOwnerByUser

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
    permission_classes = [IsOwnerByUser]
    pagination_class = None
    
    model = None
    create_success_message = "Created!"
    update_success_message = "Updated!"
    delete_success_message = "Deleted!"
    not_found_message = "Object Not Found!"
    
    #----------User-----------------------------------
    def get_user(self):
        pid = self.kwargs.get('pid')
        try:
            user = CustomUser.objects.get(pid=pid)
        except CustomUser.DoesNotExist:
            user = None
        return user
    
    #-------------Object Queryset-----------------------
    def get_queryset(self):
        user = self.get_user()
        if user:
            return self.model.objects.filter(user=user)
        return self.model.objects.none()
    
    #-------------Created-------------------------------
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
    
    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(user=user)
    
    
    #-------------------Queryset List-------------------
    def list(self, request, *args, **kwargs):
        try:
            response = super().list(request, *args, **kwargs).data
            return Response(
                {
                    'status': True,
                    'count': len(response),
                    'data': response
                }, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get_object(self):
        try:
            query_set = self.get_queryset()
            return query_set.get(pk=self.kwargs.get('pk'))
        except self.model.DoesNotExist:
            raise NotFound({
                'status': False,
                'message': self.not_found_message
            })
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response(
            {
                'status': True,
                'data': self.get_serializer(instance).data
            }, status=status.HTTP_200_OK
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
    
    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return Response(
            {
                'status': True,
                'message': self.delete_success_message,
            }, status=status.HTTP_200_OK
        )

