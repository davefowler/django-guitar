# TypeScript Client Guide

How to use the generated Guitar client in your frontend.

---

## Setup

### Generate the Client

```bash
python manage.py generate_guitar_client --output ./frontend/src/guitar/
```

### Import Models

```typescript
import { Question, Choice, User } from './guitar';
```

---

## Basic CRUD

### Create

```typescript
const question = await Question.objects.create({
  name: 'Sales Q4',
  data: { values: [100, 200, 300] },
  dashboard_id: 1
});

console.log(question.id);  // Auto-assigned ID
```

### Read

```typescript
// Get all
const questions = await Question.objects.all();

// Get by ID
const question = await Question.objects.get({ id: 1 });

// Filter
const myQuestions = await Question.objects.filter({ user_id: 5 });

// First match (or null)
const question = await Question.objects.filter({ name: 'Sales' }).first();
```

### Update

```typescript
// Update single
await Question.objects.filter({ id: 1 }).update({ name: 'New Name' });

// Update multiple
await Question.objects.filter({ archived: false }).update({ archived: true });
```

### Delete

```typescript
// Delete single
await Question.objects.filter({ id: 1 }).delete();

// Delete multiple
await Question.objects.filter({ archived: true }).delete();
```

---

## Filtering

### Basic Filters

```typescript
// Exact match
Question.objects.filter({ user_id: 5 })

// Multiple conditions (AND)
Question.objects.filter({ user_id: 5, archived: false })
```

### Lookups

```typescript
// Comparison
Question.objects.filter({ views__gt: 100 })       // views > 100
Question.objects.filter({ views__gte: 100 })      // views >= 100
Question.objects.filter({ views__lt: 100 })       // views < 100
Question.objects.filter({ views__lte: 100 })      // views <= 100

// Text search
Question.objects.filter({ name__contains: 'Sales' })      // Case-sensitive
Question.objects.filter({ name__icontains: 'sales' })     // Case-insensitive
Question.objects.filter({ name__startswith: 'Q4' })
Question.objects.filter({ name__endswith: 'Report' })

// List membership
Question.objects.filter({ status__in: ['draft', 'review'] })

// Null checks
Question.objects.filter({ deleted_at__isnull: true })

// Date filters
Question.objects.filter({ created_at__year: 2024 })
Question.objects.filter({ created_at__gte: '2024-01-01' })
```

### Exclude

```typescript
// Exclude (opposite of filter)
Question.objects.exclude({ archived: true })

// Combine filter and exclude
Question.objects
  .filter({ user_id: 5 })
  .exclude({ status: 'draft' })
```

### Related Fields

```typescript
// Filter by related object's field
Question.objects.filter({ dashboard__name: 'Sales' })

// Multiple levels deep
Question.objects.filter({ dashboard__owner__email: 'alice@example.com' })
```

---

## Ordering

```typescript
// Ascending
Question.objects.order_by('name')

// Descending (prefix with -)
Question.objects.order_by('-created_at')

// Multiple fields
Question.objects.order_by('-created_at', 'name')
```

---

## Pagination

### Limit & Offset

```typescript
// First 10
Question.objects.limit(10)

// Skip first 20, take 10
Question.objects.limit(10).offset(20)
```

### Cursor-Based

```typescript
// First page
const page1 = await Question.objects.order_by('-created_at').limit(10);
// Returns: { results: [...], next_cursor: 'abc123', has_more: true }

// Next page
const page2 = await Question.objects
  .order_by('-created_at')
  .after(page1.next_cursor)
  .limit(10);
```

---

## Field Selection

### Only (Include)

```typescript
// Only fetch specific fields
const questions = await Question.objects.only('id', 'name');
// questions[0].id    ✓
// questions[0].name  ✓
// questions[0].data  undefined
```

### Defer (Exclude)

```typescript
// Fetch all except large fields
const questions = await Question.objects.defer('large_blob', 'raw_data');
```

---

## Relationships

### Including Related Objects

By default, foreign keys return just the ID:

```typescript
const question = await Question.objects.get({ id: 1 });
question.dashboard_id  // 5 (just the ID)
question.dashboard     // undefined
```

Use `select_related` to include the full object:

```typescript
const question = await Question.objects
  .get({ id: 1 })
  .select_related('dashboard');

question.dashboard_id  // 5
question.dashboard     // { id: 5, name: 'Sales Choice', ... }
```

### Multiple Relations

