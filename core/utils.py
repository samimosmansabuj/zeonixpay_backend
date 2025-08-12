from rest_framework import viewsets
from authentication.permissions import IsOwnerByUser
from authentication.models import CustomUser
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.response import Response
from rest_framework import status
from cryptography.fernet import Fernet
import uuid
import json
import base64

class DataEncryptDecrypt:
    def __init__(self):
        self.key = self.generate_key()
        self.cipher_suite = Fernet(self.key)
    
    def generate_key(self):
        return Fernet.generate_key()

    def encrypt_data(self, json_data):
        json_string = json.dumps(json_data)
        encrypted_data = self.cipher_suite.encrypt(json_string.encode('utf-8'))
        return encrypted_data
    
    def decrypt_data(self, encrypted_data):
        decrypted_data = self.cipher_suite.decrypt(encrypted_data)
        json_data = json.loads(decrypted_data.decode('utf-8'))
        return json_data


class CustomPaymentSectionViewsets(viewsets.ModelViewSet):
    permission_classes = [IsOwnerByUser]
    pagination_class = None
    
    model = None
    create_success_message = "Created!"
    update_success_message = "Updated!"
    delete_success_message = "Deleted!"
    not_found_message = "Object Not Found!"
    ordering_by = "-id"
    
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
            return self.model.objects.filter(user=user).order_by(self.ordering_by)
        return self.model.objects.none()
    
    
    
    #-------------Created-------------------------------
    def json_encrypted(self, post_data):
        url_json = {
            "success_url": post_data.get("success_url"),
            "cancel_url": post_data.get("cancel_url"),
            "failed_url": post_data.get("failed_url"),
        }
        object = DataEncryptDecrypt()
        encrypted_data = object.encrypt_data(url_json)
        post_data['data'] = encrypted_data
        return post_data
    
    def create(self, request, *args, **kwargs):
        try:
            post_data = request.data.copy()
            data = self.json_encrypted(post_data)
            serializer = self.get_serializer(data=data)
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



