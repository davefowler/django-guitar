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
from django.utils import timezone
from guitar import GuitarModel

class Question(GuitarModel, models.Model):
    question_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')
    
    class GuitarMeta:
        fields = ['id', 'question_text', 'pub_date']
        writable_fields = ['question_text', 'pub_date']
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
    └── Question.ts
```

## Use It in Your Frontend

```typescript
import { Question } from './guitar';

// List all questions
const questions = await Question.objects.all();

// Filter questions
const recentQuestions = await Question.objects.filter({ pub_date__year: 2024 });

// Get a single question
const question = await Question.objects.get({ id: 1 });

// Create a question
const newQuestion = await Question.objects.create({
  question_text: 'What is your favorite programming language?',
  pub_date: new Date()
});

// Update a question
await Question.objects.filter({ id: 1 }).update({ question_text: 'Updated Question' });

// Delete a question
await Question.objects.filter({ id: 1 }).delete();
```

It works just like Django's ORM!

---

## Model-Level Security (MLS)

Django Guitar uses **Model-Level Security** - permissions defined once, on your models. No more scattering permission checks across endpoints.

Add a `GuitarManager` to control access:

```python
class Question(GuitarModel, models.Model):
    question_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')
    
    class GuitarMeta:
        fields = ['id', 'question_text', 'pub_date']
        writable_fields = ['question_text', 'pub_date']
    
    class GuitarManager:
        def filter_read(self, request, queryset):
            """Users can only see published questions."""
            return queryset.filter(pub_date__lte=timezone.now())
        
        def filter_write(self, request, queryset):
            """Users can only edit unpublished questions."""
            return queryset.filter(pub_date__gte=timezone.now())
        
        def check_create(self, request, data):
            """Set pub_date to future if not provided."""
            if 'pub_date' not in data:
                data['pub_date'] = timezone.now()
            return data
```

Now:
- Users only see published questions
- Users can only edit unpublished questions
- New questions default to current time

---

## Chaining Queries

Just like Django, you can chain query methods:

```typescript
const questions = await Question.objects
  .filter({ pub_date__year: 2024 })
  .exclude({ pub_date__lt: '2024-01-01' })
  .order_by('-pub_date')
  .limit(10);
```

## Including Related Objects

```python
class Choice(GuitarModel, models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    choice_text = models.CharField(max_length=200)
    votes = models.IntegerField(default=0)
    
    class GuitarMeta:
        fields = ['id', 'choice_text', 'votes', 'question_id']
```

```typescript
// By default, just the ID
const choice = await Choice.objects.get({ id: 1 });
choice.question_id  // 5

// Include the full object
const choice = await Choice.objects.get({ id: 1 }).select_related('question');
choice.question  // { id: 5, question_text: 'What is...', ... }

// Include reverse relation
const question = await Question.objects.get({ id: 1 }).prefetch_related('choices');
question.choices  // [{ id: 1, choice_text: 'Python', ... }, ...]
```

---

## Next Steps

- [API Reference](api-reference.md) - All configuration options
- [Permission Patterns](permission-patterns.md) - Common permission scenarios
- [TypeScript Client](typescript-client.md) - Frontend usage details
- [Examples](https://github.com/davefowler/django-guitar/tree/main/examples) - Full example applications

