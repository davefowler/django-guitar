# Getting Started with Django Guitar

Django Guitar automatically generates a Django-like API for your frontend. Define your models once, get a fully-typed TypeScript client for free.

## Installation

```bash
pip install django-guitar
```

```python
# settings.py
INSTALLED_APPS = [
    ...
    'guitar',
]

GUITAR = {
    'BASE_URL': '/guitar/',
    'TYPESCRIPT_OUTPUT': './frontend/src/guitar/',
}
```

```python
# urls.py
from guitar import guitar_urls

urlpatterns = [
    ...
    path('guitar/', include(guitar_urls)),
]
```

## Your First Guitar Model

Add `GuitarModel` to any Django model:

```python
# models.py
from django.db import models
from guitar import GuitarModel

class Chart(GuitarModel, models.Model):
    name = models.CharField(max_length=255)
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    
    class GuitarMeta:
        fields = ['id', 'name', 'data', 'created_at', 'user_id']
        writable_fields = ['name', 'data']
```

That's it! Your model now has a full REST API.

## Generate the TypeScript Client

```bash
python manage.py generate_guitar_client
```

This creates TypeScript files in your frontend:

```
frontend/src/guitar/
├── index.ts
├── client.ts
└── models/
    └── Chart.ts
```

## Use It in Your Frontend

```typescript
import { Chart } from './guitar';

// List all charts
const charts = await Chart.objects.all();

// Filter charts
const myCharts = await Chart.objects.filter({ user_id: 5 });

// Get a single chart
const chart = await Chart.objects.get({ id: 1 });

// Create a chart
const newChart = await Chart.objects.create({
  name: 'Sales Q4',
  data: { labels: ['Jan', 'Feb'], values: [100, 200] }
});

// Update a chart
await Chart.objects.filter({ id: 1 }).update({ name: 'Updated Name' });

// Delete a chart
await Chart.objects.filter({ id: 1 }).delete();
```

It works just like Django's ORM!

---

## Adding Permissions

By default, anyone can access your models. Add a `GuitarManager` to control access:

```python
class Chart(GuitarModel, models.Model):
    # ... fields ...
    
    class GuitarMeta:
        fields = ['id', 'name', 'data', 'created_at', 'user_id']
        writable_fields = ['name', 'data']
    
    class GuitarManager:
        def filter_read(self, request, queryset):
            """Users can only see their own charts."""
            return queryset.filter(user=request.user)
        
        def filter_write(self, request, queryset):
            """Users can only edit their own charts."""
            return queryset.filter(user=request.user)
        
        def check_create(self, request, data):
            """Set the user automatically on create."""
            data['user'] = request.user
            return data
```

Now:
- Users only see their own charts
- Users can only edit their own charts
- New charts are automatically assigned to the current user

---

## Chaining Queries

Just like Django, you can chain query methods:

```typescript
const charts = await Chart.objects
  .filter({ user_id: 5 })
  .exclude({ archived: true })
  .order_by('-created_at')
  .limit(10);
```

## Including Related Objects

```python
class Chart(GuitarModel, models.Model):
    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE)
    
    class GuitarMeta:
        fields = ['id', 'name', 'dashboard_id']
```

```typescript
// By default, just the ID
const chart = await Chart.objects.get({ id: 1 });
chart.dashboard_id  // 5

// Include the full object
const chart = await Chart.objects.get({ id: 1 }).select_related('dashboard');
chart.dashboard  // { id: 5, name: 'Sales Dashboard', ... }
```

---

## Next Steps

- [API Reference](api-reference.md) - All configuration options
- [Permission Patterns](permission-patterns.md) - Common permission scenarios
- [TypeScript Client](typescript-client.md) - Frontend usage details
- [Examples](https://github.com/davefowler/django-guitar/tree/main/examples) - Full example applications

