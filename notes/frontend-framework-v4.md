# Guitar Frontend Framework - v4 Refinements

Addressing key questions about rendering, naming, inheritance, templates, and declarative patterns.

---

## 1. Server-Side Rendering: Still Needed?

### Short Answer: Optional, for specific cases

With Custom Elements as the core, **client-side rendering is the default**. But SSR still has value for:

| Use Case | SSR Useful? |
|----------|-------------|
| Initial page load (SEO, performance) | ✅ Yes |
| Email templates | ✅ Yes |
| PDF generation | ✅ Yes |
| Live updates after interaction | ❌ No (client-side) |
| Real-time editing | ❌ No (client-side) |

### Recommendation

- **Default**: Client-side rendering via JS template engine
- **Optional**: Request SSR via `?_ssr=true` for initial page load
- **Progressive enhancement**: Server renders initial HTML, JS hydrates for interactivity

```html
<!-- Initial load: server-rendered -->
<guitar-list model="todo" template="list-item" ssr>
  <!-- Server pre-renders this content -->
  <todo-list-item item-id="1">...</todo-list-item>
  <todo-list-item item-id="2">...</todo-list-item>
</guitar-list>

<!-- On interaction, client takes over -->
```

---

## 2. Naming: "Config" vs Something Better

### Options

| Name | Feel |
|------|------|
| `config` | Generic, unclear |
| `behavior` | Describes what it does ✓ |
| `controller` | MVC-ish, familiar to backend devs ✓ |
| `handler` | Event-focused |
| `component` | Conflicts with the element itself |
| `definition` | Too abstract |

### Recommendation: `behavior`

```typescript
// guitar/templates/chart/card.behavior.ts  (or just card.ts)
import type { ElementBehavior } from '@guitar/core';

const behavior: ElementBehavior<Chart> = {
  onSuccess: (chart) => { ... },
  onError: (error) => { ... },
  actions: { ... },
  on: { ... },
};

export default behavior;
```

Or even simpler - just export what you need:

```typescript
// guitar/templates/chart/card.ts
export const actions = {
  edit: (chart) => Guitar.navigate(`/charts/${chart.id}/edit`),
  delete: async (chart) => { ... },
};

export const onSuccess = (chart) => {
  Guitar.toast(`Updated "${chart.name}"`);
};

export const on = {
  click: (chart) => Chart.emit('selected', chart),
};
```

---

## 3. CSS: Style the Element Directly

You're absolutely right! Custom elements ARE HTML elements, so style them directly:

```css
/* guitar/templates/chart/card.css */

/* Style the custom element itself */
chart-card {
  display: block;  /* Custom elements are inline by default */
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  padding: 16px;
  transition: box-shadow 0.2s;
}

chart-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

chart-card.selected {
  outline: 2px solid var(--primary-color);
}

chart-card.loading {
  opacity: 0.5;
}

/* Internal elements use classes */
chart-card .title {
  font-size: 1.2em;
  margin: 0;
}

chart-card .actions {
  display: flex;
  gap: 8px;
}
```

---

## 4. registerElement with Inheritance

Yes! Much better than separate `registerConfig`. Inherit from any element:

```typescript
// Create element that extends guitar-edit with custom behavior
Guitar.registerElement('todo-quick-edit', {
  extends: 'guitar-edit',  // Inherit from guitar-edit
  
  model: 'todo',
  fields: ['title', 'completed'],
  autoSave: true,
  autoSaveDelay: 500,
  
  onSuccess: (todo) => {
    Guitar.toast('Saved!');
  },
});

// Create element that extends another custom element
Guitar.registerElement('todo-priority-edit', {
  extends: 'todo-quick-edit',  // Inherit from todo-quick-edit
  
  fields: ['title', 'completed', 'priority'],  // Override fields
});
```

### Usage

```html
<todo-quick-edit item-id="123"></todo-quick-edit>
<todo-priority-edit item-id="123"></todo-priority-edit>
```

### Implementation

```typescript
// guitar/core/register.ts

Guitar.registerElement = (tagName: string, options: ElementOptions) => {
  // Get parent class
  let ParentClass: typeof HTMLElement;
  
  if (options.extends) {
    // Check if it's a built-in guitar element
    if (options.extends.startsWith('guitar-')) {
      ParentClass = customElements.get(options.extends);
    } else {
      // It's a user-defined element
      ParentClass = customElements.get(options.extends);
    }
    
    if (!ParentClass) {
      throw new Error(`Cannot extend "${options.extends}" - element not defined`);
    }
  } else {
    // Default parent
    ParentClass = GuitarElement;
  }
  
  // Create new class extending parent
  class NewElement extends ParentClass {
    static options = { ...ParentClass.options, ...options };
    
    // Override methods as needed
    get model() {
      return options.model || super.model;
    }
    
    get fields() {
      return options.fields || super.fields;
    }
    
    // etc.
  }
  
  // Register the element
  customElements.define(tagName, NewElement);
  
  return NewElement;
};
```

