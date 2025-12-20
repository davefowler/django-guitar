"""
GuitarModel mixin and related classes for Model-Level Security (MLS).
"""

from typing import Any, Dict, List, Optional, Set, Type
from django.db import models
from django.http import HttpRequest
from django.db.models import QuerySet
from django.core.exceptions import PermissionDenied


class GuitarMeta:
    """
    Configuration class for Guitar models.
    Define this as an inner class on your model.
    """
    # Field exposure
    fields: List[str] = '__all__'
    exclude_fields: List[str] = []
    read_only_fields: List[str] = []
    writable_fields: Optional[List[str]] = None
    
    # Operations
    operations: List[str] = ['list', 'retrieve', 'create', 'update', 'delete']
    exclude_operations: List[str] = []
    
    # Pagination
    pagination: int = 50
    max_pagination: int = 1000
    pagination_style: str = 'offset'  # or 'cursor'
    
    # Query methods
    allowed_methods: Optional[List[str]] = None
    excluded_methods: List[str] = []
    custom_methods: List[str] = []
    
    # Filtering
    filterable_fields: Optional[List[str]] = None
    orderable_fields: Optional[List[str]] = None
    searchable_fields: List[str] = []
    
    # Relationships
    expandable: List[str] = []
    max_expand_depth: int = 3
    
    # Computed fields
    annotated_fields: Dict[str, Dict[str, str]] = {}
    
    # Endpoint
    endpoint_name: Optional[str] = None


class GuitarManager:
    """
    Permission manager for Guitar models.
    Define this as an inner class on your model to control access.
    """
    chain_permissions: bool = True
    
    def filter_queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        """Base filter for ALL operations. Override for tenant isolation, etc."""
        return queryset
    
    def filter_read(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        """Filter for read operations (list, retrieve)."""
        return self.filter_queryset(request, queryset)
    
    def filter_write(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        """Filter for write operations (update)."""
        if self.chain_permissions:
            return self.filter_read(request, queryset)
        return self.filter_queryset(request, queryset)
    
    def filter_delete(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        """Filter for delete operations."""
        if self.chain_permissions:
            return self.filter_write(request, queryset)
        return self.filter_queryset(request, queryset)
    
    def check_create(self, request: HttpRequest, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate/modify data before create. Return modified data or raise PermissionDenied."""
        return data
    
    def check_write(self, request: HttpRequest, instance: Any, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate/modify data before update. Return modified data or raise PermissionDenied."""
        return data
    
    # Lifecycle hooks
    def pre_create(self, request: HttpRequest, data: Dict[str, Any]) -> Dict[str, Any]:
        """Called before create. Return modified data."""
        return data
    
    def post_create(self, request: HttpRequest, instance: Any) -> None:
        """Called after create."""
        pass
    
    def pre_update(self, request: HttpRequest, instance: Any, data: Dict[str, Any]) -> Dict[str, Any]:
        """Called before update. Return modified data."""
        return data
    
    def post_update(self, request: HttpRequest, instance: Any) -> None:
        """Called after update."""
        pass
    
    def pre_delete(self, request: HttpRequest, instance: Any) -> None:
        """Called before delete."""
        pass
    
    def post_delete(self, request: HttpRequest, instance: Any) -> None:
        """Called after delete."""
        pass


class GuitarModelMixin:
    """
    Mixin that marks a Django model for Guitar API generation.
    """
    
    @classmethod
    def _get_guitar_meta(cls) -> GuitarMeta:
        """Get the GuitarMeta configuration for this model."""
        meta_class = getattr(cls, 'GuitarMeta', None)
        if meta_class is None:
            return GuitarMeta()
        
        # Create instance with defaults
        meta = GuitarMeta()
        for attr in dir(meta_class):
            if not attr.startswith('_'):
                setattr(meta, attr, getattr(meta_class, attr))
        return meta
    
    @classmethod
    def _get_guitar_manager(cls) -> GuitarManager:
        """Get the GuitarManager for this model."""
        manager_class = getattr(cls, 'GuitarManager', None)
        if manager_class is None:
            return GuitarManager()
        
        # Create instance and copy methods
        manager = GuitarManager()
        for attr in dir(manager_class):
            if not attr.startswith('_') and callable(getattr(manager_class, attr)):
                # Bind the method properly
                method = getattr(manager_class, attr)
                if callable(method):
                    setattr(manager, attr, method.__get__(manager, GuitarManager))
        
        # Copy non-method attributes
        if hasattr(manager_class, 'chain_permissions'):
            manager.chain_permissions = manager_class.chain_permissions
        
        return manager
    
    @classmethod
    def _get_exposed_fields(cls) -> List[str]:
        """Get the list of fields exposed in the API."""
        meta = cls._get_guitar_meta()
        
        if meta.fields == '__all__':
            # Get all model fields
            model_fields = [f.name for f in cls._meta.get_fields() 
                          if hasattr(f, 'name') and not f.many_to_many and not f.one_to_many]
            # Add foreign key _id fields
            for field in cls._meta.get_fields():
                if isinstance(field, models.ForeignKey):
                    model_fields.append(f"{field.name}_id")
        else:
            model_fields = list(meta.fields)
        
        # Remove excluded fields
        if meta.exclude_fields:
            model_fields = [f for f in model_fields if f not in meta.exclude_fields]
        
        return model_fields
    
    @classmethod
    def _get_writable_fields(cls) -> List[str]:
        """Get the list of fields that can be written."""
        meta = cls._get_guitar_meta()
        
        if meta.writable_fields is not None:
            return list(meta.writable_fields)
        
        # All exposed fields except read-only ones
        exposed = cls._get_exposed_fields()
        read_only = list(meta.read_only_fields) + ['id']
        
        return [f for f in exposed if f not in read_only]
    
    @classmethod
    def _get_operations(cls) -> Set[str]:
        """Get the enabled operations for this model."""
        meta = cls._get_guitar_meta()
        
        all_ops = {'list', 'retrieve', 'create', 'update', 'delete'}
        
        if meta.operations:
            enabled = set(meta.operations)
        else:
            enabled = all_ops
        
        if meta.exclude_operations:
            enabled -= set(meta.exclude_operations)
        
        return enabled
    
    @classmethod
    def _get_endpoint_name(cls) -> str:
        """Get the API endpoint name for this model."""
        meta = cls._get_guitar_meta()
        if meta.endpoint_name:
            return meta.endpoint_name
        return cls._meta.model_name


# The actual mixin to use
class GuitarModel(GuitarModelMixin):
    """
    Add this mixin to your Django model to enable Guitar API generation.
    
    Example:
        class Chart(GuitarModel, models.Model):
            name = models.CharField(max_length=255)
            
            class GuitarMeta:
                fields = ['id', 'name']
            
            class GuitarManager:
                def filter_read(self, request, queryset):
                    return queryset.filter(user=request.user)
    """
    
    class Meta:
        abstract = True
