"""
Guitar Router - Auto-generates Django Ninja API endpoints from Guitar models.
"""

from typing import Any, Dict, List, Optional, Type, Set
import json
from django.db import models
from django.db.models import Q, QuerySet
from django.db.models.functions import Coalesce
from django.http import HttpRequest
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.conf import settings
from ninja import Router, Schema
from ninja.errors import HttpError
from pydantic import create_model
from pydantic.fields import FieldInfo

from guitar.models import GuitarModel, GuitarMeta, GuitarManager
from guitar.permissions import BasePermission, IsAuthenticated

# Try to import PostgreSQL-specific search features
try:
    from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
    POSTGRES_SEARCH_AVAILABLE = True
except ImportError:
    POSTGRES_SEARCH_AVAILABLE = False


# Field type mapping from Django to Python/Pydantic types
FIELD_TYPE_MAP = {
    models.AutoField: int,
    models.BigAutoField: int,
    models.IntegerField: int,
    models.BigIntegerField: int,
    models.SmallIntegerField: int,
    models.PositiveIntegerField: int,
    models.PositiveSmallIntegerField: int,
    models.FloatField: float,
    models.DecimalField: float,
    models.CharField: str,
    models.TextField: str,
    models.EmailField: str,
    models.URLField: str,
    models.SlugField: str,
    models.UUIDField: str,
    models.BooleanField: bool,
    models.NullBooleanField: Optional[bool],
    models.DateField: str,
    models.DateTimeField: str,
    models.TimeField: str,
    models.JSONField: dict,
    models.ForeignKey: int,  # Returns the _id
}


# Django field lookups that are supported
FIELD_LOOKUPS = [
    # Basic comparisons
    'exact', 'iexact', 'contains', 'icontains', 'startswith', 'istartswith',
    'endswith', 'iendswith', 'gt', 'gte', 'lt', 'lte', 'in', 'isnull',
    # Date/time lookups
    'year', 'month', 'day', 'week_day', 'hour', 'minute', 'second',
    'date', 'time', 'week', 'quarter', 'iso_year',
    # Other lookups
    'range', 'regex', 'iregex',
]