### No More registerConfig

Now everything is `registerElement`:

```typescript
// Before (confusing)
Guitar.registerConfig('todo-inline', { ... });  // Not an element
Guitar.registerElement('todo-editor', { ... }); // Is an element

// After (simple)
Guitar.registerElement('todo-inline-editor', { 
  extends: 'guitar-edit',
  ...
});
```

---

## 5. Queryset as Function / Property

### Option A: Set on Element Class

```typescript
// Define element with queryset
Guitar.registerElement('active-todos-list', {
  extends: 'guitar-list',
  model: 'todo',
  template: 'list-item',
  
  // Queryset as a function
  queryset: () => {
    return Todo.objects
      .filter({ completed: false })
      .exclude({ archived: true })
      .order_by('-priority', '-created_at');
  },
});
```

```html
<!-- Just use it - queryset is built-in -->
<active-todos-list></active-todos-list>
```

### Option B: Set as Property After Definition

```typescript
// Get the element class
const ActiveTodosList = Guitar.registerElement('active-todos-list', {
  extends: 'guitar-list',
  model: 'todo',
  template: 'list-item',
});

// Set queryset on the class (affects all instances)
ActiveTodosList.queryset = () => {
  return Todo.objects
    .filter({ completed: false })
    .order_by('-priority');
};
```

### Option C: Set on Instance

```html
<guitar-list id="my-list" model="todo" template="list-item"></guitar-list>

<script>
  const list = document.getElementById('my-list');
  
  // Set queryset on this specific instance
  list.queryset = () => {
    return Todo.objects
      .filter({ user_id: currentUser.id })
      .order_by('-created_at');
  };
</script>
```

### Option D: Queryset in Behavior File

```typescript
// guitar/templates/todo/active-list.ts
export const queryset = () => {
  return Todo.objects
    .filter({ completed: false })
    .order_by('-priority', '-created_at');
};
```

```html
<!-- Auto-created from template, queryset included -->
<todo-active-list></todo-active-list>
```

---

## 6. Does the Todo App Need Custom Templates?

### Maybe Not! Generic Views Might Suffice

If `<guitar-list>` and `<guitar-edit>` are configurable enough:

```html
<guitar-list 
  model="todo"
  fields="completed,title,priority,due_date"
  display="table"
  editable="completed"
  on-click="select"
></guitar-list>

<guitar-edit
  model="todo"
  fields="title,priority,due_date,notes"
  auto-save
></guitar-edit>
```

### But Custom Templates Give You

1. **Custom HTML structure** - Not just a table or form
2. **Custom styling** - Exactly the look you want
3. **Custom interactions** - Drag-drop, swipe, etc.
4. **Branding** - Your app's unique feel

### Recommendation

- **Start with generic views** for rapid prototyping
- **Create custom templates** when you need custom UX

```html
<!-- Quick prototype -->
<guitar-list model="todo" display="cards"></guitar-list>

<!-- Production with custom design -->
<todo-list></todo-list>  <!-- Uses custom template -->
```

---

## 7. Templates: Django in JS with Event Binding

### The Vision

