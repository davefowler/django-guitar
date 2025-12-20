# Django Guitar 🎸

> Automatically generate a Django-like ORM for the frontend from your Django models.

## Vision

Django Guitar bridges the gap between Django's powerful ORM and frontend development by automatically generating TypeScript clients that mirror Django's query syntax. Write your models once, and get a fully-typed, permission-aware API client for free.

```typescript
// Frontend code that feels like Django
const charts = await Chart.objects.filter({ user_id: currentUser.id });
const chart = await Chart.objects.get({ id: 1 });
await Chart.objects.create({ name: "My Chart", data: [...] });
```

## Background

Originally conceived in 2010 during the development of Chartio, django-guitar predates many similar solutions:

- **PostgREST / Supabase** - Auto-generated REST APIs from Postgres
- **Hasura / GraphQL** - Auto-generated GraphQL from databases
- **Prisma** - Type-safe database client generation
- **tRPC** - End-to-end type safety

Django Guitar brings this pattern to Django with a Pythonic, Django-native approach.

---

## Model-Level Security (MLS)

A key innovation in Django Guitar is **Model-Level Security (MLS)** - row-level permissions defined directly on your Django models.

### The Problem with Traditional Approaches

**Endpoint-based permissions** (typical REST):
```python
# permissions.py
class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user

# views.py - repeated for every endpoint
class ChartViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwner]
    
    def get_queryset(self):
        return Chart.objects.filter(user=self.request.user)
```
- ❌ Scattered across many files
- ❌ Easy to forget on new endpoints
- ❌ Hard to audit "who can access what"

**Database RLS** (PostgreSQL):
```sql
CREATE POLICY chart_access ON charts
    USING (user_id = current_user_id());
```
- ✅ Centralized and enforced
- ❌ SQL policies are awkward to write
- ❌ Difficult to test
- ❌ Hard to debug
- ❌ No Django ORM integration

### The MLS Solution

**Model-Level Security** gives you the centralization of RLS with the ergonomics of Python:

```python
class Chart(GuitarModel, models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class GuitarManager:
        def filter_read(self, request, queryset):
            return queryset.filter(user=request.user)
        
        def filter_write(self, request, queryset):
            return queryset.filter(user=request.user)
```

- ✅ **Centralized** - One place to define all permissions for a model
- ✅ **Pythonic** - Write in Python, not SQL
- ✅ **Testable** - Standard Django test patterns work
- ✅ **Reviewable** - Easy to read and code review
- ✅ **Flexible** - Full power of Django ORM, Python logic, external services
- ✅ **Familiar** - Django developers already organize logic by model

### MLS vs RLS Comparison

| Aspect | Database RLS | Model-Level Security |
|--------|--------------|---------------------|
| **Location** | PostgreSQL | Django models |
| **Language** | SQL | Python |
| **Testing** | Requires DB fixtures | Standard Django tests |
| **Debugging** | Query logs, painful | Python debugger, easy |
| **Code review** | SQL in migrations | Python in models.py |
| **Django ORM** | No integration | Full integration |
| **External calls** | Impossible | Easy (APIs, caches, etc.) |

MLS provides the *benefits* of RLS (centralized, declarative security) at the *application layer* where it's easier to work with.

---

## Core Concepts

### 1. GuitarModel Mixin

A mixin (or base class) that Django models inherit from to enable API generation:

```python
from guitar import GuitarModel

class Chart(GuitarModel, models.Model):
    name = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class GuitarMeta:
        # Fields exposed to the API
        fields = ['id', 'name', 'data', 'created_at', 'user_id']
        
        # Fields that can be written
        writable_fields = ['name', 'data']
        
        # Enable specific operations (use ONE of these, not both)
        operations = ['list', 'retrieve', 'create', 'update', 'delete']
        # OR
        exclude_operations = ['delete']  # All except delete
```

### 2. Permission Classes (Optional)

Boolean gates that run **before** any filter methods. Useful for cross-cutting concerns:

```python
from guitar.permissions import IsAuthenticated, RateLimited

class Chart(GuitarModel, models.Model):
    class GuitarMeta:
        # Simple: same for all operations
        permission_classes = [IsAuthenticated]
        
        # Or per-operation:
        permission_classes = {
            'read': [AllowAny],
            'write': [IsAuthenticated],
            'delete': [IsAuthenticated, IsAdmin],
        }
```

**Execution order:**
```
Request arrives
    ↓
permission_classes  → 401/403 if any fail (boolean checks)
    ↓
filter_* methods    → scope queryset (row-level)
    ↓
check_* methods     → validate data (value-level)
    ↓
Response
```

**When to use permission_classes vs filter_*:**

| Use case | Best approach |
|----------|---------------|
| "Must be logged in" | `permission_classes = [IsAuthenticated]` |
| "Admin only" | `permission_classes = [IsAdmin]` |
| "Rate limit to 100/min" | `permission_classes = [RateLimited]` |
| "Can only see own records" | `filter_read()` |
| "Complex row-based logic" | `filter_read()` |

Permission classes are optional - you can always do the same check inside `filter_read`:

```python
# These are equivalent:
class GuitarMeta:
    permission_classes = [IsAuthenticated]

# vs.
class GuitarManager:
    def filter_read(self, request, queryset):
        if not request.user.is_authenticated:
            raise PermissionDenied()
        return queryset
```

Global defaults in settings:
```python
GUITAR = {
    'DEFAULT_PERMISSION_CLASSES': ['guitar.permissions.IsAuthenticated'],
}
```

### 3. Permission Manager

