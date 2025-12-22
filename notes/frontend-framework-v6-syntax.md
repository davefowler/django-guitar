# Guitar Frontend - v6: Cleaner Syntax

## Vue's `:` vs `@` Syntax

In Vue:

| Syntax | Meaning | Direction |
|--------|---------|-----------|
| `:value="x"` | Bind attribute FROM state | State → Element |
| `@click="fn"` | Listen for event | Element → Handler |
| `v-model="x"` | Two-way binding | Both ↔ |

So:
- `:` = data binding (one-way down)
- `@` = event binding (one-way up)
- `v-model` = two-way

## Guitar's Approach: Same Pattern

```html
<!-- One-way: state → element -->
<input :value="searchTerm">
<div :class="{ active: isActive }">
<span :text="selectedTodo.title">

<!-- Event: element → handler -->
<button @click="handleClick">
<input @input="handleInput">
<form @submit="handleSubmit">

<!-- Two-way: both -->
<input :model="searchTerm">
```

### The `:model` Shorthand

```html
<!-- These are equivalent -->
<input :model="searchTerm">

<input 
  :value="searchTerm" 
  @input="searchTerm = $event.target.value"
>
```

### With Modifiers

```html
<!-- Debounce -->
<input :model.debounce.300="searchTerm">

<!-- Lazy (on blur, not input) -->
<input :model.lazy="searchTerm">

<!-- Number coercion -->
<input type="number" :model.number="count">
```

---

## Element deps Attribute

### The Idea

The element declares what state it depends on. When those change, it re-fetches.

```html
<todo-list 
  deps="searchTerm, sortOrder, filterCompleted"
></todo-list>
```

### How the Queryset Uses Deps

```typescript
// When registering the element
Guitar.registerElement('todo-list', {
  extends: 'guitar-list',
  model: 'todo',
  template: 'list-item',
  
  // Queryset receives deps as an object
  queryset: ({ searchTerm, sortOrder, filterCompleted }) => {
    let qs = Todo.objects;
    
    if (searchTerm) {
      qs = qs.filter({ title__icontains: searchTerm });
    }
    
    if (filterCompleted !== null) {
      qs = qs.filter({ completed: filterCompleted });
    }
    
    return qs.order_by(sortOrder || '-created_at');
  },
});
```

### Usage

```html
<!-- Declare deps, queryset auto-updates when they change -->
<todo-list deps="searchTerm, sortOrder, filterCompleted"></todo-list>

<!-- Or override deps per-instance -->
<todo-list deps="searchTerm"></todo-list>  <!-- Only reacts to search -->
```

### Implementation

```typescript
class GuitarListElement extends HTMLElement {
  private _unsubscribers: (() => void)[] = [];
  
  connectedCallback() {
    this.setupDeps();
    this.load();
  }
  
  disconnectedCallback() {
    // Cleanup subscriptions
    this._unsubscribers.forEach(fn => fn());
  }
  
  setupDeps() {
    const depsAttr = this.getAttribute('deps');
    if (!depsAttr) return;
    
    const deps = depsAttr.split(',').map(d => d.trim());
    
    deps.forEach(depName => {
      const stateVar = Guitar.state[depName];
      if (stateVar) {
        // Subscribe to changes
        const unsub = stateVar.subscribe(() => {
          this.load();  // Re-fetch when dep changes
        });
        this._unsubscribers.push(unsub);
      }
    });
  }
  
  async load() {
    // Gather current dep values
    const depsAttr = this.getAttribute('deps');
    const depValues: Record<string, any> = {};
    
    if (depsAttr) {
      depsAttr.split(',').forEach(depName => {
        const name = depName.trim();
        depValues[name] = Guitar.state[name]?.get();
      });
    }
    
    // Call queryset with dep values
    const options = (this.constructor as any).options;
    const qs = options.queryset(depValues);
    
    // Fetch and render
    const items = await qs.render(this.template).all();
    this.renderItems(items);
  }
}
```

---

## Even Simpler: Auto-Detect Deps

What if we auto-detect which state vars the queryset uses?

```typescript
Guitar.registerElement('todo-list', {
  extends: 'guitar-list',
  
  // Just write the queryset naturally
  queryset: () => {
    let qs = Todo.objects;
    
    // These accesses are tracked!
    if (state.searchTerm) {
      qs = qs.filter({ title__icontains: state.searchTerm });
    }
    
    if (state.filterCompleted !== null) {
      qs = qs.filter({ completed: state.filterCompleted });
    }
    
    return qs.order_by(state.sortOrder);
  },
  
  // No deps needed - auto-tracked!
});
```

```html
<!-- No deps attribute needed -->
<todo-list></todo-list>
```

### How Auto-Tracking Works

Similar to Vue's reactivity or MobX:

```typescript
// Wrap state access to track reads
const trackingState = new Proxy(state, {
  get(target, prop) {
    // Record that this prop was accessed
    currentTracker?.add(prop);
    return target[prop].get();
  }
});

// When running queryset, track accesses
const runWithTracking = (fn: () => any) => {
  const accessed = new Set<string>();
  currentTracker = accessed;
  
  const result = fn();
  
  currentTracker = null;
  return { result, deps: accessed };
};

// In element
class GuitarListElement {
  setupReactivity() {
    // Run queryset once to discover deps
    const { result, deps } = runWithTracking(() => 
      this.options.queryset()
    );
    
    // Subscribe to discovered deps
    deps.forEach(depName => {
      Guitar.state[depName].subscribe(() => this.load());
    });
  }
}
```

