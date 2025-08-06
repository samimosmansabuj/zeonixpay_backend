from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.views import APIView
from rest_framework import serializers
from .models import CustomUser
from rest_framework.generics import CreateAPIView
from django.contrib.auth import authenticate
from rest_framework import status, permissions
from rest_framework.response import Response

# ========================Authentication Token utils Start================================
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
# ========================Authentication Token utils End================================


class CustomUserCreateAPIView(CreateAPIView):
    permission_classes = [permissions.AllowAny]
    error_message = 'Creation Unsuccessfull!'
    
    def resposne_return(self, user):
        return Response({
            'status': True,
            'message': 'Successfully Created!'
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



