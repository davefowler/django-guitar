"""
Permission classes for Guitar.
"""

from typing import Any
from django.http import HttpRequest


class BasePermission:
    """
    Base permission class. All permission classes should inherit from this.
    """
    
    def has_permission(self, request: HttpRequest) -> bool:
        """
        Return True if permission is granted, False otherwise.
        """
        return True
    
    def has_object_permission(self, request: HttpRequest, obj: Any) -> bool:
        """
        Return True if permission is granted for the specific object.
        """
        return True


class AllowAny(BasePermission):
    """
    Allow any access.
    """
    
    def has_permission(self, request: HttpRequest) -> bool:
        return True


class IsAuthenticated(BasePermission):
    """
    Allows access only to authenticated users.
    """
    
    def has_permission(self, request: HttpRequest) -> bool:
        return bool(request.user and request.user.is_authenticated)


class IsAdminUser(BasePermission):
    """
    Allows access only to admin users.
    """
    
    def has_permission(self, request: HttpRequest) -> bool:
        return bool(request.user and request.user.is_staff)


class IsAuthenticatedOrReadOnly(BasePermission):
    """
    Allow read-only access to unauthenticated users.
    """
    
    SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')
    
    def has_permission(self, request: HttpRequest) -> bool:
        if request.method in self.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)
