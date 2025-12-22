# Guitar Frontend Framework - v3 Iteration

Focused on: auto-generated custom elements from templates, wiring up a complete todo app.

---

## Auto-Generated Custom Elements from Templates

### The Idea

If you create `guitar/templates/chart/card.html`, Guitar automatically creates a `<chart-card>` custom element.

### File Structure

```
guitar/
└── templates/
    └── chart/
        ├── card.html          # Template → creates <chart-card>
        ├── card.ts            # Optional: behavior/defaults
        ├── card.css           # Optional: scoped styles
        ├── full.html          # Template → creates <chart-full>
        ├── full.ts
        ├── list-item.html     # Template → creates <chart-list-item>
        └── edit.html          # Template → creates <chart-edit>
```

### What Gets Generated

For `guitar/templates/chart/card.html`:

```typescript
// Auto-generated: guitar/elements/chart-card.ts
import { GuitarElement } from '@guitar/core';
import template from '../templates/chart/card.html?raw';
import styles from '../templates/chart/card.css?raw';  // if exists
import config from '../templates/chart/card.ts';       // if exists

class ChartCardElement extends GuitarElement {
  static modelName = 'chart';
  static templateName = 'card';
  static template = template;
  static styles = styles;
  static config = config || {};
}

customElements.define('chart-card', ChartCardElement);
```

### The Template File (card.html)

```html
<!-- guitar/templates/chart/card.html -->
<div class="chart-card">
  <header>
    <h3>{{ chart.name }}</h3>
    <span class="badge">{{ chart.chart_type }}</span>
  </header>
  
  <div class="chart-preview">
    <!-- Chart visualization -->
  </div>
  
  <footer>
    <time datetime="{{ chart.created_at }}">
      {{ chart.created_at|date:"M d, Y" }}
    </time>
    <div class="actions">
      <button data-action="edit">Edit</button>
      <button data-action="delete">Delete</button>
    </div>
  </footer>
</div>
```

### The Config File (card.ts) - Optional

```typescript
// guitar/templates/chart/card.ts
import type { ElementConfig } from '@guitar/core';
import type { Chart } from '../models/Chart';

const config: ElementConfig<Chart> = {
  // Default event handlers
  onSuccess: (chart) => {
    console.log('Chart action succeeded:', chart);
  },
  
  onError: (error) => {
    console.error('Chart action failed:', error);
  },
  
  // Action handlers (for data-action="xxx" buttons)
  actions: {
    edit: (chart, element) => {
      Guitar.navigate(`/charts/${chart.id}/edit`);
    },
    
    delete: async (chart, element) => {
      if (confirm(`Delete "${chart.name}"?`)) {
        await Chart.objects.filter({ id: chart.id }).delete();
      }
    },
    
    duplicate: async (chart, element) => {
      await Chart.objects.create({
        ...chart,
        name: `${chart.name} (copy)`,
      });
    },
  },
  
  // DOM event handlers
  on: {
    click: (chart, element, event) => {
      Chart.emit('selected', chart);
    },
  },
  
  // Lifecycle
  onMount: (chart, element) => {
    console.log('Card mounted for chart:', chart.id);
  },
  
  onUpdate: (oldChart, newChart, element) => {
    element.classList.add('flash');
    setTimeout(() => element.classList.remove('flash'), 300);
  },
};

export default config;
```

### The Styles File (card.css) - Optional

```css
/* guitar/templates/chart/card.css */
/* Automatically scoped to the component */

.chart-card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  padding: 16px;
  transition: box-shadow 0.2s;
}

.chart-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.chart-card.selected {
  outline: 2px solid var(--primary-color);
}

.chart-card.flash {
  animation: flash 0.3s ease;
}

@keyframes flash {
  50% { background: var(--highlight-color); }
}
```

### Using the Auto-Generated Element

```html
<!-- Single chart -->
<chart-card item-id="123"></chart-card>

<!-- Or with data passed directly -->
<chart-card .data="${chartObject}"></chart-card>

<!-- Override default handlers -->
<chart-card 
  item-id="123"
  on-success="handleSuccess"
  on-error="handleError"
></chart-card>
```

---

## Creating Custom Elements via registerElement

Beyond auto-generation, you can explicitly create custom elements:

