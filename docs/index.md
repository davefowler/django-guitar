# Django Guitar 🎸

**Django ORM for your frontend.**

Write your Django models once, get a fully-typed TypeScript client that works just like Django's ORM.

```typescript
// Frontend code that feels like Django
const questions = await Question.objects.filter({ pub_date__gte: '2024-01-01' });
const question = await Question.objects.get({ id: 1 });
await Question.objects.create({ question_text: "What's your favorite color?", pub_date: new Date() });
```

---

## Why Django Guitar?

**Before Guitar:** Manually write serializers, viewsets, URLs, TypeScript types, API client...

**After Guitar:** Add one mixin, get everything for free.

```python
from django.utils import timezone
from guitar import GuitarModel

class Question(GuitarModel, models.Model):
    question_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')
    
    class GuitarManager:
        def filter_read(self, request, queryset):
            return queryset.filter(pub_date__lte=timezone.now())
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
const questions = await Question.objects
  .filter({ question_text__icontains: 'favorite' })
  .exclude({ pub_date__lt: '2024-01-01' })
  .order_by('-pub_date')
  .limit(10);

// Include related objects
const question = await Question.objects
  .get({ id: 1 })
  .prefetch_related('choices');

// CRUD operations
await Question.objects.create({ question_text: 'New Question', pub_date: new Date() });
await Question.objects.filter({ id: 1 }).update({ question_text: 'Updated' });
await Question.objects.filter({ id: 1 }).delete();
```

---

## Model-Level Security (MLS)

Traditional APIs scatter permission logic across endpoints. Database RLS centralizes this but requires writing security in SQL. **Django Guitar brings Model-Level Security** - centralized permissions in Python, right where Django developers expect them.

```python
class Question(GuitarModel, models.Model):
    question_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')
    
    class GuitarManager:
        def filter_read(self, request, queryset):
            # Users see published questions
            return queryset.filter(pub_date__lte=timezone.now())
        
        def filter_write(self, request, queryset):
            # Users can only edit unpublished questions
            return queryset.filter(pub_date__gte=timezone.now())
```

**Why MLS over RLS?**

| | Database RLS | Model-Level Security |
|-|--------------|---------------------|
| **Language** | SQL policies | Python |
| **Testing** | Difficult | Standard Django tests |
| **Code review** | Awkward | Natural |
| **Debugging** | 😰 | Easy |
| **Django integration** | None | Native |

Define once. Enforce everywhere. Review easily.

---

## Features

| Feature | Description |
|---------|-------------|
| **Model-Level Security** | Row-level permissions defined once, on your models |
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

