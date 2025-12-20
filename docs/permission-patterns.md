# Permission Patterns Cookbook

Common Model-Level Security (MLS) patterns for Django Guitar.

MLS centralizes your permissions on the model - define once, enforce everywhere. No more scattered permission checks across endpoints.

---

## Basic Patterns

### User Owns Resource

Users can only see and edit their own records:

```python
class Chart(GuitarModel, models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    
    class GuitarManager:
        def filter_read(self, request, queryset):
            return queryset.filter(user=request.user)
        
        def check_create(self, request, data):
            data['user'] = request.user
            return data
```

### Public + Private Resources

Users see their own records plus public ones:

```python
class Chart(GuitarModel, models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_public = models.BooleanField(default=False)
    
    class GuitarManager:
        def filter_read(self, request, queryset):
            return queryset.filter(
                Q(user=request.user) | Q(is_public=True)
            )
        
        def filter_write(self, request, queryset):
            # Can only edit own charts (not public ones from others)
            return queryset.filter(user=request.user)
```

### Admin Can See All

Regular users see their own, admins see everything:

```python
class GuitarManager:
    def filter_read(self, request, queryset):
        if request.user.is_staff:
            return queryset
        return queryset.filter(user=request.user)
```

---

## Role-Based Access

### Simple Roles (User field)

```python
class Project(GuitarModel, models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    editors = models.ManyToManyField(User, related_name='editable_projects')
    viewers = models.ManyToManyField(User, related_name='viewable_projects')
    
    class GuitarManager:
        def filter_read(self, request, queryset):
            return queryset.filter(
                Q(owner=request.user) |
                Q(editors=request.user) |
                Q(viewers=request.user)
            ).distinct()
        
        def filter_write(self, request, queryset):
            return queryset.filter(
                Q(owner=request.user) |
                Q(editors=request.user)
            ).distinct()
        
        def filter_delete(self, request, queryset):
            return queryset.filter(owner=request.user)
```

### Roles via Through Table

More flexible - roles stored in a membership table:

```python
class DashboardMembership(models.Model):
    ROLES = [('viewer', 'Viewer'), ('editor', 'Editor'), ('owner', 'Owner')]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    dashboard = models.ForeignKey('Dashboard', on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLES)


class Dashboard(GuitarModel, models.Model):
    name = models.CharField(max_length=255)
    members = models.ManyToManyField(User, through=DashboardMembership)
    
    class GuitarManager:
        def filter_read(self, request, queryset):
            return queryset.filter(members=request.user)
        
        def filter_write(self, request, queryset):
            return queryset.filter(
                dashboardmembership__user=request.user,
                dashboardmembership__role__in=['editor', 'owner']
            )
        
        def filter_delete(self, request, queryset):
            return queryset.filter(
                dashboardmembership__user=request.user,
                dashboardmembership__role='owner'
            )
```

---

## Hierarchical Access

### Access Through Parent

Charts inherit access from their dashboard:

```python
class Chart(GuitarModel, models.Model):
    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    
    class GuitarManager:
        def filter_read(self, request, queryset):
            # User can see charts if they can see the dashboard
            return queryset.filter(dashboard__members=request.user)
        
        def filter_write(self, request, queryset):
            return queryset.filter(
                dashboard__dashboardmembership__user=request.user,
                dashboard__dashboardmembership__role__in=['editor', 'owner']
            )
        
        def check_create(self, request, data):
            # Verify user has edit access to the dashboard
            dashboard_id = data.get('dashboard_id')
            has_access = DashboardMembership.objects.filter(
                user=request.user,
                dashboard_id=dashboard_id,
                role__in=['editor', 'owner']
            ).exists()
            
            if not has_access:
                raise PermissionDenied("Cannot add charts to this dashboard")
            
            return data
```

### Organization/Tenant Isolation

Multi-tenant app where users only see their organization's data:

```python
class GuitarManager:
    def filter_queryset(self, request, queryset):
        """Base filter for ALL operations - tenant isolation."""
        return queryset.filter(organization=request.user.organization)
    
    def filter_read(self, request, queryset):
        # Additional read filters (already org-filtered)
        return queryset.filter(is_active=True)
```

---

## Data Validation

### Prevent Ownership Transfer

```python
class GuitarManager:
    def check_write(self, request, instance, data):
        if 'user' in data and data['user'] != instance.user:
            raise PermissionDenied("Cannot transfer ownership")
        return data
```

### Auto-Set Audit Fields

```python
class GuitarManager:
    def check_create(self, request, data):
        data['created_by'] = request.user
        return data
    
    def check_write(self, request, instance, data):
        data['updated_by'] = request.user
        return data
```

### Validate Status Transitions