```typescript
const question = await Question.objects
  .get({ id: 1 })
  .select_related('dashboard', 'created_by');

question.dashboard   // Choice object
question.created_by  // User object
```

### Nested Relations

```typescript
const question = await Question.objects
  .get({ id: 1 })
  .select_related('dashboard.owner');

question.dashboard.owner  // User object
```

### Reverse Relations (prefetch_related)

For many-to-many or reverse foreign keys:

```typescript
const dashboard = await Choice.objects
  .get({ id: 1 })
  .prefetch_related('questions', 'members');

dashboard.questions   // Question[]
dashboard.members  // User[]
```

---

## Aggregations

```typescript
// Count
const count = await Question.objects.filter({ user_id: 5 }).count();

// Exists
const hasQuestions = await Question.objects.filter({ user_id: 5 }).exists();

// First / Last
const newest = await Question.objects.order_by('-created_at').first();
const oldest = await Question.objects.order_by('created_at').first();
```

---

## Custom Methods

If your Django model exposes custom QuerySet methods:

```python
# Django
class QuestionQuerySet(models.QuerySet):
    def active(self):
        return self.filter(archived=False)
    
    def trending(self, days=7):
        return self.filter(created_at__gte=...).order_by('-views')

class Question(GuitarModel):
    objects = QuestionQuerySet.as_manager()
    
    class GuitarMeta:
        custom_methods = ['active', 'trending']
```

```typescript
// TypeScript
const questions = await Question.objects.active().trending(30);

// Chain with built-in methods
const questions = await Question.objects
  .active()
  .trending(7)
  .select_related('dashboard')
  .limit(10);
```

---

## Error Handling

```typescript
try {
  const question = await Question.objects.get({ id: 999 });
} catch (error) {
  if (error.status === 404) {
    console.log('Question not found');
  } else if (error.status === 403) {
    console.log('Permission denied');
  } else if (error.status === 401) {
    console.log('Not authenticated');
  }
}
```

### Error Types

```typescript
import { NotFoundError, PermissionDeniedError, ValidationError } from './guitar';

try {
  await Question.objects.create({ name: '' });
} catch (error) {
  if (error instanceof ValidationError) {
    console.log(error.fields);  // { name: ['This field is required.'] }
  }
}
```

---

## TypeScript Types

### Generated Interfaces

```typescript
// Read type (all fields)
interface Question {
  id: number;
  name: string;
  data: Record<string, unknown>;
  created_at: string;
  user_id: number;
}

// Create type (writable fields, required)
interface QuestionCreate {
  name: string;
  data: Record<string, unknown>;
}

// Update type (writable fields, optional)
interface QuestionUpdate {
  name?: string;
  data?: Record<string, unknown>;
}
```

### With Relations

```typescript
// When using select_related, type expands
const question = await Question.objects
  .get({ id: 1 })
  .select_related('dashboard');

// question is typed as Question & { dashboard: Choice | null }
```

---

## Configuration

### Base URL

```typescript
import { configure } from './guitar';

configure({
  baseUrl: '/api/guitar/',  // Default: /guitar/
});
```

### Authentication

```typescript
configure({
  // For cookie-based auth (default)
  credentials: 'include',
  
  // For token-based auth
  headers: {
    'Authorization': `Bearer ${token}`,
  },
});
```

### Custom Fetch

```typescript
configure({
  fetch: async (url, options) => {
    // Add custom logic
    const response = await fetch(url, {
      ...options,
      headers: {
        ...options.headers,
        'X-Custom-Header': 'value',
      },
    });
    
    // Handle token refresh, etc.
    return response;
  },
});
```

---

## React Integration

### With React Query

```typescript
import { useQuery, useMutation } from '@tanstack/react-query';
import { Question } from './guitar';

function QuestionList() {
  const { data: questions, isLoading } = useQuery({
    queryKey: ['questions'],
    queryFn: () => Question.objects.filter({ user_id: userId }),
  });
  
  const createQuestion = useMutation({
    mutationFn: (data: QuestionCreate) => Question.objects.create(data),
    onSuccess: () => queryClient.invalidateQueries(['questions']),
  });
  
  // ...
}
```

### With SWR

```typescript
import useSWR from 'swr';
import { Question } from './guitar';

function QuestionList() {
  const { data: questions, error } = useSWR(
    ['questions', userId],
    () => Question.objects.filter({ user_id: userId })
  );
  
  // ...
}
```

