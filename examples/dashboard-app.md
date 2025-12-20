# Example: Dashboard App

A collaborative dashboard application demonstrating Guitar's permission system.

## Data Model

```
┌─────────────┐       ┌─────────────────────┐       ┌─────────────┐
│    User     │──M2M──│ DashboardMembership │──M2M──│  Dashboard  │
└─────────────┘       │  - role             │       └──────┬──────┘
                      │    (creator/editor/ │              │
                      │     viewer)         │              │ FK
                      └─────────────────────┘              │
                                                    ┌──────┴──────┐
                                                    │    Chart    │
                                                    └─────────────┘
```

## Roles & Permissions

| Role | Dashboard | Charts | Invite Users |
|------|-----------|--------|--------------|
| **creator** | create, read, update, delete | create, read, update, delete | ✓ |
| **editor** | read, update | create, read, update, delete | ✗ |
| **viewer** | read | read | ✗ |

## Models

```python
from django.db import models
from django.contrib.auth.models import User
from guitar import GuitarModel

class Dashboard(GuitarModel, models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # M2M with role via through table
    members = models.ManyToManyField(
        User, 
        through='DashboardMembership',
        related_name='dashboards'
    )
    
    class GuitarMeta:
        fields = ['id', 'name', 'description', 'created_at', 'updated_at']
        writable_fields = ['name', 'description']
        operations = ['list', 'retrieve', 'create', 'update', 'delete']
    
    class GuitarManager:
        def filter_read(self, request, queryset):
            """Users can see dashboards they're a member of."""
            return queryset.filter(members=request.user)
        
        def filter_write(self, request, queryset):
            """Only creators and editors can update dashboards."""
            return queryset.filter(
                dashboardmembership__user=request.user,
                dashboardmembership__role__in=['creator', 'editor']
            )
        
        def filter_delete(self, request, queryset):
            """Only creators can delete dashboards."""
            return queryset.filter(
                dashboardmembership__user=request.user,
                dashboardmembership__role='creator'
            )
        
        def check_create(self, request, data):
            """Anyone can create a dashboard (they become the creator)."""
            return data
        
        def post_create(self, request, instance):
            """Auto-add creator as member with 'creator' role."""
            DashboardMembership.objects.create(
                user=request.user,
                dashboard=instance,
                role='creator'
            )


class DashboardMembership(GuitarModel, models.Model):
    """Through table for Dashboard <-> User with role."""
    
    ROLE_CHOICES = [
        ('creator', 'Creator'),
        ('editor', 'Editor'),
        ('viewer', 'Viewer'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    invited_at = models.DateTimeField(auto_now_add=True)
    invited_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='invitations_sent'
    )
    
    class Meta:
        unique_together = ['user', 'dashboard']
    
    class GuitarMeta:
        fields = ['id', 'user_id', 'dashboard_id', 'role', 'invited_at']
        writable_fields = ['user_id', 'role']  # dashboard set via URL/context
        exclude_operations = ['update']  # Can only create or delete memberships
    
    class GuitarManager:
        def filter_read(self, request, queryset):
            """Can see memberships for dashboards you're a member of."""
            return queryset.filter(dashboard__members=request.user)
        
        def filter_delete(self, request, queryset):
            """Only creators can remove members."""
            return queryset.filter(
                dashboard__dashboardmembership__user=request.user,
                dashboard__dashboardmembership__role='creator'
            ).exclude(
                # Can't remove yourself if you're the only creator
                user=request.user,
                role='creator'
            )
        
        def check_create(self, request, data):
            """Only creators can invite new members."""
            dashboard_id = data.get('dashboard_id')
            
            is_creator = DashboardMembership.objects.filter(
                user=request.user,
                dashboard_id=dashboard_id,
                role='creator'
            ).exists()
            
            if not is_creator:
                raise PermissionDenied("Only creators can invite members")
            
            data['invited_by'] = request.user
            return data


class Chart(GuitarModel, models.Model):
    dashboard = models.ForeignKey(
        Dashboard, 
        on_delete=models.CASCADE,
        related_name='charts'
    )
    name = models.CharField(max_length=255)
    chart_type = models.CharField(max_length=50)  # bar, line, pie, etc.
    query = models.TextField()  # SQL or config
    position = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class GuitarMeta:
        fields = ['id', 'dashboard_id', 'name', 'chart_type', 'query', 'position', 'created_at']
        writable_fields = ['name', 'chart_type', 'query', 'position']
        # Note: dashboard_id not writable - can't move charts between dashboards
    
    class GuitarManager:
        def filter_read(self, request, queryset):
            """Can see charts in dashboards you're a member of."""
            return queryset.filter(dashboard__members=request.user)
        
        def filter_write(self, request, queryset):
            """Creators and editors can update charts."""
            return queryset.filter(
                dashboard__dashboardmembership__user=request.user,
                dashboard__dashboardmembership__role__in=['creator', 'editor']
            )
        
        def filter_delete(self, request, queryset):
            """Creators and editors can delete charts."""
            # Same as write - editors CAN delete charts (just not dashboards)
            return queryset.filter(
                dashboard__dashboardmembership__user=request.user,
                dashboard__dashboardmembership__role__in=['creator', 'editor']
            )
        
        def check_create(self, request, data):
            """Creators and editors can add charts to dashboards."""
            dashboard_id = data.get('dashboard_id')
            
            membership = DashboardMembership.objects.filter(
                user=request.user,
                dashboard_id=dashboard_id,
                role__in=['creator', 'editor']
            ).first()
            
            if not membership:
                raise PermissionDenied("Must be creator or editor to add charts")
            
            data['created_by'] = request.user
            return data
```