One template syntax that works:
1. On the server (Django)
2. On the client (JS)
3. With event binding (like React's onClick)

### How It Could Work

```html
<!-- guitar/templates/todo/list-item.html -->
<li class="todo-item {{ 'completed' if todo.completed }}">
  <input 
    type="checkbox"
    {{ 'checked' if todo.completed }}
    @change="toggleComplete"
  >
  
  <span class="title" @click="select" @dblclick="editInline">
    {{ todo.title }}
  </span>
  
  <button @click="delete" @confirm="Delete this todo?">
    Delete
  </button>
</li>
```

### The @ Syntax for Events

Inspired by Vue, but simpler:

| Attribute | Meaning |
|-----------|---------|
| `@click="actionName"` | Call action on click |
| `@change="actionName"` | Call action on change |
| `@dblclick="actionName"` | Call action on double-click |
| `@confirm="message"` | Show confirm dialog first |
| `@debounce="300"` | Debounce the event |

### JS Template Engine

Use Nunjucks (Django-compatible) + custom event binding:

```typescript
// guitar/core/template-engine.ts
import nunjucks from 'nunjucks';

// Parse template and extract event bindings
export const renderTemplate = (
  templateString: string,
  context: Record<string, any>,
  actions: Record<string, Function>
): { html: string; bindings: EventBinding[] } => {
  
  // Find all @event="action" patterns
  const bindings: EventBinding[] = [];
  let bindingId = 0;
  
  const processedTemplate = templateString.replace(
    /@(\w+)="([^"]+)"/g,
    (match, event, action) => {
      const id = `guitar-bind-${bindingId++}`;
      bindings.push({ id, event, action });
      return `data-guitar-${event}="${action}" data-guitar-bind="${id}"`;
    }
  );
  
  // Render with Nunjucks
  const html = nunjucks.renderString(processedTemplate, context);
  
  return { html, bindings };
};

// After inserting HTML, bind events
export const bindEvents = (
  container: Element,
  data: any,
  actions: Record<string, Function>
): void => {
  container.querySelectorAll('[data-guitar-bind]').forEach(el => {
    const events = ['click', 'change', 'dblclick', 'input', 'submit'];
    
    events.forEach(event => {
      const action = el.getAttribute(`data-guitar-${event}`);
      if (!action) return;
      
      const confirm = el.getAttribute('data-guitar-confirm');
      const debounce = parseInt(el.getAttribute('data-guitar-debounce') || '0');
      
      let handler = (e: Event) => {
        if (confirm && !window.confirm(confirm)) return;
        actions[action]?.(data, el, e);
      };
      
      if (debounce > 0) {
        handler = debounceHandler(handler, debounce);
      }
      
      el.addEventListener(event, handler);
    });
  });
};
```

### Full Example

```html
<!-- guitar/templates/todo/list-item.html -->
<li class="todo-item {{ 'completed' if todo.completed }}">
  <input 
    type="checkbox"
    {{ 'checked' if todo.completed }}
    @change="toggle"
  >
  
  <span 
    class="title" 
    @click="select"
  >
    {{ todo.title }}
  </span>
  
  <span class="priority badge-{{ todo.priority }}">
    {{ todo.priority }}
  </span>
  
  <button 
    class="delete-btn"
    @click="delete"
    @confirm="Delete '{{ todo.title }}'?"
  >
    ×
  </button>
</li>
```

```typescript
// guitar/templates/todo/list-item.ts
export const actions = {
  toggle: async (todo, el, event) => {
    const checkbox = event.target as HTMLInputElement;
    await Todo.objects.filter({ id: todo.id }).update({
      completed: checkbox.checked
    });
  },
  
  select: (todo) => {
    Todo.emit('selected', todo);
  },
  
  delete: async (todo) => {
    await Todo.objects.filter({ id: todo.id }).delete();
  },
};
```

### Server Compatibility

The same template works on the server! Django just ignores `@event` attributes:

```python
# Django renders this fine - @ attributes are just passed through
rendered = render_to_string('guitar/todo/list-item.html', {'todo': todo})
# Output: <li class="todo-item"><input type="checkbox" @change="toggle">...
```

When the HTML reaches the browser, Guitar's JS binds the events.

---

## 8. More Declarative Wiring

### The Problem

This is imperative:

```javascript
sortSelect.addEventListener('change', () => {
  guitarList.setOrderBy(sortSelect.value);
});
```

### Solution: Declarative Attributes

```html
<!-- Sort control declares what it controls -->
<select 
  data-guitar-controls="#todo-list"
  data-guitar-order-by
>
  <option value="-created_at">Newest</option>
  <option value="-priority">Priority</option>
</select>

<!-- Search declares what it controls -->
<input 
  type="search"
  data-guitar-controls="#todo-list"
  data-guitar-filter="title__icontains"
  data-guitar-debounce="300"
>

<!-- Filter buttons -->
<button 
  data-guitar-controls="#todo-list"
  data-guitar-filter='{"completed": false}'
>
  Active
</button>

<!-- The list just exists -->
<guitar-list id="todo-list" model="todo" template="list-item"></guitar-list>
```

### Auto-Wiring

Guitar automatically wires these up on init:

```typescript
// guitar/core/auto-wire.ts

Guitar.init = () => {
  // Wire up all controls
  document.querySelectorAll('[data-guitar-controls]').forEach(control => {
    const targetSelector = control.getAttribute('data-guitar-controls');
    const target = document.querySelector(targetSelector) as GuitarListElement;
    
    if (!target) return;
    
    // Order-by control
    if (control.hasAttribute('data-guitar-order-by')) {
      control.addEventListener('change', () => {
        target.setOrderBy((control as HTMLSelectElement).value);
      });
    }
    
    // Filter control (input)
    const filterField = control.getAttribute('data-guitar-filter');
    if (filterField && control instanceof HTMLInputElement) {
      const debounce = parseInt(control.getAttribute('data-guitar-debounce') || '0');
      
      let timer: number;
      control.addEventListener('input', () => {
        clearTimeout(timer);
        timer = window.setTimeout(() => {
          target.setFilter(filterField, control.value || null);
        }, debounce);
      });
    }
    
    // Filter control (button)
    if (filterField && control instanceof HTMLButtonElement) {
      control.addEventListener('click', () => {
        const filter = JSON.parse(filterField);
        target.replaceFilters(filter);
        
        // Update active state in button group
        control.parentElement?.querySelectorAll('[data-guitar-filter]').forEach(btn => {
          btn.classList.toggle('active', btn === control);
        });
      });
    }
  });
};
```

### Now the Wiring is Zero JS

```html
<div class="todo-app">
  <!-- Controls - auto-wired -->
  <input 
    type="search"
    data-guitar-controls="#todo-list"
    data-guitar-filter="title__icontains"
    data-guitar-debounce="300"
    placeholder="Search..."
  >
  
  <select data-guitar-controls="#todo-list" data-guitar-order-by>
    <option value="-created_at">Newest</option>
    <option value="-priority">Priority</option>
  </select>
  
  <nav>
    <button data-guitar-controls="#todo-list" data-guitar-filter='{}' class="active">All</button>
    <button data-guitar-controls="#todo-list" data-guitar-filter='{"completed": false}'>Active</button>
    <button data-guitar-controls="#todo-list" data-guitar-filter='{"completed": true}'>Done</button>
  </nav>
  
  <!-- List - just exists -->
  <guitar-list id="todo-list" model="todo" template="list-item"></guitar-list>
</div>

<script>
  Guitar.init();  // That's it!
</script>
```

---

## 9. Reactive Selection

### The Problem

This is imperative:

```javascript
Todo.on('selected', (todo) => {
  detailContainer.innerHTML = `<todo-edit item-id="${todo.id}"></todo-edit>`;
});
```

### Solution: Reactive Containers

```html
<!-- This container reacts to Todo selection -->
<div 
  data-guitar-react-to="todo:selected"
  data-guitar-render="todo-edit"
>
  <!-- Empty state shown when nothing selected -->
  <div class="empty-state">Select a todo</div>
</div>
```

When `Todo.emit('selected', todo)` fires, the container automatically:
1. Clears its content
2. Renders `<todo-edit item-id="${todo.id}">`

### More Reactive Patterns

```html
<!-- Show detail when selected -->
<div 
  data-guitar-react-to="chart:selected"
  data-guitar-render="chart-detail"
>
</div>

<!-- Show edit form when edit event fires -->
<div 
  data-guitar-react-to="todo:edit"
  data-guitar-render="todo-edit"
>
</div>

<!-- Clear when deleted -->
<div 
  data-guitar-react-to="todo:deleted"
  data-guitar-clear
>
</div>

<!-- Multiple reactions -->
<div 
  data-guitar-react-to="todo:selected todo:updated"
  data-guitar-render="todo-detail"
>
</div>
```

### Implementation

```typescript
// guitar/core/reactive.ts

Guitar.initReactive = () => {
  document.querySelectorAll('[data-guitar-react-to]').forEach(container => {
    const reactions = container.getAttribute('data-guitar-react-to').split(' ');
    
    reactions.forEach(reaction => {
      const [model, event] = reaction.split(':');
      const ModelClass = Guitar.getModel(model);
      
      ModelClass.on(event, (item) => {
        const render = container.getAttribute('data-guitar-render');
        const clear = container.hasAttribute('data-guitar-clear');
        
        if (clear) {
          container.innerHTML = '';
          return;
        }
        
        if (render && item) {
          container.innerHTML = `<${render} item-id="${item.id}"></${render}>`;
          Guitar.initComponents(container);
        }
      });
    });
  });
};
```

---

## 10. Complete Todo App - Fully Declarative

Almost zero JavaScript needed:

```html
<!DOCTYPE html>
<html>
<head>
  <title>Guitar Todos</title>
  <link rel="stylesheet" href="/static/styles.css">
  <script type="module" src="/static/guitar/guitar.js"></script>
</head>
<body>
  <div class="todo-app">
    <aside class="sidebar">
      <h1>My Todos</h1>
      
      <!-- Search - auto-wired -->
      <input 
        type="search"
        placeholder="Search..."
        data-guitar-controls="#todo-list"
        data-guitar-filter="title__icontains"
        data-guitar-debounce="300"
      >
      
      <!-- Sort - auto-wired -->
      <select data-guitar-controls="#todo-list" data-guitar-order-by>
        <option value="-created_at">Newest</option>
        <option value="-priority">Priority</option>
        <option value="due_date">Due Date</option>
      </select>
      
      <!-- Filter tabs - auto-wired -->
      <nav class="filter-tabs">
        <button data-guitar-controls="#todo-list" data-guitar-filter="{}" class="active">
          All
        </button>
        <button data-guitar-controls="#todo-list" data-guitar-filter='{"completed": false}'>
          Active
        </button>
        <button data-guitar-controls="#todo-list" data-guitar-filter='{"completed": true}'>
          Done
        </button>
      </nav>
      
      <!-- Todo list -->
      <guitar-list 
        id="todo-list" 
        model="todo" 
        template="list-item"
        order-by="-created_at"
      ></guitar-list>
      
      <!-- Quick add - auto-wired -->
      <form data-guitar-create="todo" data-guitar-refresh="#todo-list">
        <input type="text" name="title" placeholder="Add todo..." required>
        <button type="submit">Add</button>
      </form>
    </aside>
    
    <main>
      <!-- Reactive detail panel -->
      <div 
        data-guitar-react-to="todo:selected"
        data-guitar-render="todo-edit"
        class="detail-panel"
      >
        <div class="empty-state">
          <p>Select a todo to edit</p>
        </div>
      </div>
    </main>
  </div>
  
  <script>
    import { Guitar } from '/static/guitar/guitar.js';
    Guitar.init();  // That's ALL the JS!
  </script>
</body>
</html>
```

### Template: list-item.html

```html
<!-- guitar/templates/todo/list-item.html -->
<li class="todo-item {{ 'completed' if todo.completed }}">
  <input 
    type="checkbox"
    {{ 'checked' if todo.completed }}
    @change="toggle"
  >
  
  <span class="title" @click="select">
    {{ todo.title }}
  </span>
  
  <span class="priority badge-{{ todo.priority }}">
    {{ todo.priority }}
  </span>
  
  <button @click="delete" @confirm="Delete?">×</button>
</li>
```

```typescript
// guitar/templates/todo/list-item.ts
export const actions = {
  toggle: async (todo, el, e) => {
    await Todo.objects.filter({ id: todo.id }).update({
      completed: e.target.checked
    });
  },
  
  select: (todo) => Todo.emit('selected', todo),
  
  delete: async (todo) => {
    await Todo.objects.filter({ id: todo.id }).delete();
  },
};
```

### What We Achieved

| Feature | JavaScript Required? |
|---------|---------------------|
| List with filters | ❌ No |
| Search with debounce | ❌ No |
| Sort dropdown | ❌ No |
| Filter tabs | ❌ No |
| Quick add form | ❌ No |
| Selection → detail view | ❌ No |
| Toggle checkbox | Minimal (action handler) |
| Delete with confirm | Minimal (action handler) |
| Auto-save on edit | ❌ No (built into guitar-edit) |

**Total custom JS: ~15 lines** (just the action handlers)

---

## Summary: The Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        HTML Template                              │
│  Django/Nunjucks syntax + @event bindings                        │
│  todo/list-item.html                                             │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                     Behavior File (optional)                      │
│  Actions, event handlers, lifecycle hooks                        │
│  todo/list-item.ts                                               │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                      Custom Element                               │
│  Auto-generated: <todo-list-item>                                │
│  Or generic: <guitar-list>, <guitar-edit>                        │
└───────────────────────────────┬──────────────────────────────────┘
                                │
              Works in React, Vue, Svelte, vanilla
                                │
┌───────────────────────────────┴──────────────────────────────────┐
│                    Declarative Wiring                             │
│  data-guitar-controls, data-guitar-react-to                      │
│  No JS required for most interactions                            │
└──────────────────────────────────────────────────────────────────┘
```

### Key Decisions

| Question | Answer |
|----------|--------|
| SSR needed? | Optional, for initial load / SEO |
| What to call the .ts file? | `behavior` or just export what you need |
| CSS selectors? | Style element directly: `chart-card { }` |
| registerConfig? | No, just `registerElement` with `extends` |
| Queryset as function? | Yes, set on element class or instance |
| Need custom templates? | No for prototyping, yes for custom UX |
| Template syntax? | Django/Nunjucks + `@event` bindings |
| Wiring controls? | Declarative `data-guitar-controls` |
| Reactive containers? | `data-guitar-react-to` |

This is **truly Django-like**: declarative, convention-over-configuration, minimal code.
