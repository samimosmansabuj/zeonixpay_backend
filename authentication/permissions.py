from rest_framework.permissions import BasePermission, SAFE_METHODS


class AdminCreatePermission(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        else:
            user = request.user
            return user.is_authenticated and user.role.name in ['Admin']

class AdminAllPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated and user.role.name in ['Admin', 'Staff']


class IsOwnerByUser(BasePermission):
    def has_permission(self, request, view):
        pid = view.kwargs.get('pid')
        return request.user.is_authenticated and str(request.user.pid) == str(pid)

class MerchantCreatePermission(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return user.is_authenticated and user.role.name == 'Merchant'

class StaffUpdatePermission(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return user.is_authenticated and user.role.name in ['Staff', 'Admin']

class AdminUpdatePermission(BasePermission):
    def has_permission(self, request, view):
        if request.method in ["PATCH", "PUT"] and request.user.role.name in ["Admin", "Merchant"]:
            return True
        # return request.user.role.name == 'Merchant' and request.method in SAFE_METHODS
        return False


