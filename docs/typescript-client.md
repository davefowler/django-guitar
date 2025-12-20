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
import { Chart, Dashboard, User } from './guitar';
```

---

## Basic CRUD

### Create

```typescript
const chart = await Chart.objects.create({
  name: 'Sales Q4',
  data: { values: [100, 200, 300] },
  dashboard_id: 1
});

console.log(chart.id);  // Auto-assigned ID
```

### Read

```typescript
// Get all
const charts = await Chart.objects.all();

// Get by ID
const chart = await Chart.objects.get({ id: 1 });

// Filter
const myCharts = await Chart.objects.filter({ user_id: 5 });

// First match (or null)
const chart = await Chart.objects.filter({ name: 'Sales' }).first();
```

### Update

```typescript
// Update single
await Chart.objects.filter({ id: 1 }).update({ name: 'New Name' });

// Update multiple
await Chart.objects.filter({ archived: false }).update({ archived: true });
```

### Delete

```typescript
// Delete single
await Chart.objects.filter({ id: 1 }).delete();

// Delete multiple
await Chart.objects.filter({ archived: true }).delete();
```

---

## Filtering

### Basic Filters

```typescript
// Exact match
Chart.objects.filter({ user_id: 5 })

// Multiple conditions (AND)
Chart.objects.filter({ user_id: 5, archived: false })
```

### Lookups

```typescript
// Comparison
Chart.objects.filter({ views__gt: 100 })       // views > 100
Chart.objects.filter({ views__gte: 100 })      // views >= 100
Chart.objects.filter({ views__lt: 100 })       // views < 100
Chart.objects.filter({ views__lte: 100 })      // views <= 100

// Text search
Chart.objects.filter({ name__contains: 'Sales' })      // Case-sensitive
Chart.objects.filter({ name__icontains: 'sales' })     // Case-insensitive
Chart.objects.filter({ name__startswith: 'Q4' })
Chart.objects.filter({ name__endswith: 'Report' })

// List membership
Chart.objects.filter({ status__in: ['draft', 'review'] })

// Null checks
Chart.objects.filter({ deleted_at__isnull: true })

// Date filters
Chart.objects.filter({ created_at__year: 2024 })
Chart.objects.filter({ created_at__gte: '2024-01-01' })
```

### Exclude

```typescript
// Exclude (opposite of filter)
Chart.objects.exclude({ archived: true })

// Combine filter and exclude
Chart.objects
  .filter({ user_id: 5 })
  .exclude({ status: 'draft' })
```

### Related Fields

```typescript
// Filter by related object's field
Chart.objects.filter({ dashboard__name: 'Sales' })

// Multiple levels deep
Chart.objects.filter({ dashboard__owner__email: 'alice@example.com' })
```

---

## Ordering

```typescript
// Ascending
Chart.objects.order_by('name')

// Descending (prefix with -)
Chart.objects.order_by('-created_at')

// Multiple fields
Chart.objects.order_by('-created_at', 'name')
```

---

## Pagination

### Limit & Offset

```typescript
// First 10
Chart.objects.limit(10)

// Skip first 20, take 10
Chart.objects.limit(10).offset(20)
```

### Cursor-Based

```typescript
// First page
const page1 = await Chart.objects.order_by('-created_at').limit(10);
// Returns: { results: [...], next_cursor: 'abc123', has_more: true }

// Next page
const page2 = await Chart.objects
  .order_by('-created_at')
  .after(page1.next_cursor)
  .limit(10);
```

---

## Field Selection

### Only (Include)

```typescript
// Only fetch specific fields
const charts = await Chart.objects.only('id', 'name');
// charts[0].id    ✓
// charts[0].name  ✓
// charts[0].data  undefined
```

### Defer (Exclude)

```typescript
// Fetch all except large fields
const charts = await Chart.objects.defer('large_blob', 'raw_data');
```

---

## Relationships

### Including Related Objects

By default, foreign keys return just the ID:

```typescript
const chart = await Chart.objects.get({ id: 1 });
chart.dashboard_id  // 5 (just the ID)
chart.dashboard     // undefined
```

Use `select_related` to include the full object:

```typescript
const chart = await Chart.objects
  .get({ id: 1 })
  .select_related('dashboard');

chart.dashboard_id  // 5
chart.dashboard     // { id: 5, name: 'Sales Dashboard', ... }
```

### Multiple Relations

```typescript
const chart = await Chart.objects
  .get({ id: 1 })
  .select_related('dashboard', 'created_by');

chart.dashboard   // Dashboard object
chart.created_by  // User object
```

### Nested Relations

```typescript
const chart = await Chart.objects
  .get({ id: 1 })
  .select_related('dashboard.owner');

chart.dashboard.owner  // User object
```

### Reverse Relations (prefetch_related)

For many-to-many or reverse foreign keys:

```typescript
const dashboard = await Dashboard.objects
  .get({ id: 1 })
  .prefetch_related('charts', 'members');

dashboard.charts   // Chart[]
dashboard.members  // User[]
```

---

## Aggregations

```typescript
// Count
const count = await Chart.objects.filter({ user_id: 5 }).count();

// Exists
const hasCharts = await Chart.objects.filter({ user_id: 5 }).exists();

// First / Last
const newest = await Chart.objects.order_by('-created_at').first();
const oldest = await Chart.objects.order_by('created_at').first();
```

---

## Custom Methods

If your Django model exposes custom QuerySet methods:

```python
# Django
class ChartQuerySet(models.QuerySet):
    def active(self):
        return self.filter(archived=False)
    
    def trending(self, days=7):
        return self.filter(created_at__gte=...).order_by('-views')

class Chart(GuitarModel):
    objects = ChartQuerySet.as_manager()
    
    class GuitarMeta:
        custom_methods = ['active', 'trending']
```

```typescript
// TypeScript
const charts = await Chart.objects.active().trending(30);

// Chain with built-in methods
const charts = await Chart.objects
  .active()
  .trending(7)
  .select_related('dashboard')
  .limit(10);
```

---

## Error Handling

```typescript
try {
  const chart = await Chart.objects.get({ id: 999 });
} catch (error) {
  if (error.status === 404) {
    console.log('Chart not found');
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
  await Chart.objects.create({ name: '' });
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
interface Chart {
  id: number;
  name: string;
  data: Record<string, unknown>;
  created_at: string;
  user_id: number;
}

// Create type (writable fields, required)
interface ChartCreate {
  name: string;
  data: Record<string, unknown>;
}

// Update type (writable fields, optional)
interface ChartUpdate {
  name?: string;
  data?: Record<string, unknown>;
}
```

### With Relations

```typescript
// When using select_related, type expands
const chart = await Chart.objects
  .get({ id: 1 })
  .select_related('dashboard');

// chart is typed as Chart & { dashboard: Dashboard | null }
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
import { Chart } from './guitar';

function ChartList() {
  const { data: charts, isLoading } = useQuery({
    queryKey: ['charts'],
    queryFn: () => Chart.objects.filter({ user_id: userId }),
  });
  
  const createChart = useMutation({
    mutationFn: (data: ChartCreate) => Chart.objects.create(data),
    onSuccess: () => queryClient.invalidateQueries(['charts']),
  });
  
  // ...
}
```

### With SWR

```typescript
import useSWR from 'swr';
import { Chart } from './guitar';

function ChartList() {
  const { data: charts, error } = useSWR(
    ['charts', userId],
    () => Chart.objects.filter({ user_id: userId })
  );
  
  // ...
}
```