```python
class GuitarManager:
    VALID_TRANSITIONS = {
        'draft': ['review', 'cancelled'],
        'review': ['published', 'draft'],
        'published': ['archived'],
    }
    
    def check_write(self, request, instance, data):
        if 'status' in data:
            old_status = instance.status
            new_status = data['status']
            
            if new_status not in self.VALID_TRANSITIONS.get(old_status, []):
                raise ValidationError(
                    f"Cannot transition from {old_status} to {new_status}"
                )
        return data
```

---

## Restricting Operations

### Read-Only Model

```python
class AuditLog(GuitarModel, models.Model):
    class GuitarMeta:
        operations = ['list', 'retrieve']  # No create, update, delete
```

### Create-Only (Append-Only)

```python
class Event(GuitarModel, models.Model):
    class GuitarMeta:
        operations = ['list', 'retrieve', 'create']  # No update, delete
```

### No Bulk Deletes

```python
class GuitarMeta:
    # Allow single delete, but delete requires an ID
    def filter_delete(self, request, queryset):
        # Only allow deleting single objects
        if queryset.count() > 1:
            raise PermissionDenied("Bulk delete not allowed")
        return queryset.filter(user=request.user)
```

---

## Advanced Patterns

### Time-Based Access

Records can only be edited within 24 hours of creation:

```python
class GuitarManager:
    def filter_write(self, request, queryset):
        cutoff = timezone.now() - timedelta(hours=24)
        return queryset.filter(
            user=request.user,
            created_at__gte=cutoff
        )
```

### Feature Flags

```python
from myapp.features import is_feature_enabled

class GuitarManager:
    def filter_read(self, request, queryset):
        if not is_feature_enabled('advanced_charts', request.user):
            queryset = queryset.exclude(chart_type__in=['advanced', 'premium'])
        return queryset.filter(user=request.user)
```

### Soft Delete

Soft delete pattern - override the delete method in your QuerySet:

```python
class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        return self.update(deleted_at=timezone.now())
    
    def active(self):
        return self.filter(deleted_at__isnull=True)

class Chart(GuitarModel, models.Model):
    deleted_at = models.DateTimeField(null=True, blank=True)
    objects = SoftDeleteQuerySet.as_manager()
    
    class GuitarManager:
        def filter_read(self, request, queryset):
            return queryset.active().filter(user=request.user)
```

---

## Composable Predicates

For complex validation logic, use composable predicates (inspired by django-rules):

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
def is_published(request, obj):
    return obj.status == 'published'

@predicate
def is_draft(request, obj):
    return obj.status == 'draft'

# Compose with | (or), & (and), ~ (not)
can_view = is_owner | is_admin | is_published
can_edit = (is_owner | is_admin) & ~is_published  # Can't edit published
can_delete = is_owner & is_draft  # Only owner, only drafts
can_publish = is_admin
```

Use in GuitarManager:

```python
class Article(GuitarModel, models.Model):
    class GuitarManager:
        def check_write(self, request, instance, data):
            if not can_edit(request, instance):
                raise PermissionDenied("Cannot edit this article")
            
            # Check specific transitions
            if data.get('status') == 'published':
                if not can_publish(request, instance):
                    raise PermissionDenied("Only admins can publish")
            
            return data
        
        def check_delete(self, request, instance):
            if not can_delete(request, instance):
                raise PermissionDenied("Can only delete your own drafts")
```

**When to use predicates vs filter_*:**

| Use Case | Best Approach |
|----------|---------------|
| "Which objects can user see?" | `filter_read()` |
| "Can user edit this specific field?" | Predicate in `check_write()` |
| "Can user perform this state transition?" | Predicate in `check_write()` |
| Bulk operations | `filter_*()` methods |
| Single-object validation | Predicates |

---

## Testing Permissions

```python
from django.test import TestCase
from guitar.test import GuitarTestMixin

class ChartPermissionTests(GuitarTestMixin, TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user('user1')
        self.user2 = User.objects.create_user('user2')
        self.chart = Chart.objects.create(name='Test', user=self.user1)
    
    def test_owner_can_read(self):
        self.client.force_login(self.user1)
        response = self.guitar_get(Chart, self.chart.id)
        self.assertEqual(response.status_code, 200)
    
    def test_non_owner_cannot_read(self):
        self.client.force_login(self.user2)
        response = self.guitar_get(Chart, self.chart.id)
        self.assertEqual(response.status_code, 404)  # Filtered out
    
    def test_owner_can_update(self):
        self.client.force_login(self.user1)
        response = self.guitar_patch(Chart, self.chart.id, {'name': 'New'})
        self.assertEqual(response.status_code, 200)
    
    def test_non_owner_cannot_update(self):
        self.client.force_login(self.user2)
        response = self.guitar_patch(Chart, self.chart.id, {'name': 'New'})
        self.assertEqual(response.status_code, 404)  # Filtered out
```