```typescript
// This creates a <chart-dashboard-card> custom element
Guitar.registerElement('chart-dashboard-card', {
  model: 'chart',
  template: 'card',  // Uses existing template
  
  // Override/extend defaults
  actions: {
    edit: (chart) => openModal('chart-edit', chart),
  },
  
  onSuccess: (chart) => {
    showToast(`Updated "${chart.name}"`);
    refreshDashboard();
  },
});
```

```html
<!-- Now usable anywhere -->
<chart-dashboard-card item-id="123"></chart-dashboard-card>
```

### Difference from registerConfig

| Function | Creates Custom Element? | Purpose |
|----------|------------------------|---------|
| `registerElement()` | ✅ Yes | Create a new `<tag-name>` element |
| `registerConfig()` | ❌ No | Store config to use with `config="name"` attribute |

```typescript
// registerElement - creates <todo-inline-editor> element
Guitar.registerElement('todo-inline-editor', { ... });

// registerConfig - stores config, used via attribute
Guitar.registerConfig('todo-inline-config', { ... });
```

```html
<!-- Using registerElement result -->
<todo-inline-editor item-id="5"></todo-inline-editor>

<!-- Using registerConfig result -->
<guitar-edit config="todo-inline-config" item-id="5"></guitar-edit>
```

---

## Queryset Attribute

You asked about a `queryset` attribute for complex queries. Here's how it could work:

### Option A: Filter Attributes (Current)

```html
<guitar-list 
  model="todo"
  template="list-item"
  filter='{"completed": false, "priority": "high"}'
  order-by="-created_at"
  limit="20"
></guitar-list>
```

**Pros:** Declarative, easy to read, easy to modify dynamically
**Cons:** Can't do complex queries like `OR`, annotations, etc.

### Option B: Queryset as JS Expression

```html
<guitar-list 
  model="todo"
  template="list-item"
  queryset="Todo.objects.filter({completed: false}).exclude({archived: true}).order_by('-priority', '-created_at')"
></guitar-list>
```

**Pros:** Full power of the queryset API
**Cons:** JS in HTML attribute (a bit ugly), harder to modify dynamically

### Option C: Named Querysets (Recommended)

```typescript
// Register named querysets
Guitar.registerQueryset('active-todos', () => 
  Todo.objects
    .filter({ completed: false })
    .exclude({ archived: true })
    .order_by('-priority', '-created_at')
);

Guitar.registerQueryset('my-high-priority', (params) => 
  Todo.objects
    .filter({ 
      user_id: params.userId,
      priority: 'high',
      completed: false,
    })
    .order_by('-created_at')
);
```

```html
<!-- Use by name -->
<guitar-list 
  queryset="active-todos"
  template="list-item"
></guitar-list>

<!-- With params -->
<guitar-list 
  queryset="my-high-priority"
  queryset-params='{"userId": 5}'
  template="list-item"
></guitar-list>
```

**Pros:** Complex queries defined in JS, clean HTML, reusable
**Cons:** Extra registration step

### Recommendation

Support both `filter`/`order-by` attributes AND named `queryset`:

```typescript
class GuitarListElement extends HTMLElement {
  async load() {
    let qs;
    
    const querysetName = this.getAttribute('queryset');
    if (querysetName) {
      // Use registered queryset
      const querysetFn = Guitar.getQueryset(querysetName);
      const params = JSON.parse(this.getAttribute('queryset-params') || '{}');
      qs = querysetFn(params);
    } else {
      // Build from attributes
      const model = this.getAttribute('model');
      const ModelClass = Guitar.getModel(model);
      
      qs = ModelClass.objects;
      
      const filter = this.getAttribute('filter');
      if (filter) qs = qs.filter(JSON.parse(filter));
      
      const orderBy = this.getAttribute('order-by');
      if (orderBy) qs = qs.order_by(...orderBy.split(','));
      
      const limit = this.getAttribute('limit');
      if (limit) qs = qs.limit(parseInt(limit));
    }
    
    // Apply dynamic filters from search/sort controls
    qs = this.applyDynamicFilters(qs);
    
    // Fetch and render
    const items = await qs.render(this.getAttribute('template')).all();
    // ...
  }
}
```

---

## Complete Todo App Example (Vanilla JS)