class GuitarRouter:
    """
    Auto-generates Django Ninja API endpoints from Guitar models.
    """
    
    def __init__(
        self,
        default_permission_classes: Optional[List[Type[BasePermission]]] = None,
        prefix: str = "",
    ) -> None:
        self.router = Router()
        self.registered_models: List[Type[models.Model]] = []
        self.default_permission_classes = default_permission_classes or [IsAuthenticated]
        self.prefix = prefix
        self._schemas: Dict[str, Type[Schema]] = {}
    
    def register(self, model_class: Type[models.Model]) -> None:
        """Register a Guitar model with the router."""
        if not issubclass(model_class, GuitarModel):
            raise ValueError(f"{model_class.__name__} must inherit from GuitarModel")
        
        self.registered_models.append(model_class)
        self._create_endpoints(model_class)
    
    def _get_field_type(self, field: models.Field) -> type:
        """Get the Python type for a Django field."""
        field_type = type(field)
        
        # Handle nullable fields
        is_nullable = getattr(field, 'null', False) or getattr(field, 'blank', False)
        
        python_type = FIELD_TYPE_MAP.get(field_type, Any)
        
        if is_nullable and python_type != Optional[bool]:
            return Optional[python_type]
        return python_type
    
    def _create_schemas(self, model_class: Type[models.Model]) -> Dict[str, Type[Schema]]:
        """Create Pydantic schemas for a model."""
        model_name = model_class.__name__
        meta = model_class._get_guitar_meta()
        
        exposed_fields = model_class._get_exposed_fields()
        writable_fields = model_class._get_writable_fields()
        read_only_fields = list(meta.read_only_fields) + ['id']
        
        # Build field definitions for read schema
        read_fields = {}
        for field_name in exposed_fields:
            # Check if it's a FK _id field
            if field_name.endswith('_id'):
                base_name = field_name[:-3]
                try:
                    field = model_class._meta.get_field(base_name)
                    if isinstance(field, models.ForeignKey):
                        read_fields[field_name] = (Optional[int], None)
                        continue
                except:
                    pass
            
            try:
                field = model_class._meta.get_field(field_name)
                field_type = self._get_field_type(field)
                
                # Make read-only fields have default None
                if field_name in read_only_fields:
                    read_fields[field_name] = (Optional[field_type], None)
                else:
                    is_nullable = getattr(field, 'null', False) or getattr(field, 'blank', False)
                    if is_nullable:
                        read_fields[field_name] = (Optional[field_type], None)
                    else:
                        read_fields[field_name] = (field_type, ...)
            except:
                # Might be a property or computed field
                read_fields[field_name] = (Optional[Any], None)
        
        # Create read schema
        ReadSchema = create_model(
            f'{model_name}Read',
            **read_fields
        )
        
        # Build field definitions for create schema
        create_fields = {}
        for field_name in writable_fields:
            if field_name in read_only_fields:
                continue
            
            # Check if it's a FK _id field
            if field_name.endswith('_id'):
                base_name = field_name[:-3]
                try:
                    field = model_class._meta.get_field(base_name)
                    if isinstance(field, models.ForeignKey):
                        is_nullable = getattr(field, 'null', False)
                        if is_nullable:
                            create_fields[field_name] = (Optional[int], None)
                        else:
                            create_fields[field_name] = (int, ...)
                        continue
                except:
                    pass
            
            try:
                field = model_class._meta.get_field(field_name)
                field_type = self._get_field_type(field)
                
                is_nullable = getattr(field, 'null', False) or getattr(field, 'blank', False)
                has_default = field.has_default() or getattr(field, 'auto_now', False) or getattr(field, 'auto_now_add', False)
                
                if is_nullable or has_default:
                    create_fields[field_name] = (Optional[field_type], None)
                else:
                    create_fields[field_name] = (field_type, ...)
            except:
                create_fields[field_name] = (Optional[Any], None)
        
        CreateSchema = create_model(
            f'{model_name}Create',
            **create_fields
        )
        
        # Build field definitions for update schema (all optional)
        update_fields = {}
        for field_name in writable_fields:
            if field_name in read_only_fields:
                continue
            
            if field_name.endswith('_id'):
                update_fields[field_name] = (Optional[int], None)
                continue
            
            try:
                field = model_class._meta.get_field(field_name)
                field_type = self._get_field_type(field)
                update_fields[field_name] = (Optional[field_type], None)
            except:
                update_fields[field_name] = (Optional[Any], None)
        
        UpdateSchema = create_model(
            f'{model_name}Update',
            **update_fields
        )
        
        # Filter schema for query params
        filter_fields = {}
        filterable = meta.filterable_fields or exposed_fields
        
        for field_name in filterable:
            # Add base field
            filter_fields[field_name] = (Optional[Any], None)
            
            # Add lookup variants
            for lookup in FIELD_LOOKUPS:
                filter_fields[f"{field_name}__{lookup}"] = (Optional[Any], None)
        
        # Add ordering and pagination
        filter_fields['_order'] = (Optional[str], None)
        filter_fields['_limit'] = (Optional[int], None)
        filter_fields['_offset'] = (Optional[int], None)
        filter_fields['_only'] = (Optional[str], None)
        filter_fields['_defer'] = (Optional[str], None)
        filter_fields['_expand'] = (Optional[str], None)
        filter_fields['_exclude'] = (Optional[str], None)  # Comma-separated field names to exclude
        filter_fields['_search'] = (Optional[str], None)  # Search query string
        
        FilterSchema = create_model(
            f'{model_name}Filter',
            **filter_fields
        )
        
        return {
            'read': ReadSchema,
            'create': CreateSchema,
            'update': UpdateSchema,
            'filter': FilterSchema,
        }
    
    def _check_permissions(
        self,
        request: HttpRequest,
        model_class: Type[models.Model],
        permission_classes: Optional[List[Type[BasePermission]]] = None,
    ) -> None:
        """Check if the request has permission."""
        if permission_classes is None:
            permission_classes = self.default_permission_classes
        
        for permission_class in permission_classes:
            permission = permission_class()
            if not permission.has_permission(request):
                raise HttpError(403, "Permission denied")
    
    def _parse_filter_params(
        self,
        query_params: Dict[str, Any],
        model_class: Type[models.Model],
        exclude_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        Parse query parameters into Django filter kwargs.
        
        Args:
            query_params: Query parameters dict
            model_class: The model class
            exclude_mode: If True, parse for exclude() instead of filter()
        """
        meta = model_class._get_guitar_meta()
        filterable = set(meta.filterable_fields) if meta.filterable_fields else None
        exposed = set(model_class._get_exposed_fields())
        
        filters = {}
        
        for key, value in query_params.items():
            if value is None:
                continue
            
            # Skip special params
            if key.startswith('_'):
                continue
            
            # Parse the field name and lookup
            parts = key.split('__')
            field_name = parts[0]
            
            # Check if field is filterable
            if filterable and field_name not in filterable:
                continue
            if field_name not in exposed and not field_name.endswith('_id'):
                continue
            
            # Handle __in lookup (comma-separated values)
            if len(parts) > 1 and parts[-1] == 'in':
                if isinstance(value, str):
                    value = [v.strip() for v in value.split(',')]
            
            filters[key] = value
        
        return filters
    
    def _apply_ordering(
        self,
        queryset: QuerySet,
        order_param: Optional[str],
        model_class: Type[models.Model],
    ) -> QuerySet:
        """Apply ordering to queryset."""
        if not order_param:
            return queryset
        
        meta = model_class._get_guitar_meta()
        orderable = set(meta.orderable_fields) if meta.orderable_fields else None
        
        order_fields = [f.strip() for f in order_param.split(',')]
        valid_fields = []
        
        for field in order_fields:
            field_name = field.lstrip('-')
            
            if orderable and field_name not in orderable:
                continue
            
            valid_fields.append(field)
        
        if valid_fields:
            queryset = queryset.order_by(*valid_fields)
        
        return queryset
    
    def _apply_pagination(
        self,
        queryset: QuerySet,
        limit: Optional[int],
        offset: Optional[int],
        model_class: Type[models.Model],
    ) -> QuerySet:
        """Apply pagination to queryset."""
        meta = model_class._get_guitar_meta()
        
        if limit is None:
            limit = meta.pagination
        else:
            limit = min(limit, meta.max_pagination)
        
        if offset is None:
            offset = 0
        
        return queryset[offset:offset + limit]
    
    def _parse_expand(
        self,
        expand_param: Optional[str],
        model_class: Type[models.Model],
    ) -> tuple[List[str], List[str]]:
        """
        Parse _expand parameter into select_related and prefetch_related lists.
        Returns (select_related_fields, prefetch_related_fields).
        """
        if not expand_param:
            return [], []
        
        meta = model_class._get_guitar_meta()
        expandable = set(meta.expandable) if meta.expandable else None
        
        # Split comma-separated list
        expand_fields = [f.strip() for f in expand_param.split(',')]
        
        select_fields = []
        prefetch_fields = []
        
        for field_path in expand_fields:
            # Check if field is expandable (if expandable list is configured)
            if expandable and field_path not in expandable:
                # Check if any prefix matches (for nested expansions)
                if not any(field_path.startswith(f + '.') for f in expandable):
                    continue
            
            # Split nested paths (e.g., "dashboard.owner")
            parts = field_path.split('.')
            first_field = parts[0]
            
            # Check if it's a ForeignKey (select_related) or reverse/M2M (prefetch_related)
            try:
                field = model_class._meta.get_field(first_field)
                
                if isinstance(field, models.ForeignKey):
                    # ForeignKey uses select_related
                    select_fields.append(field_path)
                elif isinstance(field, models.ManyToManyField):
                    # M2M uses prefetch_related
                    prefetch_fields.append(field_path)
                else:
                    # Default to select_related for unknown (will be validated when applied)
                    select_fields.append(field_path)
            except models.FieldDoesNotExist:
                # Might be a reverse relation (no field, but has related_name)
                # Try to find it via related_objects
                found = False
                for rel in model_class._meta.related_objects:
                    if rel.get_accessor_name() == first_field:
                        prefetch_fields.append(field_path)
                        found = True
                        break
                
                if not found:
                    # Unknown field, skip it
                    continue
        
        return select_fields, prefetch_fields
    
    def _apply_expand(
        self,
        queryset: QuerySet,
        expand_param: Optional[str],
        model_class: Type[models.Model],
    ) -> QuerySet:
        """Apply select_related and prefetch_related to queryset."""
        select_fields, prefetch_fields = self._parse_expand(expand_param, model_class)
        
        if select_fields:
            queryset = queryset.select_related(*select_fields)
        
        if prefetch_fields:
            queryset = queryset.prefetch_related(*prefetch_fields)
        
        return queryset
    
    def _apply_search(
        self,
        queryset: QuerySet,
        search_query: Optional[str],
        model_class: Type[models.Model],
    ) -> QuerySet:
        """
        Apply full-text search to queryset.
        Uses PostgreSQL SearchVector if available, otherwise falls back to icontains.
        """
        if not search_query:
            return queryset
        
        meta = model_class._get_guitar_meta()
        searchable_fields = meta.searchable_fields
        
        if not searchable_fields:
            # If no searchable_fields configured, search all text fields
            searchable_fields = [
                f.name for f in model_class._meta.get_fields()
                if isinstance(f, (models.CharField, models.TextField))
            ]
        
        if not searchable_fields:
            return queryset
        
        # Check database backend
        db_backend = settings.DATABASES['default']['ENGINE']
        
        # PostgreSQL full-text search
        if POSTGRES_SEARCH_AVAILABLE and 'postgresql' in db_backend:
            try:
                # Build SearchVector from searchable fields
                search_vector = SearchVector(*searchable_fields)
                search_query_obj = SearchQuery(search_query)
                
                # Annotate with search rank
                queryset = queryset.annotate(
                    search=search_vector,
                    rank=SearchRank(search_vector, search_query_obj)
                ).filter(search=search_query_obj).order_by('-rank')
                
                return queryset
            except Exception:
                # Fall back to icontains if search fails
                pass
        
        # Fallback: use icontains across multiple fields
        search_conditions = Q()
        for field_name in searchable_fields:
            try:
                # Verify field exists
                model_class._meta.get_field(field_name)
                search_conditions |= Q(**{f"{field_name}__icontains": search_query})
            except models.FieldDoesNotExist:
                continue
        
        if search_conditions:
            queryset = queryset.filter(search_conditions)
        
        return queryset
    
    def _serialize_instance(
        self,
        instance: models.Model,
        model_class: Type[models.Model],
        only_fields: Optional[List[str]] = None,
        defer_fields: Optional[List[str]] = None,
        expand_fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Serialize a model instance to a dictionary.
        
        Args:
            instance: The model instance to serialize
            model_class: The model class
            only_fields: Fields to include (None = all exposed fields)
            defer_fields: Fields to exclude
            expand_fields: Related fields to expand (e.g., ['dashboard', 'dashboard.owner'])
        """
        exposed = model_class._get_exposed_fields()
        
        if only_fields:
            fields = [f for f in only_fields if f in exposed]
        else:
            fields = exposed
        
        if defer_fields:
            fields = [f for f in fields if f not in defer_fields]
        
        # Build set of expanded field names (first part of paths)
        expanded_field_names = set()
        if expand_fields:
            for path in expand_fields:
                first_field = path.split('.')[0]
                expanded_field_names.add(first_field)
        
        data = {}
        for field_name in fields:
            # Handle FK _id fields
            if field_name.endswith('_id'):
                base_name = field_name[:-3]
                try:
                    fk_field = model_class._meta.get_field(base_name)
                    if isinstance(fk_field, models.ForeignKey):
                        data[field_name] = getattr(instance, field_name, None)
                        
                        # If this FK is expanded, include the full object
                        if base_name in expanded_field_names:
                            related_obj = getattr(instance, base_name, None)
                            if related_obj:
                                # Find nested expansion paths for this field
                                nested_paths = [
                                    '.'.join(p.split('.')[1:])
                                    for p in expand_fields or []
                                    if p.startswith(base_name + '.')
                                ]
                                nested_paths = [p for p in nested_paths if p]  # Remove empty
                                
                                # Check if related model is a GuitarModel
                                related_model = fk_field.related_model
                                if issubclass(related_model, GuitarModel):
                                    data[base_name] = self._serialize_instance(
                                        related_obj,
                                        related_model,
                                        expand_fields=nested_paths if nested_paths else None,
                                    )
                                else:
                                    # Not a GuitarModel, serialize basic fields
                                    data[base_name] = {
                                        'id': getattr(related_obj, 'id', None),
                                        'pk': getattr(related_obj, 'pk', None),
                                    }
                        continue
                except:
                    pass
            
            # Get the value
            value = getattr(instance, field_name, None)
            
            # Handle expanded reverse relations (prefetch_related)
            if field_name in expanded_field_names:
                try:
                    # Check if it's a reverse relation
                    field = model_class._meta.get_field(field_name)
                    if isinstance(field, (models.ManyToManyField, models.ForeignKey)):
                        # Already handled above
                        pass
                except models.FieldDoesNotExist:
                    # Might be a reverse relation
                    related_obj = getattr(instance, field_name, None)
                    if related_obj is not None:
                        # Check if it's a manager (M2M or reverse FK)
                        if hasattr(related_obj, 'all'):
                            # It's a related manager
                            related_objs = list(related_obj.all())
                            related_model = related_obj.model
                            
                            # Find nested expansion paths
                            nested_paths = [
                                '.'.join(p.split('.')[1:])
                                for p in expand_fields or []
                                if p.startswith(field_name + '.')
                            ]
                            nested_paths = [p for p in nested_paths if p]
                            
                            if issubclass(related_model, GuitarModel):
                                data[field_name] = [
                                    self._serialize_instance(
                                        obj,
                                        related_model,
                                        expand_fields=nested_paths if nested_paths else None,
                                    )
                                    for obj in related_objs
                                ]
                            else:
                                # Not a GuitarModel, serialize basic fields
                                data[field_name] = [
                                    {'id': getattr(obj, 'id', None), 'pk': getattr(obj, 'pk', None)}
                                    for obj in related_objs
                                ]
                            continue
            
            # Handle special types
            if hasattr(value, 'isoformat'):
                value = value.isoformat()
            
            data[field_name] = value
        
        return data
    
    def _create_endpoints(self, model_class: Type[models.Model]) -> None:
        """Create all CRUD endpoints for a model."""
        meta = model_class._get_guitar_meta()
        operations = model_class._get_operations()
        endpoint_name = model_class._get_endpoint_name()
        schemas = self._create_schemas(model_class)
        
        # Store schemas for TypeScript generation
        self._schemas[model_class.__name__] = schemas
        
        # Helper to get manager
        def get_manager() -> GuitarManager:
            return model_class._get_guitar_manager()
        
        # LIST endpoint
        if 'list' in operations:
            @self.router.get(f"/{endpoint_name}/", response=List[schemas['read']])
            def list_items(request: HttpRequest) -> List[Dict[str, Any]]:
                self._check_permissions(request, model_class)
                
                # Get query parameters from request
                query_params = {k: v for k, v in request.GET.items()}
                
                manager = get_manager()
                queryset = model_class.objects.all()
                
                # Apply permission filter
                queryset = manager.filter_read(request, queryset)
                
                # Apply query filters
                filters = self._parse_filter_params(query_params, model_class)
                if filters:
                    queryset = queryset.filter(**filters)
                
                # Apply exclude filters (if _exclude param is present)
                exclude_param = query_params.get('_exclude')
                if exclude_param:
                    # Parse exclude fields (comma-separated)
                    exclude_fields = [f.strip() for f in exclude_param.split(',')]
                    # Parse each exclude field as a filter
                    for exclude_field in exclude_fields:
                        # Support field=value format or just field name
                        if '=' in exclude_field:
                            field_name, field_value = exclude_field.split('=', 1)
                            exclude_filters = self._parse_filter_params({field_name: field_value}, model_class)
                            if exclude_filters:
                                queryset = queryset.exclude(**exclude_filters)
                        else:
                            # Just exclude if field is truthy
                            exclude_filters = self._parse_filter_params({exclude_field: True}, model_class)
                            if exclude_filters:
                                queryset = queryset.exclude(**exclude_filters)
                
                # Apply ordering
                queryset = self._apply_ordering(
                    queryset,
                    query_params.get('_order'),
                    model_class,
                )
                
                # Apply relationship expansion (before pagination for efficiency)
                expand_param = query_params.get('_expand')
                queryset = self._apply_expand(queryset, expand_param, model_class)
                
                # Apply pagination
                limit_val = query_params.get('_limit')
                offset_val = query_params.get('_offset')
                queryset = self._apply_pagination(
                    queryset,
                    int(limit_val) if limit_val else None,
                    int(offset_val) if offset_val else None,
                    model_class,
                )
                
                # Parse field selection
                only_fields = None
                defer_fields = None
                if query_params.get('_only'):
                    only_fields = [f.strip() for f in query_params['_only'].split(',')]
                if query_params.get('_defer'):
                    defer_fields = [f.strip() for f in query_params['_defer'].split(',')]
                
                # Parse expand fields for serialization
                expand_fields = None
                if expand_param:
                    expand_fields = [f.strip() for f in expand_param.split(',')]
                
                # Serialize
                return [
                    self._serialize_instance(obj, model_class, only_fields, defer_fields, expand_fields)
                    for obj in queryset
                ]
            
            # Update function name for uniqueness
            list_items.__name__ = f"list_{endpoint_name}"
        
        # COUNT endpoint
        if 'list' in operations:  # Count uses same permissions as list
            @self.router.get(f"/{endpoint_name}/_count/", response=int)
            def count_items(request: HttpRequest) -> int:
                self._check_permissions(request, model_class)
                
                # Get query parameters from request
                query_params = {k: v for k, v in request.GET.items()}
                
                manager = get_manager()
                queryset = model_class.objects.all()
                
                # Apply permission filter
                queryset = manager.filter_read(request, queryset)
                
                # Apply query filters
                filters = self._parse_filter_params(query_params, model_class)
                if filters:
                    queryset = queryset.filter(**filters)
                
                # Apply search
                search_query = query_params.get('_search')
                queryset = self._apply_search(queryset, search_query, model_class)
                
                # Apply exclude filters
                exclude_param = query_params.get('_exclude')
                if exclude_param:
                    exclude_fields = [f.strip() for f in exclude_param.split(',')]
                    for exclude_field in exclude_fields:
                        if '=' in exclude_field:
                            field_name, field_value = exclude_field.split('=', 1)
                            exclude_filters = self._parse_filter_params({field_name: field_value}, model_class)
                            if exclude_filters:
                                queryset = queryset.exclude(**exclude_filters)
                        else:
                            exclude_filters = self._parse_filter_params({exclude_field: True}, model_class)
                            if exclude_filters:
                                queryset = queryset.exclude(**exclude_filters)
                
                return queryset.count()
            
            count_items.__name__ = f"count_{endpoint_name}"
        
        # RETRIEVE endpoint
        if 'retrieve' in operations:
            @self.router.get(f"/{endpoint_name}/{{id}}/", response=schemas['read'])
            def retrieve_item(request: HttpRequest, id: int) -> Dict[str, Any]:
                self._check_permissions(request, model_class)
                
                # Get query parameters from request
                query_params = {k: v for k, v in request.GET.items()}
                
                manager = get_manager()
                queryset = model_class.objects.all()
                
                # Apply permission filter
                queryset = manager.filter_read(request, queryset)
                
                # Apply relationship expansion
                expand_param = query_params.get('_expand')
                queryset = self._apply_expand(queryset, expand_param, model_class)
                
                try:
                    instance = queryset.get(pk=id)
                except model_class.DoesNotExist:
                    raise HttpError(404, "Not found")
                
                # Parse expand fields for serialization
                expand_fields = None
                if expand_param:
                    expand_fields = [f.strip() for f in expand_param.split(',')]
                
                return self._serialize_instance(instance, model_class, expand_fields=expand_fields)
            
            retrieve_item.__name__ = f"retrieve_{endpoint_name}"
        
        # CREATE endpoint
        if 'create' in operations:
            @self.router.post(f"/{endpoint_name}/", response=schemas['read'])
            def create_item(request: HttpRequest, data: schemas['create']) -> Dict[str, Any]:
                self._check_permissions(request, model_class)
                
                manager = get_manager()
                
                # Convert to dict
                create_data = data.model_dump(exclude_unset=True)
                
                # Run permission check
                try:
                    create_data = manager.check_create(request, create_data)
                except PermissionDenied as e:
                    raise HttpError(403, str(e))
                
                # Pre-create hook
                create_data = manager.pre_create(request, create_data)
                
                # Create instance
                try:
                    instance = model_class.objects.create(**create_data)
                except Exception as e:
                    raise HttpError(400, str(e))
                
                # Post-create hook
                manager.post_create(request, instance)
                
                return self._serialize_instance(instance, model_class)
            
            create_item.__name__ = f"create_{endpoint_name}"
        
        # UPDATE endpoint
        if 'update' in operations:
            @self.router.patch(f"/{endpoint_name}/{{id}}/", response=schemas['read'])
            def update_item(request: HttpRequest, id: int, data: schemas['update']) -> Dict[str, Any]:
                self._check_permissions(request, model_class)
                
                manager = get_manager()
                queryset = model_class.objects.all()
                
                # Apply permission filter
                queryset = manager.filter_write(request, queryset)
                
                try:
                    instance = queryset.get(pk=id)
                except model_class.DoesNotExist:
                    raise HttpError(404, "Not found")
                
                # Convert to dict
                update_data = data.model_dump(exclude_unset=True)
                
                # Run permission check
                try:
                    update_data = manager.check_write(request, instance, update_data)
                except PermissionDenied as e:
                    raise HttpError(403, str(e))
                
                # Pre-update hook
                update_data = manager.pre_update(request, instance, update_data)
                
                # Update instance
                for field, value in update_data.items():
                    setattr(instance, field, value)
                
                try:
                    instance.save()
                except Exception as e:
                    raise HttpError(400, str(e))
                
                # Post-update hook
                manager.post_update(request, instance)
                
                return self._serialize_instance(instance, model_class)
            
            update_item.__name__ = f"update_{endpoint_name}"
        
        # DELETE endpoint
        if 'delete' in operations:
            @self.router.delete(f"/{endpoint_name}/{{id}}/")
            def delete_item(request: HttpRequest, id: int) -> Dict[str, str]:
                self._check_permissions(request, model_class)
                
                manager = get_manager()
                queryset = model_class.objects.all()
                
                # Apply permission filter
                queryset = manager.filter_delete(request, queryset)
                
                try:
                    instance = queryset.get(pk=id)
                except model_class.DoesNotExist:
                    raise HttpError(404, "Not found")
                
                # Pre-delete hook
                try:
                    manager.pre_delete(request, instance)
                except PermissionDenied as e:
                    raise HttpError(403, str(e))
                
                # Store instance for post-delete hook
                instance_copy = instance
                
                # Delete
                instance.delete()
                
                # Post-delete hook
                manager.post_delete(request, instance_copy)
                
                return {"detail": "Deleted"}
            
            delete_item.__name__ = f"delete_{endpoint_name}"
        
        # BULK UPDATE endpoint
        if 'update' in operations:
            @self.router.patch(f"/{endpoint_name}/_bulk/", response=List[schemas['read']])
            def bulk_update_items(request: HttpRequest, data: schemas['update']) -> List[Dict[str, Any]]:
                self._check_permissions(request, model_class)
                
                # Get query parameters from request
                query_params = {k: v for k, v in request.GET.items()}
                
                manager = get_manager()
                queryset = model_class.objects.all()
                
                # Apply permission filter
                queryset = manager.filter_write(request, queryset)
                
                # Apply query filters
                filters = self._parse_filter_params(query_params, model_class)
                if filters:
                    queryset = queryset.filter(**filters)
                
                # Apply exclude filters
                exclude_param = query_params.get('_exclude')
                if exclude_param:
                    exclude_fields = [f.strip() for f in exclude_param.split(',')]
                    for exclude_field in exclude_fields:
                        if '=' in exclude_field:
                            field_name, field_value = exclude_field.split('=', 1)
                            exclude_filters = self._parse_filter_params({field_name: field_value}, model_class)
                            if exclude_filters:
                                queryset = queryset.exclude(**exclude_filters)
                        else:
                            exclude_filters = self._parse_filter_params({exclude_field: True}, model_class)
                            if exclude_filters:
                                queryset = queryset.exclude(**exclude_filters)
                
                # Convert update data to dict
                update_data = data.model_dump(exclude_unset=True)
                
                # Get all instances to update
                instances = list(queryset)
                
                if not instances:
                    return []
                
                # Apply updates to each instance
                # Note: We could use Django's bulk_update() here, but we validate each one
                # to ensure check_write() passes (though queryset filtering handles security)
                updated_instances = []
                for instance in instances:
                    # Run permission check (though queryset already filtered)
                    try:
                        instance_update_data = manager.check_write(request, instance, update_data.copy())
                    except PermissionDenied:
                        continue  # Skip this instance
                    
                    # Apply updates
                    for field, value in instance_update_data.items():
                        setattr(instance, field, value)
                    
                    updated_instances.append(instance)
                
                # Use Django's bulk_update for efficiency
                # Note: This bypasses save() and signals, but that's Django's behavior
                model_class.objects.bulk_update(updated_instances, list(update_data.keys()))
                
                # Serialize and return
                return [
                    self._serialize_instance(instance, model_class)
                    for instance in updated_instances
                ]
            
            bulk_update_items.__name__ = f"bulk_update_{endpoint_name}"
        
        # BULK CREATE endpoint
        if 'create' in operations:
            @self.router.post(f"/{endpoint_name}/_bulk/", response=List[schemas['read']])
            def bulk_create_items(request: HttpRequest, data: List[schemas['create']]) -> List[Dict[str, Any]]:
                self._check_permissions(request, model_class)
                
                manager = get_manager()
                
                # Validate and prepare each item
                instances_to_create = []
                for item_data in data:
                    create_data = item_data.model_dump(exclude_unset=True)
                    
                    # Run permission check
                    try:
                        create_data = manager.check_create(request, create_data)
                    except PermissionDenied:
                        continue  # Skip this item
                    
                    # Pre-create hook
                    create_data = manager.pre_create(request, create_data)
                    
                    # Create instance (don't save yet)
                    instance = model_class(**create_data)
                    instances_to_create.append(instance)
                
                if not instances_to_create:
                    return []
                
                # Use Django's bulk_create for efficiency
                # Note: This bypasses save() and signals, so post_create hooks won't run
                created_instances = model_class.objects.bulk_create(instances_to_create)
                
                # Note: post_create hooks are skipped (Django's bulk_create behavior)
                # If you need post_create hooks, use individual create() calls
                
                # Serialize and return
                return [
                    self._serialize_instance(instance, model_class)
                    for instance in created_instances
                ]
            
            bulk_create_items.__name__ = f"bulk_create_{endpoint_name}"
    
    def get_registered_models(self) -> List[Type[models.Model]]:
        """Get all registered models."""
        return self.registered_models
    
    @property
    def urls(self):
        """Get the URL patterns for this router."""
        return self.router


# Default guitar router instance
guitar_router = GuitarRouter()
