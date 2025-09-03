from authentication.permissions import IsOwnerByUser
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from authentication.models import Merchant
from cryptography.fernet import Fernet
from rest_framework import viewsets
from rest_framework import status
import json
import base64

class DataEncryptDecrypt:
    def __init__(self, key=None):
        if key is None:
            self.key = Fernet.generate_key()  # Generate only once
            # Save the key to a secure place, e.g., a file, env variable, or database
        else:
            self.key = base64.b64decode(key).decode('utf-8')
        self.cipher_suite = Fernet(self.key)
    
    def generate_key(self):
        return Fernet.generate_key()

    def encrypt_data(self, json_data):
        json_string = json.dumps(json_data)
        encrypted_data = self.cipher_suite.encrypt(json_string.encode('utf-8'))
        encrypt_data_json = {
            "key": base64.b64encode(self.key).decode('utf-8'),
            "code": base64.b64encode(encrypted_data).decode('utf-8')
        }
        return encrypt_data_json
    
    def decrypt_data(self, encrypted_data):
        encrypted_data = base64.b64decode(encrypted_data).decode('utf-8')
        decrypted_data = self.cipher_suite.decrypt(encrypted_data)
        json_data = json.loads(decrypted_data.decode('utf-8'))
        return json_data

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

class CustomPaymentSectionViewsets(viewsets.ModelViewSet):
    permission_classes = [IsOwnerByUser]
    pagination_class = CustomPagenumberpagination
    
    model = None
    create_success_message = "Created!"
    update_success_message = "Updated!"
    delete_success_message = "Deleted!"
    delete_not_permission_message = f"Can't Delete!"
    not_found_message = "Object Not Found!"
    create_permission_denied_message = "Only Merchant user can Create!"
    ordering_by = "-id"
    
    #----------User-----------------------------------
    def get_user(self):
        return self.request.user
    
    def get_merchant(self):
        user = self.get_user()
        merchant = Merchant.objects.get(user=user) if Merchant.objects.filter(user=user).exists() else None
        if merchant:
            return merchant
        else:
            return None
    
    #-------------Object Queryset-----------------------
    def get_queryset(self):
        merchant = self.get_merchant()
        if merchant:
            return self.model.objects.filter(merchant=merchant).order_by(self.ordering_by)
        else:
            if self.get_user().role.name.lower() == 'admin':
                return self.queryset
            else:
                return None
    
    
    #-------------Created-------------------------------
    def create(self, request, *args, **kwargs):
        if not self.get_merchant():
            return Response(
                {
                    'status': False,
                    'message': self.create_permission_denied_message
                }
            )
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
        serializer.save(merchant=self.get_merchant())
    
    # =================Custom Queryset List Method Start=======================
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
        # page_size = request.query_params.get(self.pagination_class.page_size_query_param)
        
        
        # if all_items or (page_size and page_size.isdigit() and int(page_size)==0):
        if all_items:
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
    
    # =================Custom Queryset List Method Start=======================

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
        try:
            instance = self.get_object()
            return Response(
                {
                    'status': True,
                    'data': self.get_serializer(instance).data
                }, status=status.HTTP_200_OK
            )
        except NotFound as e:
            return Response(
                {
                    'status': False,
                    'message': str(e)
                }, status=status.HTTP_404_NOT_FOUND
            )
    

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
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
        except NotFound as e:
            return Response(
                {
                    'status': False,
                    'error': str(e)
                },
                status=status.HTTP_404_NOT_FOUND
            ) 
        except Exception as e:
            return Response(
                {
                    'status': False,
                    'message': str(e),
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, *args, **kwargs):
        object = self.get_object()
        message, response = self.destroy_response(object)
        if response:
            return response
        else:
            return Response(
                {
                    'status': False,
                    'message': message,
                }, status=status.HTTP_406_NOT_ACCEPTABLE
            )
    
    def destroy_response(self, object):
        if object.status.lower() == 'active':
            object.status = 'delete'
            object.save()
            return True , Response(
                {
                    'status': True,
                    'message': self.delete_success_message,
                }, status=status.HTTP_200_OK
            )
        return f"This Invoice Can't Delete!", None




def build_logo_url(request, brand_logo):
    if not brand_logo:
        return None

    url_attr = getattr(brand_logo, 'url', None)
    try:
        if url_attr:
            return request.build_absolute_uri(brand_logo.url)
    except Exception:
        pass

    from django.conf import settings
    path_str = str(brand_logo).lstrip('/')
    media_url = getattr(settings, 'MEDIA_URL', '/media/')
    return request.build_absolute_uri(f"{media_url.rstrip('/')}/{path_str}")