Let's wire up a full todo app with search and sort, no frameworks.

### File Structure

```
guitar/templates/todo/
├── list-item.html     # → <todo-list-item>
├── list-item.ts
├── edit.html          # → <todo-edit> (doubles as full view)
├── edit.ts
└── edit.css
```

### Template: list-item.html

```html
<!-- guitar/templates/todo/list-item.html -->
<li class="todo-item {{ 'completed' if todo.completed else '' }} priority-{{ todo.priority }}">
  <label class="todo-checkbox">
    <input 
      type="checkbox" 
      {{ 'checked' if todo.completed else '' }}
      data-action="toggle-complete"
    >
  </label>
  
  <span class="todo-title" data-action="select">
    {{ todo.title }}
  </span>
  
  <span class="todo-priority badge badge-{{ todo.priority }}">
    {{ todo.priority }}
  </span>
  
  {% if todo.due_date %}
  <time class="todo-due" datetime="{{ todo.due_date }}">
    {{ todo.due_date|date:"M d" }}
  </time>
  {% endif %}
  
  <button class="todo-delete" data-action="delete" title="Delete">×</button>
</li>
```

### Config: list-item.ts

```typescript
// guitar/templates/todo/list-item.ts
import type { ElementConfig } from '@guitar/core';
import type { Todo } from '../models/Todo';

const config: ElementConfig<Todo> = {
  actions: {
    'toggle-complete': async (todo, element, event) => {
      const checkbox = event.target as HTMLInputElement;
      await Todo.objects.filter({ id: todo.id }).update({
        completed: checkbox.checked
      });
    },
    
    select: (todo, element) => {
      Todo.emit('selected', todo);
    },
    
    delete: async (todo, element) => {
      if (confirm(`Delete "${todo.title}"?`)) {
        await Todo.objects.filter({ id: todo.id }).delete();
      }
    },
  },
  
  on: {
    dblclick: (todo, element) => {
      // Double-click to edit inline
      element.querySelector('.todo-title')?.setAttribute('contenteditable', 'true');
      element.querySelector('.todo-title')?.focus();
    },
  },
  
  // Subscribe to model events
  subscribe: {
    selected: (selectedTodo, todo, element) => {
      element.classList.toggle('selected', selectedTodo.id === todo.id);
    },
  },
};

export default config;
```

### Template: edit.html

```html
<!-- guitar/templates/todo/edit.html -->
<form class="todo-edit-form">
  <div class="form-header">
    <input 
      type="text" 
      name="title" 
      class="todo-title-input"
      value="{{ todo.title }}"
      placeholder="What needs to be done?"
      required
      data-autosave
    >
    
    <label class="todo-completed-toggle">
      <input 
        type="checkbox" 
        name="completed"
        {{ 'checked' if todo.completed else '' }}
        data-autosave
      >
      Done
    </label>
  </div>
  
  <div class="form-body">
    <div class="form-field">
      <label>Priority</label>
      <div class="priority-buttons" data-field="priority" data-autosave>
        {% for p in ['low', 'medium', 'high'] %}
        <button 
          type="button"
          class="{{ 'active' if todo.priority == p else '' }}"
          data-value="{{ p }}"
        >
          {{ p|title }}
        </button>
        {% endfor %}
      </div>
    </div>
    
    <div class="form-field">
      <label for="due_date">Due Date</label>
      <input 
        type="date" 
        name="due_date" 
        id="due_date"
        value="{{ todo.due_date }}"
        data-autosave
      >
    </div>
    
    <div class="form-field">
      <label for="notes">Notes</label>
      <textarea 
        name="notes" 
        id="notes"
        rows="4"
        data-autosave
      >{{ todo.notes }}</textarea>
    </div>
  </div>
  
  <div class="form-footer">
    <span class="save-indicator"></span>
    <button type="button" data-action="delete" class="btn-danger">
      Delete Todo
    </button>
  </div>
</form>
```

### Config: edit.ts

