# API Reference

Complete reference for Django Guitar configuration and Model-Level Security (MLS) methods.

---

## GuitarModel

Add to any Django model to enable Guitar:

```python
from guitar import GuitarModel

class MyModel(GuitarModel, models.Model):
    # ... fields ...
    
    class GuitarMeta:
        # ... configuration ...
    
    class GuitarManager:
        # ... permission methods ...
```

---

## GuitarMeta Options

### Field Exposure

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `fields` | `list` or `'__all__'` | `'__all__'` | Fields to expose in API |
| `exclude_fields` | `list` | `[]` | Fields to hide (use instead of `fields`) |
| `read_only_fields` | `list` | `[]` | Fields that can't be written |
| `writable_fields` | `list` | All non-read-only | Fields that can be written |

```python
class GuitarMeta:
    # Option A: Explicit list
    fields = ['id', 'name', 'email', 'created_at']
    
    # Option B: Everything except these
    exclude_fields = ['password_hash', 'internal_notes']
    
    # These can never be written via API
    read_only_fields = ['id', 'created_at', 'updated_at']
    
    # Only these can be written (optional, inferred from read_only_fields)
    writable_fields = ['name', 'email']
```

### Operations

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `operations` | `list` | All | Enabled operations |
| `exclude_operations` | `list` | `[]` | Disabled operations (use instead of `operations`) |

```python
class GuitarMeta:
    # Option A: Whitelist
    operations = ['list', 'retrieve', 'create', 'update', 'delete']
    
    # Option B: Blacklist (clearer when excluding few)
    exclude_operations = ['delete']  # Everything except delete
```

**Available operations:**
- `list` - GET collection (`Question.objects.all()`, `Question.objects.filter()`)
- `retrieve` - GET single (`Question.objects.get()`)
- `create` - POST (`Question.objects.create()`)
- `update` - PATCH (`Question.objects.update()`)
- `delete` - DELETE (`Question.objects.delete()`)

### Pagination

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `pagination` | `int` | `50` | Default page size |
| `max_pagination` | `int` | `1000` | Maximum page size |
| `pagination_style` | `str` | `'offset'` | `'offset'` or `'cursor'` |

### Query Methods

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `allowed_methods` | `list` | All safe methods | Methods exposed to frontend |
| `excluded_methods` | `list` | `[]` | Methods blocked from frontend |
| `custom_methods` | `list` | `[]` | Custom manager methods to expose |

```python
class GuitarMeta:
    # Only allow these query methods
    allowed_methods = ['filter', 'exclude', 'order_by', 'get', 'first', 'count']
    
    # Custom methods from your QuerySet
    custom_methods = ['active', 'for_user', 'trending']
```

### Filtering

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `filterable_fields` | `list` | All fields | Fields that can be filtered on |
| `orderable_fields` | `list` | All fields | Fields that can be ordered by |
| `searchable_fields` | `list` | `[]` | Fields included in search |

```python
class GuitarMeta:
    filterable_fields = ['user_id', 'status', 'created_at']
    orderable_fields = ['created_at', 'name', 'updated_at']
    searchable_fields = ['name', 'description']
```

### Relationships

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `expandable` | `list` | `[]` | Relations that can be expanded |
| `max_expand_depth` | `int` | `3` | Maximum nesting depth |

```python
class GuitarMeta:
    expandable = ['dashboard', 'created_by', 'dashboard.members']
    max_expand_depth = 2
```

### Computed Fields

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `annotated_fields` | `dict` | `{}` | Type hints for annotated fields |

```python
class GuitarMeta:
    annotated_fields = {
        'with_stats': {
            'view_count': 'number',
            'last_viewed': 'string | null',
        }
    }
```

---

## GuitarManager Methods

### Permission Filters

These methods filter querysets based on the current user.

| Method | When Called | Returns |
|--------|-------------|---------|
| `filter_queryset(request, qs)` | All operations | Filtered QuerySet |
| `filter_read(request, qs)` | list, retrieve | Filtered QuerySet |
| `filter_write(request, qs)` | update | Filtered QuerySet |
| `filter_delete(request, qs)` | delete | Filtered QuerySet |

**Chaining behavior** (when `chain_permissions = True`, the default):
- `filter_write` chains from `filter_read`
- `filter_delete` chains from `filter_write`

```python
class GuitarManager:
    def filter_read(self, request, queryset):
        """Users see their own questions + public questions."""
        return queryset.filter(
            Q(user=request.user) | Q(is_public=True)
        )
    
    def filter_write(self, request, queryset):
        """Users can only edit their own questions."""
        # Already filtered by filter_read, so just narrow further
        return queryset.filter(user=request.user)
```

### Data Validation

These methods validate/modify data before writes.

| Method | When Called | Returns |
|--------|-------------|---------|
| `check_create(request, data)` | Before create | Modified data dict |
| `check_write(request, instance, data)` | Before update | Modified data dict |