---

## Complete Syntax Reference

### Binding Syntax

| Syntax | Meaning | Example |
|--------|---------|---------|
| `:prop="expr"` | Bind property from state | `:value="searchTerm"` |
| `:model="var"` | Two-way binding | `:model="searchTerm"` |
| `:model.debounce.300` | With debounce | `:model.debounce.300="search"` |
| `:class="{ name: cond }"` | Conditional class | `:class="{ active: isActive }"` |
| `:show="cond"` | Toggle visibility | `:show="selectedId !== null"` |
| `:text="expr"` | Set text content | `:text="todo.title"` |
| `:html="expr"` | Set inner HTML | `:html="todo.description"` |

### Event Syntax

| Syntax | Meaning | Example |
|--------|---------|---------|
| `@event="action"` | Call named action | `@click="handleSave"` |
| `@event="state.x = y"` | Simple state assignment | `@click="selectedId = todo.id"` |
| `@event.modifier` | With modifier | `@click.prevent="save"` |
| `@submit.prevent` | Prevent default | `@submit.prevent="save"` |
| `@input.debounce.300` | Debounced | `@input.debounce.300="search"` |

### Element Attributes

| Attribute | Meaning | Example |
|-----------|---------|---------|
| `deps="a, b, c"` | State dependencies | `deps="searchTerm, sortOrder"` |
| `:queryset="expr"` | Bind queryset from state | `:queryset="todosQuery"` |
| `model="name"` | Model name | `model="todo"` |
| `template="name"` | Template name | `template="list-item"` |

---

## Full Example with Clean Syntax

### State

```typescript
// state.ts
export const state = defineState({
  searchTerm: { default: '', debounce: 300 },
  sortOrder: { default: '-created_at' },
  filterCompleted: { default: null },
  selectedTodoId: { default: null },
});
```

### Element

```typescript
// elements/todo-list.ts
Guitar.registerElement('todo-list', {
  extends: 'guitar-list',
  model: 'todo',
  template: 'list-item',
  
  // Deps are auto-tracked from state access
  queryset: () => {
    let qs = Todo.objects;
    
    if (state.searchTerm) {
      qs = qs.filter({ title__icontains: state.searchTerm });
    }
    
    if (state.filterCompleted !== null) {
      qs = qs.filter({ completed: state.filterCompleted });
    }
    
    return qs.order_by(state.sortOrder);
  },
});
```

### HTML

```html
<div class="todo-app">
  <aside>
    <h1>Todos</h1>
    
    <!-- Two-way binding with debounce -->
    <input 
      type="search" 
      placeholder="Search..."
      :model.debounce.300="searchTerm"
    >
    
    <!-- Two-way binding to select -->
    <select :model="sortOrder">
      <option value="-created_at">Newest</option>
      <option value="-priority">Priority</option>
      <option value="due_date">Due Date</option>
    </select>
    
    <!-- Filter buttons -->
    <nav>
      <button 
        @click="filterCompleted = null"
        :class="{ active: filterCompleted === null }"
      >All</button>
      
      <button 
        @click="filterCompleted = false"
        :class="{ active: filterCompleted === false }"
      >Active</button>
      
      <button 
        @click="filterCompleted = true"
        :class="{ active: filterCompleted === true }"
      >Done</button>
    </nav>
    
    <!-- List auto-updates when state changes (deps auto-tracked) -->
    <todo-list></todo-list>
    
    <!-- Quick add -->
    <form @submit.prevent="createTodo">
      <input type="text" name="title" placeholder="Add todo...">
      <button type="submit">Add</button>
    </form>
  </aside>
  
  <main>
    <!-- Show edit when selected -->
    <todo-edit 
      :show="selectedTodoId"
      :item-id="selectedTodoId"
    ></todo-edit>
    
    <!-- Empty state -->
    <div :show="!selectedTodoId" class="empty">
      Select a todo to edit
    </div>
  </main>
</div>
```

### Template

```html
<!-- templates/todo/list-item.html -->
<li 
  :class="{ 
    completed: todo.completed,
    selected: selectedTodoId === todo.id 
  }"
>
  <input 
    type="checkbox"
    :checked="todo.completed"
    @change="toggleComplete"
  >
  
  <span @click="selectedTodoId = todo.id">
    {{ todo.title }}
  </span>
  
  <button @click="deleteTodo" @confirm="Delete?">×</button>
</li>
```

---

## Summary

| Feature | Syntax |
|---------|--------|
| One-way binding (state → element) | `:value="x"` |
| Two-way binding | `:model="x"` |
| Event handler | `@click="action"` |
| State assignment | `@click="x = y"` |
| Debounce | `:model.debounce.300` or `@input.debounce.300` |
| Conditional class | `:class="{ active: cond }"` |
| Show/hide | `:show="cond"` |
| Element dependencies | `deps="a, b"` or auto-tracked |

This is Vue-inspired but simpler - just the essentials for Guitar's use case.
