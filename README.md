# Django Guitar 🎸

[![Documentation](https://img.shields.io/badge/docs-mkdocs-green.svg)](https://davefowler.github.io/django-guitar/)
[![PyPI](https://img.shields.io/pypi/v/django-guitar.svg)](https://pypi.org/project/django-guitar/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Django ORM for your frontend.**

Django Guitar automatically generates a fully-typed TypeScript client from your Django models. Write your models once, query them from the frontend with Django's familiar ORM syntax.

```typescript
// Frontend code that feels like Django
const questions = await Question.objects.filter({ pub_date__gte: '2024-01-01' });
const question = await Question.objects.get({ id: 1 });
await Question.objects.create({ question_text: "What's your favorite color?", pub_date: new Date() });
```

## Features

- 🔌 **Auto-generated API** - No serializers, viewsets, or URL routing to write
- 🔒 **Model-Level Security (MLS)** - Row-level permissions defined once, on your models  
- 📝 **TypeScript types** - Full type safety with auto-generated interfaces
- 🔗 **Relationships** - `select_related` and `prefetch_related` just like Django
- 🎯 **Django syntax** - `filter`, `exclude`, `order_by` - all the hits

## Model-Level Security (MLS)

Traditional REST APIs scatter permission logic across dozens of endpoints. Database-level Row-Level Security (RLS) centralizes this, but SQL-based policies are awkward to write, test, and maintain.

**Django Guitar introduces Model-Level Security (MLS)** - the best of both worlds:

```python
class Question(GuitarModel, models.Model):
    question_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')
    
    class GuitarManager:
        def filter_read(self, request, queryset):
            return queryset.filter(pub_date__lte=timezone.now())
        
        def filter_write(self, request, queryset):
            return queryset.filter(pub_date__gte=timezone.now())
```

**Why MLS?**

| Approach | Where | Pros | Cons |
|----------|-------|------|------|
| **Endpoint-based** | Views/Controllers | Familiar | Scattered, easy to miss |
| **Database RLS** | PostgreSQL | Centralized, enforced | SQL policies are awkward |
| **Model-Level (MLS)** | Django Models | Centralized, Pythonic | — |

- ✅ **Centralized** - One place to define and audit all permissions
- ✅ **Pythonic** - Write permissions in Python, not SQL
- ✅ **Reviewable** - Easy to read, test, and code review
- ✅ **Flexible** - Full power of Django ORM and Python
- ✅ **Familiar** - Django developers already think in models

## Quick Start

### Install

```bash
pip install django-guitar
```

### Add to your model

```python
from django.db import models
from django.utils import timezone
from guitar import GuitarModel

class Question(GuitarModel, models.Model):
    question_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')
    
    class GuitarMeta:
        fields = ['id', 'question_text', 'pub_date']
        writable_fields = ['question_text', 'pub_date']
    
    class GuitarManager:
        def filter_read(self, request, queryset):
            return queryset.filter(pub_date__lte=timezone.now())
```

### Generate TypeScript client

```bash
python manage.py generate_guitar_client
```

**After model changes:** Run Django migrations (`makemigrations`/`migrate`) then regenerate the TypeScript client to update types.

### Use in your frontend

```typescript
import { Question, Choice } from './guitar';

// Just like Django!
const questions = await Question.objects
  .filter({ question_text__icontains: 'favorite' })
  .exclude({ pub_date__lt: '2024-01-01' })
  .order_by('-pub_date')
  .prefetch_related('choices')
  .limit(10);

// Count (efficient server-side count)
const count = await Question.objects.filter({ pub_date__year: 2024 }).count();
// Returns: 20

// Exists check
const hasQuestions = await Question.objects.filter({ pub_date__year: 2024 }).exists();
// Returns: true

// Full-text search
const results = await Question.objects.search('favorite color');
```

## Documentation

📖 **[Full Documentation](https://davefowler.github.io/django-guitar/)**

- [Getting Started](https://davefowler.github.io/django-guitar/getting-started/) - Installation and first steps
- [API Reference](https://davefowler.github.io/django-guitar/api-reference/) - Complete configuration options
- [Permission Patterns](https://davefowler.github.io/django-guitar/permission-patterns/) - Common permission scenarios
- [TypeScript Client](https://davefowler.github.io/django-guitar/typescript-client/) - Frontend usage guide

## Limitations / Not Yet

Django Guitar is in **beta** (v0.1.0). Here's what works and what's coming:

### ✅ What Works

- **Basic CRUD** - Create, read, update, delete operations
- **Filtering** - Field lookups (`__icontains`, `__gte`, `__in`, etc.)
- **Ordering** - Single and multi-field ordering
- **Pagination** - Limit/offset pagination
- **Field selection** - `only()` and `defer()` for field selection
- **Relationship expansion** - `select_related()` and `prefetch_related()` with nested expansion support
- **Model-Level Security** - Full permission system with `filter_read`, `filter_write`, `filter_delete`
- **Lifecycle hooks** - `pre_create`, `post_create`, `pre_update`, `post_update`, etc.
- **Count/Exists** - Efficient `.count()` and `.exists()` methods (server-side, not fetching all results)
- **Full-text search** - PostgreSQL SearchVector or fallback to `icontains` across multiple fields
- **Bulk operations** - `bulk_create()` and `bulk_update()` endpoints (bulk delete via `queryset.delete()`)
- **Authentication** - Integrates with Django's built-in session/auth system (use Django's User model, permissions, etc.)
- **TypeScript generation** - Auto-generated types and client

### 🚧 Coming Soon

- **Custom QuerySet methods** - Expose custom manager methods to frontend:
  ```python
  class QuestionQuerySet(models.QuerySet):
      def published(self):
          return self.filter(pub_date__lte=timezone.now())
      
      def trending(self, days=7):
          cutoff = timezone.now() - timedelta(days=days)
          return self.annotate(
              recent_votes=Count('choice__votes', filter=Q(choice__vote_date__gte=cutoff))
          ).order_by('-recent_votes')
  
  class Question(GuitarModel, models.Model):
      objects = QuestionQuerySet.as_manager()
      
      class GuitarMeta:
          custom_methods = ['published', 'trending']  # Expose to frontend
  ```
  ```typescript
  // Frontend usage (coming soon!)
  const trending = await Question.objects.published().trending(30).limit(10);
  ```
- **Nested writes** - Create/update related objects in a single request
- **Cursor pagination** - More efficient pagination for large datasets
- **Realtime sync** - Subscribe to changes via WebSockets for multi-player experiences

### 🚫 Intentionally Not Supported

These features are intentionally excluded for security, simplicity, or design reasons:

- **Complex aggregations** (`Sum()`, `Avg()`, etc. via string parsing)
  - **Why:** String parsing of aggregation expressions is error-prone and a potential security risk
  - **Workaround:** When custom QuerySet methods land (see Coming Soon above), you'll be able to expose safe aggregations:
    ```python
    class QuestionQuerySet(models.QuerySet):
        def total_votes(self):
            return self.aggregate(total=Sum('choice__votes'))['total']
    
    class Question(GuitarModel, models.Model):
        objects = QuestionQuerySet.as_manager()
        
        class GuitarMeta:
            custom_methods = ['total_votes']  # Expose to frontend
    ```
    ```typescript
    const total = await Question.objects.filter({ id: 1 }).total_votes();
    ```

- **File uploads via JSON API**
  - **Why:** File uploads require `multipart/form-data`, which doesn't fit the JSON REST API pattern
  - **Workaround:** Use separate Django endpoints for file uploads, or direct S3/cloud storage uploads with signed URLs

- **Raw SQL queries**
  - **Why:** Security risk - raw SQL bypasses Django's ORM protections.  We don't want that on the front-end.
  - **Workaround:** Use Django's ORM methods, or expose safe custom QuerySet methods


### ⚠️ Known Limitations

- **Performance** - No built-in caching or rate limiting (add at Django/Nginx level)
- **Bulk operations and lifecycle hooks** - `bulk_create()` and `bulk_update()` use Django's bulk methods, which bypass `save()` and signals (same as Django's behavior). Lifecycle hooks like `post_create` won't run. Use individual `create()`/`update()` calls if you need hooks.

### 📝 Field Lookups Supported

Currently supported lookups:

**Basic comparisons:** `exact`, `iexact`, `contains`, `icontains`, `startswith`, `istartswith`, `endswith`, `iendswith`, `gt`, `gte`, `lt`, `lte`, `in`, `isnull`, `range`

**Date/time lookups:** `year`, `month`, `day`, `week_day`, `hour`, `minute`, `second`, `date`, `time`, `week`, `quarter`, `iso_year`

**Text lookups:** `regex`, `iregex`

All standard Django ORM field lookups are now supported!

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                         Django                               │
│  ┌─────────────────┐    ┌─────────────────┐                 │
│  │  GuitarModel    │───▶│  Auto-generated │                 │
│  │  + GuitarMeta   │    │  REST API       │                 │
│  │  + GuitarManager│    │  (Django Ninja) │                 │
│  └─────────────────┘    └────────┬────────┘                 │
└──────────────────────────────────┼──────────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │     TypeScript Client       │
                    │  Question.objects.filter(...)  │
                    └─────────────────────────────┘
```

## Inspired By

Django Guitar brings ideas from these great tools to Django:

| Project | Inspiration |
|---------|-------------|
| **Supabase / PostgREST** | Auto-generated REST APIs from database |
| **Prisma** | Type-safe database clients |
| **tRPC** | End-to-end type safety |

But with Django's familiar, Pythonic API.

## Development

```bash
# Clone the repo
git clone https://github.com/davefowler/django-guitar.git
cd django-guitar

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Serve docs locally
pip install mkdocs-material
mkdocs serve
```

## License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  Made with 🎸 for the Django community
</p>