```typescript
// guitar/templates/todo/edit.ts
import type { ElementConfig } from '@guitar/core';
import type { Todo } from '../models/Todo';

const config: ElementConfig<Todo> = {
  // Auto-save configuration
  autoSave: {
    enabled: true,
    debounce: 800,
    fields: '[data-autosave]',  // Selector for auto-save fields
    indicator: '.save-indicator',
  },
  
  actions: {
    delete: async (todo, element) => {
      if (confirm(`Delete "${todo.title}"? This cannot be undone.`)) {
        await Todo.objects.filter({ id: todo.id }).delete();
        Todo.emit('deleted', todo);
      }
    },
  },
  
  onSuccess: (todo, element) => {
    const indicator = element.querySelector('.save-indicator');
    if (indicator) {
      indicator.textContent = 'Saved';
      indicator.className = 'save-indicator saved';
      setTimeout(() => {
        indicator.textContent = '';
      }, 2000);
    }
  },
  
  onError: (error, todo, element) => {
    const indicator = element.querySelector('.save-indicator');
    if (indicator) {
      indicator.textContent = 'Error saving';
      indicator.className = 'save-indicator error';
    }
  },
  
  // Handle priority button group
  onMount: (todo, element) => {
    const priorityButtons = element.querySelector('.priority-buttons');
    priorityButtons?.addEventListener('click', (e) => {
      const button = (e.target as Element).closest('button');
      if (!button) return;
      
      // Update UI
      priorityButtons.querySelectorAll('button').forEach(b => 
        b.classList.toggle('active', b === button)
      );
      
      // Trigger auto-save
      element.dispatchEvent(new CustomEvent('guitar-field-change', {
        detail: { field: 'priority', value: button.dataset.value }
      }));
    });
  },
};

export default config;
```

### The Main HTML Page

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Guitar Todo App</title>
  <link rel="stylesheet" href="/static/todo/styles.css">
  
  <!-- Guitar runtime -->
  <script type="module" src="/static/guitar/guitar.js"></script>
</head>
<body>
  <div class="todo-app">
    
    <!-- SIDEBAR: List of todos -->
    <aside class="todo-sidebar">
      <header class="sidebar-header">
        <h1>My Todos</h1>
        
        <!-- Search box -->
        <input 
          type="search"
          id="todo-search"
          placeholder="Search todos..."
          class="search-input"
        >
        
        <!-- Sort dropdown -->
        <select id="todo-sort" class="sort-select">
          <option value="-created_at">Newest</option>
          <option value="created_at">Oldest</option>
          <option value="-priority">Priority ↓</option>
          <option value="priority">Priority ↑</option>
          <option value="due_date">Due Date</option>
          <option value="title">A-Z</option>
        </select>
      </header>
      
      <!-- Filter tabs -->
      <nav class="filter-tabs">
        <button class="active" data-filter="all">All</button>
        <button data-filter="active">Active</button>
        <button data-filter="completed">Completed</button>
      </nav>
      
      <!-- Todo list - auto-generated custom element! -->
      <ul id="todo-list" class="todo-list">
        <guitar-list 
          model="todo"
          template="list-item"
          order-by="-created_at"
        ></guitar-list>
      </ul>
      
      <!-- Quick add -->
      <form id="quick-add" class="quick-add">
        <input 
          type="text" 
          name="title" 
          placeholder="Add a todo..." 
          required
        >
        <button type="submit">Add</button>
      </form>
    </aside>
    
    <!-- MAIN: Detail/Edit view -->
    <main class="todo-main">
      <div id="todo-detail" class="todo-detail-container">
        <!-- Empty state - shown when no todo selected -->
        <div class="empty-state">
          <p>Select a todo to view details</p>
        </div>
      </div>
    </main>
    
  </div>
  
  <script type="module">
    import { Guitar, Todo } from '/static/guitar/index.js';
    
    // Initialize Guitar
    Guitar.init();
    
    // === WIRING UP SEARCH ===
    const searchInput = document.getElementById('todo-search');
    const guitarList = document.querySelector('guitar-list');
    
    let searchDebounce;
    searchInput.addEventListener('input', () => {
      clearTimeout(searchDebounce);
      searchDebounce = setTimeout(() => {
        // Set dynamic filter on the list
        guitarList.setFilter('title__icontains', searchInput.value || null);
      }, 300);
    });
    
    // === WIRING UP SORT ===
    const sortSelect = document.getElementById('todo-sort');
    
    sortSelect.addEventListener('change', () => {
      guitarList.setOrderBy(sortSelect.value);
    });
    
    // === WIRING UP FILTER TABS ===
    const filterTabs = document.querySelectorAll('.filter-tabs button');
    
    filterTabs.forEach(tab => {
      tab.addEventListener('click', () => {
        // Update active state
        filterTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        
        // Apply filter
        const filter = tab.dataset.filter;
        switch (filter) {
          case 'active':
            guitarList.setFilter('completed', false);
            break;
          case 'completed':
            guitarList.setFilter('completed', true);
            break;
          default:
            guitarList.clearFilter('completed');
        }
      });
    });
    
    // === WIRING UP QUICK ADD ===
    const quickAddForm = document.getElementById('quick-add');
    
    quickAddForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const input = quickAddForm.querySelector('input');
      const title = input.value.trim();
      
      if (title) {
        await Todo.objects.create({ title });
        input.value = '';
        // List auto-refreshes via event subscription
      }
    });
    
    // === WIRING UP SELECTION → DETAIL VIEW ===
    const detailContainer = document.getElementById('todo-detail');
    
    Todo.on('selected', async (todo) => {
      // Replace detail container content with edit view
      // Using the auto-generated <todo-edit> element!
      detailContainer.innerHTML = `
        <todo-edit item-id="${todo.id}"></todo-edit>
      `;
    });
    
    Todo.on('deleted', (todo) => {
      // Clear detail view if deleted todo was selected
      const currentEdit = detailContainer.querySelector('todo-edit');
      if (currentEdit?.getAttribute('item-id') === String(todo.id)) {
        detailContainer.innerHTML = `
          <div class="empty-state">
            <p>Todo deleted. Select another.</p>
          </div>
        `;
      }
    });
    
  </script>
