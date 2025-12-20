# Django Guitar 🎸

[![Documentation](https://img.shields.io/badge/docs-mkdocs-green.svg)](https://davefowler.github.io/django-guitar/)
[![PyPI](https://img.shields.io/pypi/v/django-guitar.svg)](https://pypi.org/project/django-guitar/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Django ORM for your frontend.**

Django Guitar automatically generates a fully-typed TypeScript client from your Django models. Write your models once, query them from the frontend with Django's familiar syntax.

```typescript
// Frontend code that feels like Django
const charts = await Chart.objects.filter({ user_id: currentUser.id });
const chart = await Chart.objects.get({ id: 1 });
await Chart.objects.create({ name: "My Chart", data: [...] });
```

## Features

- 🔌 **Auto-generated API** - No serializers, viewsets, or URL routing to write
- 🔒 **Model-Level Security (MLS)** - Row-level permissions defined once, on your models  
- 📝 **TypeScript types** - Full type safety with auto-generated interfaces
- 🔗 **Relationships** - `select_related` and `prefetch_related` just like Django
- 🎯 **Django syntax** - `filter`, `exclude`, `order_by` - all the hits
- ⚡ **Custom methods** - Expose custom QuerySet methods to the frontend

## Model-Level Security (MLS)

Traditional REST APIs scatter permission logic across dozens of endpoints. Database-level Row-Level Security (RLS) centralizes this, but SQL-based policies are awkward to write, test, and maintain.

**Django Guitar introduces Model-Level Security (MLS)** - the best of both worlds:

```python
class Chart(GuitarModel, models.Model):
    class GuitarManager:
        def filter_read(self, request, queryset):
            return queryset.filter(user=request.user)
        
        def filter_write(self, request, queryset):
            return queryset.filter(user=request.user)
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
from guitar import GuitarModel

class Chart(GuitarModel, models.Model):
    name = models.CharField(max_length=255)
    data = models.JSONField()
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    
    class GuitarMeta:
        fields = ['id', 'name', 'data', 'created_at', 'user_id']
        writable_fields = ['name', 'data']
    
    class GuitarManager:
        def filter_read(self, request, queryset):
            return queryset.filter(user=request.user)
```

### Generate TypeScript client

```bash
python manage.py generate_guitar_client
```

### Use in your frontend

```typescript
import { Chart } from './guitar';

// Just like Django!
const charts = await Chart.objects
  .filter({ name__icontains: 'sales' })
  .exclude({ archived: true })
  .order_by('-created_at')
  .select_related('dashboard')
  .limit(10);
```

## Documentation

📖 **[Full Documentation](https://davefowler.github.io/django-guitar/)**

- [Getting Started](https://davefowler.github.io/django-guitar/getting-started/) - Installation and first steps
- [API Reference](https://davefowler.github.io/django-guitar/api-reference/) - Complete configuration options
- [Permission Patterns](https://davefowler.github.io/django-guitar/permission-patterns/) - Common permission scenarios
- [TypeScript Client](https://davefowler.github.io/django-guitar/typescript-client/) - Frontend usage guide

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
                    │  Chart.objects.filter(...)  │
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