Override methods to define row-level security. By default, permissions chain (cascade):

```
filter_queryset (base - applies to ALL operations)
    └── filter_read (viewing - list/retrieve)
            └── filter_write (modify - update) ← chains from filter_read
                    └── filter_delete (remove) ← chains from filter_write
```

**Default behavior (`chain_permissions = True`):** You can never write what you can't read, and never delete what you can't write.

```python
class Chart(GuitarModel, models.Model):
    # ... fields ...
    
    class GuitarManager:
        # chain_permissions = True  (default - safe)
        
        def filter_queryset(self, request, queryset):
            """Base filter for ALL operations. Optional."""
            # Example: tenant isolation
            return queryset.filter(organization=request.user.organization)
        
        # --- USING-style: Which existing rows can be accessed ---
        
        def filter_read(self, request, queryset):
            """Which rows can be viewed. (RLS: USING on SELECT)"""
            if request.user.is_superuser:
                return queryset
            return queryset.filter(Q(user=request.user) | Q(is_public=True))
        
        def filter_write(self, request, queryset):
            """Which rows can be modified. (RLS: USING on UPDATE)
            Chains from filter_read by default.
            """
            return queryset.filter(user=request.user)
        
        def filter_delete(self, request, queryset):
            """Which rows can be deleted. (RLS: USING on DELETE)
            Chains from filter_write by default.
            """
            return queryset.exclude(is_protected=True)
        
        # --- WITH CHECK-style: What data is valid to write ---
        
        def check_create(self, request, data):
            """Validate/modify data before create. (RLS: WITH CHECK on INSERT)
            Return modified data, or raise PermissionDenied.
            """
            # Force user_id to current user (can't create for others)
            data['user'] = request.user
            return data
        
        def check_write(self, request, instance, data):
            """Validate/modify data before update. (RLS: WITH CHECK on UPDATE)
            Return modified data, or raise PermissionDenied.
            """
            # Prevent transferring ownership
            if 'user' in data and data['user'] != instance.user:
                raise PermissionDenied("Cannot transfer ownership")
            return data
```

**Permission chain (default):**
| Method | If not defined | RLS Equivalent |
|--------|----------------|----------------|
| `filter_queryset` | All objects | Base policy |
| `filter_read` | `filter_queryset` | `USING` on SELECT |
| `filter_write` | `filter_read` | `USING` on UPDATE |
| `filter_delete` | `filter_write` | `USING` on DELETE |
| `check_create` | Allow (return data as-is) | `WITH CHECK` on INSERT |
| `check_write` | Allow (return data as-is) | `WITH CHECK` on UPDATE |

This means the minimal secure setup is just:

```python
class GuitarManager:
    def filter_read(self, request, queryset):
        return queryset.filter(user=request.user)
    # write and delete automatically chain from this!
    
    def check_create(self, request, data):
        data['user'] = request.user  # Force ownership
        return data
```

**Disabling chaining** for edge cases (write-only APIs, etc.):

```python
class AuditLog(GuitarModel, models.Model):
    class GuitarManager:
        chain_permissions = False  # Each filter is independent
        
        def filter_read(self, request, queryset):
            # Admins can read logs
            if request.user.is_admin:
                return queryset
            return queryset.none()
        
        def can_create(self, request, data):
            # Anyone can create logs (write-only for non-admins)
            return True
```

### Composable Predicates