</body>
</html>
```

### The GuitarList Element API

```typescript
// The <guitar-list> element exposes these methods for external control:

interface GuitarListElement extends HTMLElement {
  // Set a filter field (additive)
  setFilter(field: string, value: any): void;
  
  // Clear a specific filter
  clearFilter(field: string): void;
  
  // Clear all dynamic filters
  clearFilters(): void;
  
  // Replace all filters
  replaceFilters(filters: Record<string, any>): void;
  
  // Set ordering
  setOrderBy(...fields: string[]): void;
  
  // Refresh the list
  refresh(): void;
  
  // Get current items
  getItems(): any[];
}
```

### Implementation of setFilter, setOrderBy

```typescript
class GuitarListElement extends HTMLElement {
  private _dynamicFilters: Record<string, any> = {};
  private _dynamicOrderBy: string[] | null = null;
  
  setFilter(field: string, value: any): void {
    if (value === null || value === undefined || value === '') {
      delete this._dynamicFilters[field];
    } else {
      this._dynamicFilters[field] = value;
    }
    this.load();  // Reload with new filters
  }
  
  clearFilter(field: string): void {
    delete this._dynamicFilters[field];
    this.load();
  }
  
  clearFilters(): void {
    this._dynamicFilters = {};
    this.load();
  }
  
  replaceFilters(filters: Record<string, any>): void {
    this._dynamicFilters = { ...filters };
    this.load();
  }
  
  setOrderBy(...fields: string[]): void {
    this._dynamicOrderBy = fields;
    this.load();
  }
  