---

## TypeScript Usage

```typescript
import { Dashboard, Chart, DashboardMembership } from './guitar';

// ============================================================
// VIEWER: Alice is a viewer on Dashboard #1
// ============================================================

// ✓ Can list dashboards she's a member of
const dashboards = await Dashboard.objects.all();
// Returns: [{ id: 1, name: "Sales Dashboard", ... }]

// ✓ Can view charts
const charts = await Chart.objects.filter({ dashboard_id: 1 });
// Returns: [{ id: 1, name: "Revenue Chart", ... }, ...]

// ✗ Cannot update dashboard
await Dashboard.objects.update({ id: 1 }, { name: "New Name" });
// Error: 404 Not Found (filtered out by filter_write)

// ✗ Cannot delete charts
await Chart.objects.delete({ id: 1 });
// Error: 404 Not Found

// ✗ Cannot invite members
await DashboardMembership.objects.create({
    dashboard_id: 1,
    user_id: 5,
    role: 'viewer'
});
// Error: 403 "Only creators can invite members"


// ============================================================
// EDITOR: Bob is an editor on Dashboard #1
// ============================================================

// ✓ Can update dashboard
await Dashboard.objects.update({ id: 1 }, { name: "Updated Name" });
// Success

// ✓ Can create charts
await Chart.objects.create({
    dashboard_id: 1,
    name: "New Chart",
    chart_type: "bar",
    query: "SELECT ..."
});
// Success

// ✓ Can delete charts
await Chart.objects.delete({ id: 5 });
// Success

// ✗ Cannot delete dashboard
await Dashboard.objects.delete({ id: 1 });
// Error: 404 Not Found

// ✗ Cannot invite members
await DashboardMembership.objects.create({ ... });
// Error: 403 "Only creators can invite members"


// ============================================================
// CREATOR: Carol is the creator of Dashboard #1
// ============================================================

// ✓ Full CRUD on dashboard
await Dashboard.objects.update({ id: 1 }, { name: "Carol's Dashboard" });
await Dashboard.objects.delete({ id: 1 });

// ✓ Full CRUD on charts
await Chart.objects.create({ ... });
await Chart.objects.delete({ id: 10 });

// ✓ Can invite new members
await DashboardMembership.objects.create({
    dashboard_id: 1,
    user_id: 5,
    role: 'editor'
});
// Success - user 5 is now an editor

// ✓ Can change member roles
// (if we allowed update on DashboardMembership)

// ✓ Can remove members
await DashboardMembership.objects.delete({ id: 3 });
// Success - removed member
```

---

## Edge Cases Demonstrated

### 1. Cascading Permissions via Relationships
Charts inherit access from their parent Dashboard:
```python
def filter_read(self, request, queryset):
    return queryset.filter(dashboard__members=request.user)
```

### 2. Role-Based Row Filtering
Same queryset, different operations:
```python
def filter_write(self, request, queryset):
    return queryset.filter(..., role__in=['creator', 'editor'])

def filter_delete(self, request, queryset):
    return queryset.filter(..., role='creator')  # More restrictive
```

### 3. check_create for Validation
When you can't use queryset filtering (no existing row):
```python
def check_create(self, request, data):
    if not is_creator:
        raise PermissionDenied("Only creators can invite")
    data['invited_by'] = request.user  # Auto-set audit field
    return data
```

### 4. post_create Hook
Auto-setup after creation:
```python
def post_create(self, request, instance):
    DashboardMembership.objects.create(
        user=request.user,
        dashboard=instance,
        role='creator'  # Creator of new dashboard
    )
```

### 5. Preventing Self-Removal
Business logic in filter:
```python
def filter_delete(self, request, queryset):
    return queryset.filter(...).exclude(
        user=request.user,
        role='creator'  # Can't remove yourself as creator
    )
```

---

## API Endpoints Generated

```
# Dashboards
GET    /guitar/dashboard/           → list (filtered by membership)
GET    /guitar/dashboard/{id}/      → retrieve
POST   /guitar/dashboard/           → create (becomes creator)
PATCH  /guitar/dashboard/{id}/      → update (creator/editor only)
DELETE /guitar/dashboard/{id}/      → delete (creator only)

# Charts
GET    /guitar/chart/               → list (via dashboard membership)
GET    /guitar/chart/{id}/          → retrieve
POST   /guitar/chart/               → create (creator/editor only)
PATCH  /guitar/chart/{id}/          → update (creator/editor only)
DELETE /guitar/chart/{id}/          → delete (creator/editor only)

# Memberships
GET    /guitar/dashboardmembership/         → list (see your dashboard's members)
POST   /guitar/dashboardmembership/         → create (creator invites)
DELETE /guitar/dashboardmembership/{id}/    → delete (creator removes)
```

---

## Possible Extensions

1. **Public dashboards** - Add `is_public` boolean, adjust `filter_read`:
   ```python
   def filter_read(self, request, queryset):
       return queryset.filter(
           Q(members=request.user) | Q(is_public=True)
       )
   ```

2. **Dashboard templates** - Clonable dashboards with `clone_from_id`

3. **Chart data caching** - Add `cached_data` field with `read_only_fields`

4. **Audit log** - Track all changes (write-only model with `chain_permissions=False`)

5. **Transfer ownership** - Explicit endpoint to transfer creator role

