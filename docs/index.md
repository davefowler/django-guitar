# Django Guitar 🎸

**Django ORM for your frontend.**

Write your Django models once, get a fully-typed TypeScript client that works just like Django's ORM.

```typescript
// Frontend code that feels like Django
const charts = await Chart.objects.filter({ user_id: currentUser.id });
const chart = await Chart.objects.get({ id: 1 });
await Chart.objects.create({ name: "My Chart", data: [...] });
```

---

## Why Django Guitar?

**Before Guitar:** Manually write serializers, viewsets, URLs, TypeScript types, API client...

**After Guitar:** Add one mixin, get everything for free.

```python
from guitar import GuitarModel

class Chart(GuitarModel, models.Model):
    name = models.CharField(max_length=255)
    data = models.JSONField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class GuitarManager:
        def filter_read(self, request, queryset):
            return queryset.filter(user=request.user)
```

That's it. You now have:

- ✅ REST API endpoints
- ✅ Row-level permissions
- ✅ TypeScript client with full types
- ✅ Django-style query syntax on the frontend

---

## Quick Example

```typescript
// Filter, order, paginate - just like Django
const charts = await Chart.objects
  .filter({ name__icontains: 'sales' })
  .exclude({ archived: true })
  .order_by('-created_at')
  .limit(10);

// Include related objects
const chart = await Chart.objects
  .get({ id: 1 })
  .select_related('dashboard', 'created_by');

// CRUD operations
await Chart.objects.create({ name: 'New Chart', data: {} });
await Chart.objects.filter({ id: 1 }).update({ name: 'Updated' });
await Chart.objects.filter({ id: 1 }).delete();
```

---

## Features

| Feature | Description |
|---------|-------------|
| **Model-Level Permissions** | Define read/write/delete filters directly on your models |
| **TypeScript Generation** | Auto-generated types that stay in sync |
| **Django Query Syntax** | `filter`, `exclude`, `order_by`, `select_related` - all the hits |
| **Custom Methods** | Expose custom QuerySet methods to the frontend |
| **Permission Chaining** | Write permissions automatically inherit from read |

---

## Documentation

| Guide | Description |
|-------|-------------|
| **[Getting Started](getting-started.md)** | Install Django Guitar and create your first API in 5 minutes |
| **[API Reference](api-reference.md)** | Complete reference for all configuration options |
| **[Permission Patterns](permission-patterns.md)** | Common permission scenarios with copy-paste solutions |
| **[TypeScript Client](typescript-client.md)** | How to use the generated client in your frontend |

---

## Inspired By

Django Guitar brings ideas from these great tools to the Django ecosystem:

- **Supabase / PostgREST** - Auto-generated REST APIs
- **Prisma** - Type-safe database clients
- **tRPC** - End-to-end type safety

But with a Django-native feel that Django developers will love.