  async load(): Promise<void> {
    const model = this.getAttribute('model');
    const template = this.getAttribute('template') || 'list-item';
    
    // Build queryset
    const ModelClass = Guitar.getModel(model);
    let qs = ModelClass.objects;
    
    // Apply static filter from attribute
    const staticFilter = this.getAttribute('filter');
    if (staticFilter) {
      qs = qs.filter(JSON.parse(staticFilter));
    }
    
    // Apply dynamic filters (from search, filter tabs, etc.)
    if (Object.keys(this._dynamicFilters).length > 0) {
      qs = qs.filter(this._dynamicFilters);
    }
    
    // Apply ordering (dynamic overrides static)
    const orderBy = this._dynamicOrderBy || this.getAttribute('order-by')?.split(',');
    if (orderBy) {
      qs = qs.order_by(...orderBy);
    }
    
    // Apply limit
    const limit = this.getAttribute('limit');
    if (limit) {
      qs = qs.limit(parseInt(limit));
    }
    
    // Request rendered templates
    qs = qs.render(template);
    
    // Fetch
    this.classList.add('loading');
    try {
      const items = await qs.all();
      
      // Render items
      this.innerHTML = items
        .map(item => item._renders[template])
        .join('');
      
      // Initialize child components
      Guitar.initComponents(this);
      
    } finally {
      this.classList.remove('loading');
    }
  }
}
```

---

## How It All Connects

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User Interaction                             │
└───────────┬───────────────────┬───────────────────┬─────────────────┘
            │                   │                   │
     Types in search      Clicks sort         Clicks filter tab
            │                   │                   │
            ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Event Listeners (vanilla JS)                     │
│   searchInput.on('input')  sortSelect.on('change')  tab.on('click') │
└───────────┬───────────────────┬───────────────────┬─────────────────┘
            │                   │                   │
            ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      <guitar-list> Element                           │
│                                                                      │
│   .setFilter('title__icontains', 'buy')                             │
│   .setOrderBy('-priority')                                          │
│   .setFilter('completed', false)                                    │
│                                                                      │
│   → Internally calls .load()                                        │
│   → Builds queryset with all filters merged                         │
│   → Fetches from API with _render=list-item                         │
│   → Renders HTML into element                                       │
│   → Initializes <todo-list-item> components                         │
└─────────────────────────────────────────────────────────────────────┘
            │
            │ User clicks a todo item
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   <todo-list-item> Component                         │
│                                                                      │
│   data-action="select" → config.actions.select()                    │
│                        → Todo.emit('selected', todo)                │
└───────────────────────────────────────────────────────────────────┘
            │
            │ Event bubbles up
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Todo.on('selected', ...)                        │
│                                                                      │
│   → Updates detail container with <todo-edit item-id="X">           │
│   → <todo-edit> fetches todo data                                   │
│   → Renders edit form with auto-save                                │
└─────────────────────────────────────────────────────────────────────┘
            │
            │ User edits a field
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      <todo-edit> Component                           │
│                                                                      │
│   [data-autosave] field changes                                     │
│   → Debounced save triggered                                        │
│   → Todo.objects.filter({id}).update({...})                         │
│   → Backend returns updated todo with _renders                      │
│   → GuitarRegistry.set('todo', id, data)                            │
│   → Todo.emit('updated', todo)                                      │
└─────────────────────────────────────────────────────────────────────┘
            │
            │ Event propagates
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│            All <todo-list-item> Components Listen                    │
│                                                                      │
│   subscribe.updated → if my todo, re-render with new HTML          │
│                                                                      │
│   The list item in the sidebar updates automatically!               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Summary: The Custom Element Approach

### Why Custom Elements?

| Benefit | Explanation |
|---------|-------------|
| **Framework agnostic** | Works in React, Vue, Svelte, vanilla, anything |
| **Native browser API** | No library needed, fast, standards-based |
| **Encapsulated** | Styles, behavior, template all bundled |
| **Composable** | Use like any HTML element |
| **Auto-generated** | Create template file → get custom element |

### What We Generate

| File | Creates |
|------|---------|
| `templates/chart/card.html` | `<chart-card>` element |
| `templates/chart/edit.html` | `<chart-edit>` element |
| `templates/todo/list-item.html` | `<todo-list-item>` element |

### Built-in Generic Elements

| Element | Purpose |
|---------|---------|
| `<guitar-list>` | Display list of items with filtering/sorting |
| `<guitar-detail>` | Display single item (read-only) |
| `<guitar-edit>` | Edit form with auto-save |

### The Wiring Pattern

```javascript
// 1. Get reference to guitar-list
const list = document.querySelector('guitar-list');

// 2. Wire up controls
searchInput.on('input', () => list.setFilter('field', value));
sortSelect.on('change', () => list.setOrderBy(value));
filterTab.on('click', () => list.setFilter('status', value));

// 3. Wire up selection
Model.on('selected', (item) => {
  detailContainer.innerHTML = `<model-edit item-id="${item.id}"></model-edit>`;
});

// 4. Everything else is automatic via events
// - Updates propagate via GuitarRegistry
// - All instances of an item stay in sync
// - No manual DOM manipulation needed
```

This is **Django-like in spirit**: declarative, convention-over-configuration, minimal boilerplate.