```python
class GuitarManager:
    def check_create(self, request, data):
        """Auto-set user on create."""
        data['user'] = request.user
        return data
    
    def check_write(self, request, instance, data):
        """Prevent changing ownership."""
        if 'user' in data and data['user'] != instance.user:
            raise PermissionDenied("Cannot transfer ownership")
        return data
```

### Composable Predicates

Reusable permission logic inspired by django-rules:

```python
from guitar import predicate

@predicate
def is_owner(request, obj):
    return obj.user == request.user

@predicate
def is_admin(request, obj):
    return request.user.is_staff

# Compose with | (or), & (and), ~ (not)
can_edit = is_owner | is_admin
can_delete = is_owner & ~is_published
```

Use in `check_*` methods:

```python
class GuitarManager:
    def check_write(self, request, instance, data):
        if not can_edit(request, instance):
            raise PermissionDenied()
        return data
```

### Lifecycle Hooks

| Method | When Called | Returns |
|--------|-------------|---------|
| `pre_create(request, data)` | Before create | Modified data |
| `post_create(request, instance)` | After create | None |
| `pre_update(request, instance, data)` | Before update | Modified data |
| `post_update(request, instance)` | After update | None |
| `pre_delete(request, instance)` | Before delete | None |
| `post_delete(request, instance)` | After delete | None |

```python
class GuitarManager:
    def post_create(self, request, instance):
        """Send notification on create."""
        notify_team(f"New question created: {instance.name}")
    
    def pre_delete(self, request, instance):
        """Archive instead of delete."""
        instance.archived = True
        instance.save()
        raise PermissionDenied("Questions are archived, not deleted")
```

### Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `chain_permissions` | `bool` | `True` | Chain filter methods |

```python
class GuitarManager:
    chain_permissions = False  # Each filter is independent
```

---

## Global Settings

```python
# settings.py
GUITAR = {
    # Base URL for all Guitar endpoints
    'BASE_URL': '/guitar/',
    
    # TypeScript output directory
    'TYPESCRIPT_OUTPUT': './frontend/src/guitar/',
    
    # Default pagination
    'DEFAULT_PAGINATION': 50,
    'MAX_PAGINATION': 1000,
    'PAGINATION_STYLE': 'offset',  # or 'cursor'
    
    # Default permission classes
    'DEFAULT_PERMISSION_CLASSES': [
        'guitar.permissions.IsAuthenticated',
    ],
}
```

---

## TypeScript Client Methods

### Query Methods (Chainable)

```typescript
// Filtering
Question.objects.all()
Question.objects.filter({ user_id: 5 })
Question.objects.filter({ name__icontains: 'sales' })
Question.objects.exclude({ archived: true })

// Ordering
Question.objects.order_by('-created_at')
Question.objects.order_by('name', '-created_at')

// Pagination
Question.objects.limit(10)
Question.objects.offset(20)
Question.objects.limit(10).offset(20)

// Field selection
Question.objects.only('id', 'name')
Question.objects.defer('large_data_field')

// Relations
Question.objects.select_related('dashboard')
Dashboard.objects.prefetch_related('questions')
```

### Terminal Methods (Return data)

```typescript
// Single objects
await Question.objects.get({ id: 1 })           // Throws if not found
await Question.objects.filter({...}).first()    // Returns null if not found
await Question.objects.filter({...}).last()

// Collections
await Question.objects.all()
await Question.objects.filter({...})

// Aggregates
await Question.objects.filter({...}).count()
await Question.objects.filter({...}).exists()
```

### Write Methods

```typescript
// Create
await Question.objects.create({ name: 'New', data: {} })

// Update
await Question.objects.filter({ id: 1 }).update({ name: 'Updated' })

// Delete
await Question.objects.filter({ id: 1 }).delete()

// Bulk
await Question.objects.bulk_create([...])
await Question.objects.filter({...}).update({...})  // Bulk update
await Question.objects.filter({...}).delete()       // Bulk delete
```

### Field Lookups

```typescript
// Comparison
{ id: 5 }                    // Exact match
{ id__gt: 5 }               // Greater than
{ id__gte: 5 }              // Greater than or equal
{ id__lt: 10 }              // Less than
{ id__lte: 10 }             // Less than or equal

// Text
{ name__contains: 'foo' }    // Contains (case-sensitive)
{ name__icontains: 'foo' }   // Contains (case-insensitive)
{ name__startswith: 'foo' }  // Starts with
{ name__endswith: 'foo' }    // Ends with

// Lists
{ id__in: [1, 2, 3] }        // In list

// Null
{ deleted_at__isnull: true } // Is null

// Dates
{ created_at__year: 2024 }
{ created_at__month: 12 }
{ created_at__gte: '2024-01-01' }

// Relations
{ dashboard__name: 'Sales' }
{ dashboard__members__id: 5 }
```