Inspired by [django-rules](https://github.com/dfunckt/django-rules), Guitar supports composable predicates for reusable permission logic:

```python
from guitar import predicate

# Define reusable predicates
@predicate
def is_owner(request, obj):
    return obj.user == request.user

@predicate
def is_admin(request, obj):
    return request.user.is_staff

@predicate
def is_public(request, obj):
    return getattr(obj, 'is_public', False)

@predicate
def is_published(request, obj):
    return obj.status == 'published'

# Compose with | (or), & (and), ~ (not)
can_view = is_owner | is_admin | is_public
can_edit = is_owner | is_admin
can_delete = is_owner & ~is_published  # Owner can delete, but not if published
can_publish = is_admin & ~is_published  # Only admins, and only if not already published
```

**Use in `check_*` methods:**

```python
class Article(GuitarModel, models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20)
    is_public = models.BooleanField(default=False)
    
    class GuitarManager:
        def filter_read(self, request, queryset):
            # Filter-based (returns queryset)
            return queryset.filter(
                Q(user=request.user) | Q(is_public=True) | Q(user__is_staff=True)
            )
        
        def check_write(self, request, instance, data):
            # Predicate-based (returns bool, raises if False)
            if not can_edit(request, instance):
                raise PermissionDenied("Cannot edit this article")
            
            # Validate specific field changes
            if 'status' in data and data['status'] == 'published':
                if not can_publish(request, instance):
                    raise PermissionDenied("Only admins can publish")
            
            return data
        
        def check_delete(self, request, instance):
            if not can_delete(request, instance):
                raise PermissionDenied("Cannot delete published articles")
```

**Why both patterns?**

| Pattern | Returns | Best for |
|---------|---------|----------|
| `filter_*` | QuerySet | "Which rows can user access?" (listing, bulk ops) |
| Predicates | Boolean | "Can user do X to this specific object?" (validation) |

Predicates are especially useful for:
- Field-level validation ("can user set status to published?")
- Complex conditional logic
- Reusing the same rules across multiple models

**Predicate with arguments:**

```python
@predicate
def has_role(request, obj, role):
    return obj.memberships.filter(user=request.user, role=role).exists()

# Usage
can_manage = has_role.curry('admin') | has_role.curry('owner')
```

### 4. TypeScript Client Generation

Auto-generated TypeScript that mirrors Django's ORM:

```typescript
// Auto-generated: guitar_client.ts

interface Chart {
  id: number;
  name: string;
  data: Record<string, unknown>;
  created_at: string;
  user_id: number;
}

class ChartManager {
  async all(): Promise<Chart[]>
  async get(lookup: Partial<Chart>): Promise<Chart>
  async filter(lookup: Partial<Chart>): Promise<Chart[]>
  async create(data: ChartCreate): Promise<Chart>
  async update(lookup: Partial<Chart>, data: ChartUpdate): Promise<Chart>
  async delete(lookup: Partial<Chart>): Promise<void>
}

export const Chart = {
  objects: new ChartManager()
};
```

### Client Bundling & Distribution

#### Option A: Build-time Generation (Recommended)

Management command generates TypeScript files into your frontend directory:

```bash
python manage.py generate_guitar_client --output ./frontend/src/guitar/
```

```
frontend/src/guitar/
├── index.ts           # Main exports
├── client.ts          # Base HTTP client (fetch wrapper)
├── types.ts           # Shared types
└── models/
    ├── Chart.ts
    ├── Dashboard.ts
    └── User.ts
```

Usage in frontend:
```typescript
import { Chart, Dashboard } from './guitar';

const charts = await Chart.objects.filter({ user_id: 5 });
```

**Pros:** Full TypeScript support, IDE autocomplete, tree-shakeable
**When to regenerate:** After model changes, run in CI/CD or git pre-commit hook

#### Option B: Runtime Served (Original approach)

Django serves a compiled JS file at a URL - like the original 2010 django-guitar:

```python
# urls.py
urlpatterns = [
    path('guitar/client.js', guitar_client_view),  # Serves compiled JS
]
```

```html
<!-- In your HTML -->
<script src="/guitar/client.js"></script>
<script>
  const charts = await Chart.objects.all();
</script>
```

**Pros:** No build step, always in sync with models
**Cons:** No TypeScript types at dev time, not tree-shakeable

#### Option C: Hybrid (Dev convenience)

- **Development:** Django serves live-generated client at `/guitar/client.ts`
- **Production:** Pre-built TypeScript files

```python
GUITAR = {
    'SERVE_CLIENT': DEBUG,  # Only serve in dev
    'TYPESCRIPT_OUTPUT': './frontend/src/guitar/',
}
```

```bash
# Development: client auto-regenerates on model changes
# Production: generate once at build time
python manage.py generate_guitar_client
```

#### Hot Reload (Development)

In development, watch for model changes and regenerate:

```bash
python manage.py generate_guitar_client --watch
```

Or integrate with Django's runserver to auto-regenerate when models change.

---

## Architecture

### Option A: Built on Django REST Framework

```
┌─────────────────────────────────────────────────────────┐
│                    Django Guitar                         │
├─────────────────────────────────────────────────────────┤
│  GuitarModel Mixin                                       │
│    ├── Auto-generates DRF Serializers                   │
│    ├── Auto-generates DRF ViewSets                      │
│    └── Auto-generates Router URLs                       │
├─────────────────────────────────────────────────────────┤
│  TypeScript Generator                                    │
│    ├── Introspects models + serializers                 │
│    ├── Generates TypeScript interfaces                  │
│    └── Generates manager classes with fetch calls       │
├─────────────────────────────────────────────────────────┤
│  Django REST Framework                                   │
│    ├── Serialization                                    │
│    ├── Authentication                                   │
│    └── Request/Response handling                        │
└─────────────────────────────────────────────────────────┘
```

**Pros:**
- Battle-tested, widely used
- Extensive ecosystem (filters, pagination, auth)
- Familiar to Django developers

**Cons:**
- Heavier dependency
- Class-based views can be complex

### Option B: Built on Django Ninja

```
┌─────────────────────────────────────────────────────────┐
│                    Django Guitar                         │
├─────────────────────────────────────────────────────────┤
│  GuitarModel Mixin                                       │
│    ├── Auto-generates Pydantic Schemas                  │
│    ├── Auto-generates Ninja API endpoints               │
│    └── Registers routes automatically                   │
├─────────────────────────────────────────────────────────┤
│  TypeScript Generator                                    │
│    ├── Uses Pydantic schemas directly                   │
│    ├── Generates TypeScript interfaces                  │
│    └── Generates manager classes                        │
├─────────────────────────────────────────────────────────┤
│  Django Ninja                                            │
│    ├── Pydantic validation                              │
│    ├── Auto OpenAPI generation                          │
│    └── Fast, async-ready                                │
└─────────────────────────────────────────────────────────┘
```

**Pros:**
- Modern, fast, async-first
- Native Pydantic = better TypeScript generation
- Auto OpenAPI docs
- Less boilerplate

**Cons:**
- Smaller ecosystem
- Less widely adopted

### Recommendation

**Django Ninja** seems like the better fit because:
1. Pydantic models map directly to TypeScript interfaces
2. Built-in OpenAPI can be leveraged for client generation
3. Cleaner, more modern API
4. Async support for performance

---

## API Design

### REST Endpoints (Auto-generated)

```
GET    /guitar/chart/           → Chart.objects.all() / .filter()
GET    /guitar/chart/{id}/      → Chart.objects.get({id})
POST   /guitar/chart/           → Chart.objects.create()
PATCH  /guitar/chart/{id}/      → Chart.objects.update()
DELETE /guitar/chart/{id}/      → Chart.objects.delete()
```

### Query Parameters

```
GET /guitar/chart/?user_id=5&name__icontains=sales&_order=-created_at&_limit=10
```

Maps to:
```python
Chart.objects.filter(user_id=5, name__icontains='sales').order_by('-created_at')[:10]
```

### TypeScript Client API

```typescript
// Basic CRUD
await Chart.objects.all();
await Chart.objects.get({ id: 1 });
await Chart.objects.filter({ user_id: 5 });
await Chart.objects.create({ name: "New Chart", data: {} });
await Chart.objects.update({ id: 1 }, { name: "Updated" });
await Chart.objects.delete({ id: 1 });

// Advanced queries (Django-style lookups)
await Chart.objects.filter({ 
  name__icontains: "sales",
  created_at__gte: "2024-01-01",
  user_id__in: [1, 2, 3]
});

// Ordering and pagination
await Chart.objects.filter({ user_id: 5 }).order_by('-created_at').limit(10);

// Chaining
await Chart.objects
  .filter({ user_id: 5 })
  .exclude({ archived: true })
  .order_by('-created_at')
  .limit(10);
```

---

## TypeScript Generation

### Management Command

```bash
python manage.py generate_guitar_client --output ./frontend/src/guitar/
```

### Generated Structure

```
frontend/src/guitar/
├── index.ts           # Main exports
├── client.ts          # Base HTTP client
├── types.ts           # Shared types
└── models/
    ├── Chart.ts
    ├── Dashboard.ts
    └── User.ts
```

### Generated Model Example

```typescript
// models/Chart.ts
import { GuitarManager, GuitarConfig } from '../client';

export interface Chart {
  readonly id: number;
  name: string;
  data: Record<string, unknown>;
  readonly created_at: string;
  user_id: number;
}

export interface ChartCreate {
  name: string;
  data: Record<string, unknown>;
}

export interface ChartUpdate {
  name?: string;
  data?: Record<string, unknown>;
}

class ChartManager extends GuitarManager<Chart, ChartCreate, ChartUpdate> {
  protected endpoint = '/guitar/chart/';
}

export const Chart = {
  objects: new ChartManager()
};
```

---

## Permission System

### Row-Level Security

```python
class Chart(GuitarModel, models.Model):
    class GuitarManager:
        def get_queryset(self, request, action):
            """Base queryset for all operations"""
            qs = super().get_queryset(request, action)
            
            if action == 'list':
                return self.filter_list(request, qs)
            elif action == 'retrieve':
                return self.filter_retrieve(request, qs)
            elif action in ('update', 'partial_update'):
                return self.filter_update(request, qs)
            elif action == 'destroy':
                return self.filter_delete(request, qs)
            return qs
        
        def filter_list(self, request, queryset):
            # Users see their own charts + public charts
            return queryset.filter(
                Q(user=request.user) | Q(is_public=True)
            )
        
        def filter_update(self, request, queryset):
            # Users can only update their own charts
            return queryset.filter(user=request.user)
```

### Field-Level Security

```python
class Chart(GuitarModel, models.Model):
    class GuitarMeta:
        fields = ['id', 'name', 'data', 'created_at', 'user_id']
        
        # Different fields for different contexts
        list_fields = ['id', 'name', 'created_at']
        detail_fields = ['id', 'name', 'data', 'created_at', 'user_id']
        create_fields = ['name', 'data']
        update_fields = ['name', 'data']
```

### Pre/Post Hooks

```python
class Chart(GuitarModel, models.Model):
    class GuitarManager:
        def pre_create(self, request, data):
            """Modify data before creation"""
            data['user'] = request.user
            return data
        
        def post_create(self, request, instance):
            """Actions after creation"""
            send_notification(f"New chart created: {instance.name}")
        
        def pre_update(self, request, instance, data):
            """Validate or modify before update"""
            if 'data' in data:
                validate_chart_data(data['data'])
            return data
```

---

## Authentication

Guitar uses **Django's built-in authentication**. No special auth system - `request.user` comes from Django's auth middleware.

```python
# settings.py - standard Django auth
MIDDLEWARE = [
    ...
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    ...
]

# For JWT/token auth, use packages like:
# - djangorestframework-simplejwt
# - django-rest-knox
# - django-oauth-toolkit

# Guitar just uses request.user - however you populate it is up to you
```

Guitar's permission methods receive the standard Django request:
```python
def filter_read(self, request, queryset):
    # request.user is populated by Django's auth middleware
    return queryset.filter(user=request.user)
```

---

## Error Handling

Guitar returns **standard REST errors** - nothing fancy. Errors are HTTP status codes with JSON bodies:

```python
# HTTP Status Codes
400  # Bad Request - validation error, malformed request
401  # Unauthorized - not authenticated
403  # Forbidden - authenticated but not permitted
404  # Not Found - object doesn't exist (or filtered out by permissions)
405  # Method Not Allowed - operation not enabled for this model
429  # Too Many Requests - rate limited
500  # Server Error - unexpected error
```

**Error response format:**
```json
{
  "detail": "You do not have permission to perform this action."
}
```

For validation errors (400):
```json
{
  "name": ["This field is required."],
  "email": ["Enter a valid email address."]
}
```

This matches Django REST Framework's format. No custom error handling needed - just standard REST conventions that frontend developers expect.

---

## Configuration

### Global Settings

```python
# settings.py
GUITAR = {
    'BASE_URL': '/guitar/',
    'DEFAULT_PAGINATION': 50,
    'MAX_PAGINATION': 1000,
    'TYPESCRIPT_OUTPUT': './frontend/src/guitar/',
    'DEFAULT_PERMISSION_CLASSES': ['guitar.permissions.IsAuthenticated'],
}
```

### Model-Level Settings

```python
class Chart(GuitarModel, models.Model):
    class GuitarMeta:
        # API configuration
        endpoint_name = 'chart'  # defaults to model name lowercase
        
        # Field exposure (use fields OR exclude_fields, not both)
        fields = ['id', 'name', 'data', 'created_at']
        # OR
        exclude_fields = ['internal_secret', 'legacy_blob']  # Everything except these
        
        read_only_fields = ['id', 'created_at']
        
        # Operations (use one, not both)
        operations = ['list', 'retrieve', 'create', 'update', 'delete']
        exclude_operations = ['delete']  # clearer when excluding few
        
        # Pagination
        pagination = 50
        max_pagination = 200
        
        # Filtering
        filterable_fields = ['user_id', 'created_at', 'name']
        searchable_fields = ['name', 'description']
        orderable_fields = ['created_at', 'name']
```

---

## Method Architecture

### Core Principle: Generic Dispatcher

The backend has **one generic dispatcher** - no special-cased functions for `filter`, `order_by`, etc. Everything goes through the same path:

```python
manager[method_name](*args, **kwargs)
```

Built-in methods (`filter`, `exclude`, `order_by`) and custom manager methods (`trending`, `for_user`) are handled identically. This makes the system inherently extensible.

### Backend Implementation

```python
# The entire dispatcher - intentionally simple
def execute_chain(model, chain, request):
    qs = model.objects.all()
    
    # Apply permission filters first
    qs = model.GuitarManager().filter_read(request, qs)
    
    for step in chain:
        method_name = step['method']
        args = step.get('args', [])
        kwargs = step.get('kwargs', {})
        
        # Check blocklist (raw, extra, etc.)
        if method_name in BLOCKED_METHODS:
            raise MethodBlocked(method_name)
        
        # Check allowlist (if configured)
        allowed = model.GuitarMeta.allowed_methods
        if allowed and method_name not in allowed:
            raise MethodNotAllowed(method_name)
        
        # Optional: run validator if one exists
        validator = getattr(model.GuitarMeta, f'validate_{method_name}', None)
        if validator:
            validator(args, kwargs, request)
        
        # Execute - same for built-in AND custom methods
        method = getattr(qs, method_name)
        qs = method(*args, **kwargs)
    
    return qs
```

**Key insight:** There's no `if method_name == 'filter': ...` anywhere. The dispatcher doesn't know or care whether it's calling `filter()` or `trending()`. They're all just method names on the QuerySet.

### Wire Format: Hybrid Approach

Guitar uses a **hybrid approach** similar to Supabase/PostgREST:
- **Simple reads** → GET with query params (cacheable, RESTful)
- **Complex reads** → POST body (no URL limits)
- **Writes** → Standard REST verbs

#### Simple Reads (GET)

```
GET /guitar/chart/?user_id=5&name__icontains=sales&_order=-created_at&_limit=10

# With expansion
GET /guitar/chart/?user_id=5&_expand=dashboard,created_by

# Field selection
GET /guitar/chart/?_only=id,name,dashboard_id
```

**Reserved params (prefixed with `_`):**
| Param | Purpose | Example |
|-------|---------|---------|
| `_order` | Ordering | `_order=-created_at,name` |
| `_limit` | Pagination limit | `_limit=10` |
| `_offset` | Pagination offset | `_offset=20` |
| `_expand` | Expand relations | `_expand=dashboard,created_by` |
| `_only` | Include only these fields | `_only=id,name` |
| `_defer` | Exclude these fields | `_defer=large_blob` |

#### Complex Reads (POST)

For long filter chains, custom methods, or complex arguments:

```
POST /guitar/chart/_query/
{
  "chain": [
    { "method": "filter", "kwargs": { "user_id": 5 } },
    { "method": "trending", "args": [30] },
    { "method": "select_related", "args": ["dashboard"] },
    { "method": "first" }
  ]
}
```

#### Writes (Standard REST)

```
# Create
POST /guitar/chart/
{ "name": "New Chart", "dashboard_id": 1 }

# Update
PATCH /guitar/chart/5/
{ "name": "Updated Name" }

# Delete
DELETE /guitar/chart/5/

# Bulk operations
POST /guitar/chart/_bulk/
{
  "operation": "update",
  "filter": { "archived": true },
  "data": { "archived": false }
}
```

#### TypeScript Client Abstraction

The client automatically chooses GET or POST based on complexity:

```typescript
// Simple → client uses GET
await Chart.objects.filter({ user_id: 5 }).select_related('dashboard');
// GET /guitar/chart/?user_id=5&_expand=dashboard

// Complex → client uses POST
await Chart.objects.trending(30).with_stats().prefetch_related('dashboard.members');
// POST /guitar/chart/_query/ { "chain": [...] }
```

Developers don't need to think about the wire format.

---

## Naming Convention: snake_case

Guitar uses **snake_case** for all method names to match Django's API:

```typescript
// Guitar methods mirror Django exactly
await Chart.objects.select_related('dashboard')   // not selectRelated
await Chart.objects.order_by('-created_at')       // not orderBy
await Chart.objects.get_or_create({ name: 'X' })  // not getOrCreate
await Chart.objects.prefetch_related('members')   // not prefetchRelated
```

**Why snake_case?**
1. Guitar's identity is "Django ORM on the frontend" - should *feel* like Django
2. 1:1 mapping to Django docs (directly transferable knowledge)
3. Field names are already snake_case (`user_id`, `created_at`)
4. Immediately recognizable to Django developers

**ESLint configuration** (if needed):
```javascript
// .eslintrc.js
module.exports = {
  rules: {
    'camelcase': ['error', { 
      allow: ['^.*\\.objects\\.', '_id$', '_at$'] 
    }]
  }
}
```

### Method Configuration

```python
class Chart(GuitarModel, models.Model):
    class GuitarMeta:
        # Built-in methods to expose (whitelist)
        allowed_methods = [
            # Chainable
            'filter', 'exclude', 'order_by', 'reverse',
            'only', 'defer', 'distinct',
            'select_related', 'prefetch_related',
            # Terminal
            'get', 'first', 'last', 'earliest', 'latest',
            'exists', 'count', 'in_bulk',
        ]
        
        # Or use exclusion (blacklist)
        # excluded_methods = ['delete', 'update']  # block bulk operations
        
        # Expose custom manager methods
        custom_methods = ['active', 'for_user', 'with_stats', 'trending']
```

### Custom Manager Methods (like Supabase RPC)

Custom manager methods are Guitar's equivalent to **Supabase's `rpc()`** - server-side functions callable from the frontend. But unlike raw RPC or stored procedures, these are:

- **Type-safe** - defined in Python, generates TypeScript signatures
- **Chainable** - can combine with other QuerySet methods
- **Permission-aware** - still go through `filter_read`/`filter_write`

```python
class ChartQuerySet(models.QuerySet):
    def active(self):
        """Only non-archived charts."""
        return self.filter(archived=False)
    
    def for_user(self, user_id):
        """Charts the user has access to."""
        return self.filter(dashboard__members__id=user_id)
    
    def with_stats(self):
        """Annotate with view counts."""
        return self.annotate(
            view_count=Count('chart_views'),
            last_viewed=Max('chart_views__viewed_at')
        )
    
    def trending(self, days=7):
        """Charts with most views in last N days."""
        cutoff = timezone.now() - timedelta(days=days)
        return self.annotate(
            recent_views=Count(
                'chart_views',
                filter=Q(chart_views__viewed_at__gte=cutoff)
            )
        ).order_by('-recent_views')


class Chart(GuitarModel, models.Model):
    objects = ChartQuerySet.as_manager()
    
    class GuitarMeta:
        custom_methods = ['active', 'for_user', 'with_stats', 'trending']
```

### TypeScript Usage

```typescript
// Built-in methods
await Chart.objects.filter({ user_id: 5 }).first();

// Custom methods exposed to frontend
await Chart.objects.active().forUser(5).withStats();

// Chained with built-ins
await Chart.objects
  .active()
  .trending(30)
  .select_related('dashboard')
  .only('id', 'name', 'view_count');

// Parameters passed through
await Chart.objects.trending({ days: 7 });  // kwargs style
await Chart.objects.trending(7);             // args style
```

### TypeScript Generation for Custom Methods

```typescript
// Auto-generated from GuitarMeta.custom_methods
class ChartQuerySet extends BaseQuerySet<Chart> {
  active(): ChartQuerySet {
    return this._chain('active');
  }
  
  forUser(userId: number): ChartQuerySet {
    return this._chain('forUser', [userId]);
  }
  
  withStats(): ChartQuerySet<Chart & { view_count: number; last_viewed: string }> {
    return this._chain('withStats');
  }
  
  trending(days?: number): ChartQuerySet {
    return this._chain('trending', days !== undefined ? [days] : []);
  }
}
```

### Write Operations

Write operations use the same pattern but with different endpoints:

```typescript
// Create
await Chart.objects.create({ name: "New", dashboard_id: 1 });
// POST /guitar/chart/
// { "method": "create", "kwargs": { "name": "New", "dashboard_id": 1 } }

// Bulk update (filtered)
await Chart.objects.filter({ archived: true }).update({ archived: false });
// POST /guitar/chart/_query/
// { 
//   "chain": [
//     { "method": "filter", "kwargs": { "archived": true } },
//     { "method": "update", "kwargs": { "archived": false } }
//   ]
// }

// Delete
await Chart.objects.filter({ id: 1 }).delete();
// POST /guitar/chart/_query/
// {
//   "chain": [
//     { "method": "filter", "kwargs": { "id": 1 } },
//     { "method": "delete" }
//   ]
// }
```

### Security Considerations

**Blocked methods (never exposed, hardcoded):**
```python
# These are ALWAYS blocked - no configuration can enable them
BLOCKED_METHODS = [
    'raw',           # Raw SQL - SQL injection risk
    'extra',         # Deprecated, allows raw SQL
    'using',         # Database selection - not relevant
    'select_for_update',  # Row locking - not relevant for API
    'explain',       # Query analysis - info disclosure
]
```

**Configurable restrictions:**
```python
class GuitarMeta:
    # Restrict which kwargs are allowed for each method
    method_allowed_kwargs = {
        'filter': ['id', 'user_id', 'dashboard_id', 'created_at__gte'],
        'order_by': ['created_at', 'name', '-created_at', '-name'],
    }
    
    # Require certain methods to be terminal (can't chain after)
    terminal_methods = ['get', 'first', 'delete', 'update', 'count']
    
    # Methods that require specific permission classes
    method_permissions = {
        'delete': [IsAdmin],
        'update': [IsAuthenticated],
    }
```

**Why no raw SQL?**

Unlike Supabase RPC (which can call arbitrary SQL functions), Guitar custom methods are:
- Defined in Python code (reviewable, version-controlled)
- Still QuerySet-based (can't bypass ORM protections)
- Subject to the same permission filters

If you need raw SQL for performance, write a custom manager method:
```python
class ChartQuerySet(models.QuerySet):
    def with_complex_stats(self):
        # Raw SQL is allowed HERE (server-side, reviewed code)
        # But the method itself is what's exposed, not the SQL
        return self.raw('''
            SELECT c.*, COUNT(v.id) as view_count
            FROM charts c LEFT JOIN views v ON ...
        ''')
```

---

## Soft Deletes

Guitar doesn't have special soft-delete support - use Django's standard patterns. Override the delete behavior in your custom manager:

```python
class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        """Soft delete - set deleted_at instead of removing."""
        return self.update(deleted_at=timezone.now())
    
    def hard_delete(self):
        """Actually delete from database."""
        return super().delete()
    
    def active(self):
        """Only non-deleted records."""
        return self.filter(deleted_at__isnull=True)
    
    def deleted(self):
        """Only soft-deleted records."""
        return self.filter(deleted_at__isnull=False)


class Chart(GuitarModel, models.Model):
    deleted_at = models.DateTimeField(null=True, blank=True)
    objects = SoftDeleteQuerySet.as_manager()
    
    class GuitarMeta:
        custom_methods = ['active', 'deleted']
        exclude_fields = ['deleted_at']  # Hide from API
    
    class GuitarManager:
        def filter_read(self, request, queryset):
            # Only show active records by default
            return queryset.active().filter(user=request.user)
```

```typescript
// Frontend sees normal delete behavior
await Chart.objects.filter({ id: 1 }).delete();
// But it's actually a soft delete on the backend

// Admins could access deleted records via custom method
await Chart.objects.deleted();  // If exposed
```

Guitar doesn't need to know about soft deletes - it just calls the manager's `delete()` method, which you control.

---

## File Uploads

File and image fields require special handling since JSON can't contain binary data.

### Option A: Separate Upload Endpoint (Recommended)

```python
class Chart(GuitarModel, models.Model):
    thumbnail = models.ImageField(upload_to='charts/')
    
    class GuitarMeta:
        fields = ['id', 'name', 'thumbnail']  # thumbnail returns URL
        writable_fields = ['name']  # thumbnail NOT directly writable
```

```typescript
// 1. Upload file separately
const uploadResponse = await fetch('/guitar/upload/', {
  method: 'POST',
  body: formData  // multipart/form-data
});
const { file_id } = await uploadResponse.json();

// 2. Attach to object
await Chart.objects.create({
  name: "My Chart",
  thumbnail_id: file_id  // Reference the uploaded file
});

// 3. Read returns URL
const chart = await Chart.objects.get({ id: 1 });
chart.thumbnail  // "https://cdn.example.com/charts/abc123.png"
```

### Option B: Base64 Inline (Small files only)

```python
class GuitarMeta:
    file_upload_mode = 'base64'  # For small files like avatars
    max_file_size = 1024 * 1024  # 1MB limit
```

```typescript
await User.objects.update({ id: 1 }, {
  avatar: "data:image/png;base64,iVBORw0KGgo..."
});
```

### Option C: Presigned URLs (For large files)

```typescript
// 1. Get presigned upload URL
const { upload_url, file_id } = await Chart.objects.get_upload_url({
  filename: "chart.png",
  content_type: "image/png"
});

// 2. Upload directly to storage (S3, GCS, etc.)
await fetch(upload_url, { method: 'PUT', body: file });

// 3. Attach to object
await Chart.objects.update({ id: 1 }, { thumbnail_id: file_id });
```

---

## Computed Fields

Python `@property` methods can be included in the API:

```python
class User(GuitarModel, models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def initials(self):
        return f"{self.first_name[0]}{self.last_name[0]}"
    
    class GuitarMeta:
        fields = ['id', 'first_name', 'last_name', 'full_name', 'initials']
        read_only_fields = ['full_name', 'initials']  # Can't write to properties
```

TypeScript generation:
```typescript
interface User {
  id: number;
  first_name: string;
  last_name: string;
  readonly full_name: string;   // Computed, read-only
  readonly initials: string;    // Computed, read-only
}
```

For **annotated fields** (from QuerySet annotations):

```python
class ChartQuerySet(models.QuerySet):
    def with_stats(self):
        return self.annotate(
            view_count=Count('views'),
            last_viewed=Max('views__created_at')
        )

class Chart(GuitarModel):
    class GuitarMeta:
        custom_methods = ['with_stats']
        # Annotated fields defined for TypeScript generation
        annotated_fields = {
            'with_stats': {
                'view_count': 'number',
                'last_viewed': 'string | null',  # datetime as ISO string
            }
        }
```

```typescript
// TypeScript knows about annotated fields
const charts = await Chart.objects.with_stats();
charts[0].view_count;   // number
charts[0].last_viewed;  // string | null
```

---

## Pagination

### Offset-based (Simple)

```typescript
// Page 1
const page1 = await Chart.objects.filter({...}).limit(10);

// Page 2
const page2 = await Chart.objects.filter({...}).limit(10).offset(10);

// Page 3
const page3 = await Chart.objects.filter({...}).limit(10).offset(20);
```

**Pros:** Simple, random access to any page
**Cons:** Slow for large offsets, inconsistent if data changes

### Cursor-based (Recommended for large datasets)

```typescript
// First page
const page1 = await Chart.objects.filter({...}).order_by('-created_at').limit(10);
// Returns: { results: [...], next_cursor: "abc123", has_more: true }

// Next page using cursor
const page2 = await Chart.objects
  .filter({...})
  .order_by('-created_at')
  .after('abc123')
  .limit(10);
```

**Pros:** Fast regardless of position, consistent with changing data
**Cons:** No random access, must traverse sequentially

### Configuration

```python
GUITAR = {
    'DEFAULT_PAGINATION': 50,
    'MAX_PAGINATION': 1000,
    'PAGINATION_STYLE': 'offset',  # or 'cursor'
}

# Per-model override
class GuitarMeta:
    pagination = 100
    max_pagination = 500
    pagination_style = 'cursor'
```

### Response format

```json
{
  "results": [...],
  "count": 1234,
  "next_cursor": "eyJpZCI6MTAwfQ==",
  "has_more": true
}
```

---

## Relationships

### Foreign Key Handling

```python
class Chart(GuitarModel, models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class GuitarMeta:
        fields = ['id', 'name', 'user_id']  # Just the ID
        # OR
        expand = ['user']  # Include nested object
```

```typescript
// With expand
interface Chart {
  id: number;
  name: string;
  user: User;  // Nested object
}

// Request expansion
await Chart.objects.filter({ user_id: 5 }).expand('user');
```

### Reverse Relations

```python
class Dashboard(GuitarModel, models.Model):
    class GuitarMeta:
        expand = ['charts']  # Include related charts
```

```typescript
// Access related objects
const dashboard = await Dashboard.objects.get({ id: 1 }).expand('charts');
console.log(dashboard.charts);  // Chart[]
```

---

## Open Questions

1. **Realtime subscriptions?** Should we support WebSocket-based live updates?
   ```typescript
   Chart.objects.filter({ user_id: 5 }).subscribe((charts) => {
     // Called when charts change
   });
   ```

2. **Bulk operations?**
   ```typescript
   await Chart.objects.bulk_create([...]);
   await Chart.objects.filter({ archived: true }).bulkDelete();
   ```

3. **Aggregations?**
   ```typescript
   await Chart.objects.filter({ user_id: 5 }).count();
   await Chart.objects.aggregate({ total: Sum('views') });
   ```

4. **Caching strategy?** Client-side caching, ETags, stale-while-revalidate?

5. **Offline support?** Queue mutations when offline?

6. **Framework adapters?** 
   - React Query integration
   - SWR integration
   - Vue Query integration

---

## Implementation Phases

### Phase 0: Documentation First
Write the docs before the code - ensures we're aligned and catches design issues early.

- [ ] **Getting Started Guide** - Installation, first model, first query
- [ ] **API Reference** - All GuitarMeta options, GuitarManager methods
- [ ] **Permission Patterns Cookbook** - Common scenarios with examples
- [ ] **TypeScript Client Guide** - Usage, types, error handling

See [docs/](docs/) directory for documentation drafts.

### Phase 1: Core
- [ ] GuitarModel mixin
- [ ] Basic CRUD operations
- [ ] Permission manager (read/write/delete filters)
- [ ] Django Ninja integration
- [ ] Basic TypeScript generation

### Phase 2: Query Features
- [ ] Field lookups (`__icontains`, `__gte`, etc.)
- [ ] Ordering
- [ ] Pagination
- [ ] Field selection

### Phase 3: Reference App (Dashboard Example)
Build the [Dashboard App](examples/dashboard-app.md) as validation:
- [ ] User, Dashboard, Chart, DashboardMembership models
- [ ] Role-based permissions (creator/editor/viewer)
- [ ] M2M with through table (membership roles)
- [ ] Cascading permissions (charts via dashboard access)
- [ ] TypeScript client exercising all CRUD operations
- [ ] Test suite covering permission edge cases

This serves as:
1. **Validation** - Proves the core features work together
2. **Test harness** - Regression tests for all permission scenarios
3. **Documentation** - Living example for users
4. **Dogfooding** - Find UX issues before release

### Phase 4: Advanced
- [ ] Relationship expansion (`select_related`, `prefetch_related`)
- [ ] Nested writes
- [ ] Bulk operations
- [ ] Custom manager methods (RPC-style)
- [ ] Search

### Phase 5: Developer Experience
- [ ] Hot-reload TypeScript on model changes
- [ ] React Query / SWR adapters
- [ ] Admin panel integration
- [ ] OpenAPI documentation

### Phase 7: Production
- [ ] Caching
- [ ] Rate limiting
- [ ] Monitoring / logging
- [ ] Performance optimization

---

## Prior Art & Inspiration

| Project | Relationship |
|---------|-------------|
| **PostgREST** | Similar auto-API, but Postgres-native, not Django |
| **Supabase** | PostgREST + Auth + Realtime |
| **Hasura** | GraphQL version of similar concept |
| **Django REST Framework** | Potential foundation layer |
| **Django Ninja** | Potential foundation layer (preferred) |
| **Prisma** | TypeScript-first ORM inspiration |
| **tRPC** | End-to-end type safety inspiration |

---

## Name Ideas

- **Django Guitar** 🎸 - The original!
- **Django Bridge** - Bridging backend and frontend
- **Django Mirror** - Frontend mirrors backend
- **Django Echo** - API echoes ORM

---

## Getting Started (Future)

```bash
pip install django-guitar

# settings.py
INSTALLED_APPS = [
    ...
    'guitar',
]

# urls.py  
from guitar import guitar_router
urlpatterns = [
    path('guitar/', guitar_router.urls),
]

# Generate TypeScript
python manage.py generate_guitar_client
```

```typescript
// Frontend
import { Chart } from './guitar';

const charts = await Chart.objects.all();
```

