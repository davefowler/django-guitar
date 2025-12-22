# Guitar Frontend Framework - v5: State & Reactivity

The insight: `search_term` and `Todo` objects are both just **state**. One syncs to backend, one doesn't. Let's unify them.

---

## The Unified State Model

### Two Types of State, Same API

```typescript
// Backend-synced state (model objects)
Guitar.state.todos = Todo.objects.filter({ user_id: currentUser.id });

// Frontend-only state (UI state)
Guitar.state.searchTerm = '';
Guitar.state.selectedTodoId = null;
Guitar.state.sortOrder = '-created_at';
Guitar.state.filterCompleted = null;  // null = all, true = done, false = active
```

### State Declaration

```typescript
// guitar/state.ts - Define your app's state
import { defineState } from '@guitar/core';

export const state = defineState({
  // Frontend-only state
  searchTerm: {
    default: '',
    debounce: 300,
  },
  
  selectedTodoId: {
    default: null,
  },
  
  sortOrder: {
    default: '-created_at',
  },
  
  filterCompleted: {
    default: null,  // null = all
  },
  
  // Derived/computed state
  activeTodos: {
    derive: (state) => {
      let qs = Todo.objects;
      
      if (state.searchTerm) {
        qs = qs.filter({ title__icontains: state.searchTerm });
      }
      
      if (state.filterCompleted !== null) {
        qs = qs.filter({ completed: state.filterCompleted });
      }
      
      return qs.order_by(state.sortOrder);
    },
    // Re-derive when these change
    deps: ['searchTerm', 'filterCompleted', 'sortOrder'],
  },
  
  selectedTodo: {
    derive: (state) => {
      if (!state.selectedTodoId) return null;
      return Guitar.registry.get('todo', state.selectedTodoId);
    },
    deps: ['selectedTodoId'],
  },
});
```

---

## Binding State to Inputs

### Option A: @state attribute

```html
<!-- Input binds to state.searchTerm -->
<input 
  type="search"
  placeholder="Search..."
  @state="searchTerm"
>

<!-- Select binds to state.sortOrder -->
<select @state="sortOrder">
  <option value="-created_at">Newest</option>
  <option value="-priority">Priority</option>
</select>

<!-- Buttons set state.filterCompleted -->
<nav>
  <button @state:set="filterCompleted = null" @state:class.active="filterCompleted === null">
    All
  </button>
  <button @state:set="filterCompleted = false" @state:class.active="filterCompleted === false">
    Active
  </button>
  <button @state:set="filterCompleted = true" @state:class.active="filterCompleted === true">
    Done
  </button>
</nav>
```

### Option B: Vue-style v-model (but simpler)

```html
<input type="search" :state="searchTerm">
<select :state="sortOrder">...</select>
<button @click="state.filterCompleted = null">All</button>
```

### Option C: Explicit two-way binding

```html
<input 
  type="search"
  :value="state.searchTerm"
  @input="state.searchTerm = this.value"
>
```

### Recommendation: @state for simple, explicit for complex

```html
<!-- Simple binding -->
<input @state="searchTerm">

<!-- With options -->
<input @state="searchTerm" @state:debounce="300">

<!-- Complex/conditional -->
<input 
  :value="state.searchTerm"
  @input="handleSearch"
>
```

---

## Queryset Reacting to State

### The Queryset Uses State Variables

```typescript
Guitar.registerElement('todo-list', {
  extends: 'guitar-list',
  
  // Queryset is a function that receives state
  queryset: (state) => {
    let qs = Todo.objects;
    
    if (state.searchTerm) {
      qs = qs.filter({ title__icontains: state.searchTerm });
    }
    
    if (state.filterCompleted !== null) {
      qs = qs.filter({ completed: state.filterCompleted });
    }
    
    return qs.order_by(state.sortOrder);
  },
  
  // Declare which state vars trigger re-fetch
  watches: ['searchTerm', 'filterCompleted', 'sortOrder'],
});
```

### Or Use Derived State

```typescript
// In state definition
activeTodos: {
  derive: (state) => {
    return Todo.objects
      .filter({ 
        title__icontains: state.searchTerm || undefined,
        completed: state.filterCompleted,
      })
      .order_by(state.sortOrder);
  },
  deps: ['searchTerm', 'filterCompleted', 'sortOrder'],
},
```

```html
<!-- List just uses the derived queryset -->
<guitar-list :queryset="state.activeTodos" template="list-item"></guitar-list>
```

---

## How Different Frameworks Do This

### Vue

```vue
<template>
  <input v-model="searchTerm">
  <TodoList :todos="filteredTodos" />
</template>

<script setup>
import { ref, computed } from 'vue';

const searchTerm = ref('');
const filteredTodos = computed(() => 
  todos.filter(t => t.title.includes(searchTerm.value))
);
</script>
```

### Svelte

```svelte
<script>
  let searchTerm = '';
  $: filteredTodos = todos.filter(t => t.title.includes(searchTerm));
</script>

<input bind:value={searchTerm}>
<TodoList todos={filteredTodos} />
```

### Solid

```jsx
const [searchTerm, setSearchTerm] = createSignal('');
const filteredTodos = createMemo(() => 
  todos().filter(t => t.title.includes(searchTerm()))
);

<input value={searchTerm()} onInput={e => setSearchTerm(e.target.value)} />
<TodoList todos={filteredTodos()} />
```

### What They Have in Common

1. **Reactive primitives** - `ref`, `let`, `createSignal`
2. **Derived/computed values** - `computed`, `$:`, `createMemo`
3. **Two-way binding** - `v-model`, `bind:value`, controlled inputs

---

## Guitar's Approach: Simple Signals + HTML Binding

### State as Signals

```typescript
// guitar/core/state.ts
export const createState = <T>(initial: T, options?: StateOptions): State<T> => {
  let value = initial;
  const subscribers = new Set<(val: T) => void>();
  
  return {
    get: () => value,
    
    set: (newValue: T) => {
      if (newValue !== value) {
        value = newValue;
        subscribers.forEach(fn => fn(value));
      }
    },
    
    subscribe: (fn: (val: T) => void) => {
      subscribers.add(fn);
      return () => subscribers.delete(fn);
    },
  };
};

// Usage
const searchTerm = createState('', { debounce: 300 });
searchTerm.subscribe(val => console.log('Search changed:', val));
searchTerm.set('hello');
```

### Derived State

```typescript
export const deriveState = <T>(
  fn: () => T,
  deps: State<any>[]
): DerivedState<T> => {
  let cached = fn();
  
  // Re-compute when deps change
  deps.forEach(dep => {
    dep.subscribe(() => {
      cached = fn();
      subscribers.forEach(fn => fn(cached));
    });
  });
  
  return {
    get: () => cached,
    subscribe: (fn) => { ... },
  };
};

// Usage
const filteredTodos = deriveState(
  () => Todo.objects.filter({ title__icontains: searchTerm.get() }),
  [searchTerm]
);
```

### Global State Store

```typescript
// guitar/state.ts
import { createState, deriveState } from '@guitar/core';

export const state = {
  // UI state
  searchTerm: createState('', { debounce: 300 }),
  sortOrder: createState('-created_at'),
  filterCompleted: createState<boolean | null>(null),
  selectedTodoId: createState<number | null>(null),
  
  // Derived
  get activeTodosQuery() {
    return deriveState(() => {
      let qs = Todo.objects;
      
      const search = this.searchTerm.get();
      if (search) qs = qs.filter({ title__icontains: search });
      
      const completed = this.filterCompleted.get();
      if (completed !== null) qs = qs.filter({ completed });
      
      return qs.order_by(this.sortOrder.get());
    }, [this.searchTerm, this.sortOrder, this.filterCompleted]);
  },
  
  get selectedTodo() {
    return deriveState(() => {
      const id = this.selectedTodoId.get();
      return id ? Guitar.registry.get('todo', id) : null;
    }, [this.selectedTodoId]);
  },
};
```

---

## HTML Binding Syntax

### The @ Syntax Extended

```html
<!-- Bind input to state (two-way) -->
<input @state="searchTerm">

<!-- Bind with debounce -->
<input @state="searchTerm" @debounce="300">

<!-- One-way: read from state -->
<span @text="selectedTodo.title"></span>

<!-- One-way: write to state on event -->
<button @click:state="filterCompleted = false">Active</button>

<!-- Conditional class based on state -->
<button @class:active="filterCompleted === false">Active</button>

<!-- Show/hide based on state -->
<div @show="selectedTodoId !== null">
  <todo-edit @bind:item-id="selectedTodoId"></todo-edit>
</div>

<!-- Iterate (for lists) -->
<ul @each="todo in activeTodosQuery">
  <todo-list-item @bind:item="todo"></todo-list-item>
</ul>
```

### Wait, Are We Rebuilding Vue?

Kind of! But simpler:

| Vue | Guitar | Notes |
|-----|--------|-------|
| `v-model` | `@state` | Two-way binding |
| `v-bind:class` | `@class:name` | Conditional class |
| `v-show` | `@show` | Toggle visibility |
| `v-for` | `@each` | Iteration |
| `@click` | `@click` | Same! |
| `{{ expr }}` | `{{ expr }}` | Same! (Nunjucks) |

**The difference**: Guitar is HTML-first, not component-first. No build step required for basic usage.

---

## Where Does Todo Data Live?

### The Registry Is State Too

```typescript
// Guitar.registry is just another state store
// But it syncs with the backend

Guitar.registry = {
  // Internal storage
  _store: new Map<string, Map<number, any>>(),
  
  // Get an item (reactive)
  get: (model, id) => {
    return this._store.get(model)?.get(id);
  },
  
  // Set an item (triggers subscribers)
  set: (model, id, data) => {
    this._store.get(model)?.set(id, data);
    this.emit(`${model}:updated`, data);
  },
  
  // Subscribe to changes
  subscribe: (model, id, fn) => { ... },
};
```

### So State Is Unified

```
┌─────────────────────────────────────────────────────────────────┐
│                        Guitar State                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   UI State (frontend-only)          Model State (backend-synced)│
│   ─────────────────────────         ───────────────────────────│
│   state.searchTerm                  Guitar.registry.todo[1]     │
│   state.sortOrder                   Guitar.registry.todo[2]     │
│   state.selectedTodoId              Guitar.registry.chart[5]    │
│   state.filterCompleted             ...                         │
│                                                                  │
│   Derived State                                                 │
│   ──────────────                                                │
│   state.activeTodosQuery  ──────▶  Uses both UI + Model state   │
│   state.selectedTodo      ──────▶  Looks up from registry       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Complete Example with State

### State Definition

```typescript
// app/state.ts
import { defineState } from '@guitar/core';
import { Todo } from './guitar/models/Todo';

export default defineState({
  // UI State
  searchTerm: { 
    default: '', 
    debounce: 300 
  },
  
  sortOrder: { 
    default: '-created_at' 
  },
  
  filterCompleted: { 
    default: null 
  },
  
  selectedTodoId: { 
    default: null 
  },
  
  // Derived: the queryset
  todosQuery: {
    derive: (s) => {
      let qs = Todo.objects;
      if (s.searchTerm) qs = qs.filter({ title__icontains: s.searchTerm });
      if (s.filterCompleted !== null) qs = qs.filter({ completed: s.filterCompleted });
      return qs.order_by(s.sortOrder);
    },
    deps: ['searchTerm', 'filterCompleted', 'sortOrder'],
  },
  
  // Derived: selected todo object
  selectedTodo: {
    derive: (s) => s.selectedTodoId ? Guitar.registry.get('todo', s.selectedTodoId) : null,
    deps: ['selectedTodoId'],
  },
});
```

### HTML

```html
<!DOCTYPE html>
<html>
<head>
  <script type="module">
    import { Guitar } from '@guitar/core';
    import state from './app/state.ts';
    Guitar.useState(state);
    Guitar.init();
  </script>
</head>
<body>
  <div class="todo-app">
    <aside>
      <h1>Todos</h1>
      
      <!-- Search binds to state.searchTerm (debounce defined in state) -->
      <input type="search" placeholder="Search..." @state="searchTerm">
      
      <!-- Sort binds to state.sortOrder -->
      <select @state="sortOrder">
        <option value="-created_at">Newest</option>
        <option value="-priority">Priority</option>
      </select>
      
      <!-- Filter buttons set state.filterCompleted -->
      <nav>
        <button 
          @click:state="filterCompleted = null"
          @class:active="filterCompleted === null"
        >All</button>
        
        <button 
          @click:state="filterCompleted = false"
          @class:active="filterCompleted === false"
        >Active</button>
        
        <button 
          @click:state="filterCompleted = true"
          @class:active="filterCompleted === true"
        >Done</button>
      </nav>
      
      <!-- List uses derived queryset -->
      <guitar-list 
        :queryset="todosQuery"
        template="list-item"
      ></guitar-list>
      
      <!-- Quick add -->
      <form @submit:create="todo" @submit:reset>
        <input type="text" name="title" placeholder="Add todo...">
        <button type="submit">Add</button>
      </form>
    </aside>
    
    <main>
      <!-- Show edit when something selected -->
      <div @show="selectedTodoId">
        <todo-edit :item-id="selectedTodoId"></todo-edit>
      </div>
      
      <!-- Empty state when nothing selected -->
      <div @show="!selectedTodoId" class="empty-state">
        Select a todo
      </div>
    </main>
  </div>
</body>
</html>
```

### Template with State Interaction

```html
<!-- guitar/templates/todo/list-item.html -->
<li 
  class="{{ 'completed' if todo.completed }}"
  @class:selected="selectedTodoId === todo.id"
>
  <input 
    type="checkbox"
    {{ 'checked' if todo.completed }}
    @change="toggle"
  >
  
  <span @click:state="selectedTodoId = todo.id">
    {{ todo.title }}
  </span>
  
  <button @click="delete" @confirm="Delete?">×</button>
</li>
```

---

## Inline Expressions in @click

### Should We Allow This?

```html
<button @click="() => console.log('hi')">Click</button>
```

### Options

1. **Named actions only** (safe, but limiting)
   ```html
   <button @click="sayHi">Click</button>
   ```

2. **Simple expressions** (useful, relatively safe)
   ```html
   <button @click:state="count = count + 1">+1</button>
   <button @click:state="selectedId = todo.id">Select</button>
   ```

3. **Full JS** (powerful, but risky)
   ```html
   <button @click="() => { console.log('hi'); doThing(); }">Click</button>
   ```

### Recommendation: Named + Simple State Expressions

```html
<!-- Named action (calls actions.selectTodo) -->
<button @click="selectTodo">Select</button>

<!-- State assignment (safe, limited syntax) -->
<button @click:state="selectedTodoId = todo.id">Select</button>
<button @click:state="count = count + 1">+1</button>

<!-- NOT allowed (security risk, eval needed) -->
<button @click="() => console.log('hi')">Click</button>
```

For complex logic, use named actions:

```typescript
// list-item.ts
export const actions = {
  selectTodo: (todo) => {
    console.log('Selected:', todo);
    state.selectedTodoId.set(todo.id);
    analytics.track('todo_selected', todo.id);
  },
};
```

```html
<button @click="selectTodo">Select</button>
```

---

## Django: Generate Starter Template from Generic View

### The Command

```bash
python manage.py guitar_eject todo list-item
```

This would:
1. Look at current generic rendering for `todo` + `list-item`
2. Generate `guitar/templates/todo/list-item.html`
3. Generate `guitar/templates/todo/list-item.ts` (with default actions)

### Output

```html
<!-- guitar/templates/todo/list-item.html -->
<!-- Generated from guitar-list generic view -->
<li class="guitar-list-item {{ 'completed' if todo.completed }}">
  {% for field in fields %}
    <span class="field-{{ field.name }}">
      {{ todo[field.name] }}
    </span>
  {% endfor %}
  
  <div class="actions">
    <button @click="edit">Edit</button>
    <button @click="delete">Delete</button>
  </div>
</li>
```

```typescript
// guitar/templates/todo/list-item.ts
// Generated - customize as needed

export const actions = {
  edit: (todo) => {
    state.selectedTodoId.set(todo.id);
  },
  
  delete: async (todo) => {
    if (confirm(`Delete "${todo.title}"?`)) {
      await Todo.objects.filter({ id: todo.id }).delete();
    }
  },
};
```

### Now You Can Customize

```html
<!-- Customize the generated template -->
<li class="todo-item fancy {{ 'done' if todo.completed }}">
  <div class="todo-content">
    <input type="checkbox" @change="toggle" {{ 'checked' if todo.completed }}>
    <span class="title" @click="select">{{ todo.title }}</span>
  </div>
  
  <!-- Add your custom stuff -->
  <div class="todo-meta">
    <span class="priority priority-{{ todo.priority }}">{{ todo.priority }}</span>
    <time>{{ todo.due_date|date:"M d" }}</time>
  </div>
</li>
```

---

## Summary: The State Model

### Core Concepts

| Concept | What It Is |
|---------|------------|
| **UI State** | Frontend-only values (searchTerm, selectedId) |
| **Model State** | Backend-synced objects (Todo, Chart) |
| **Derived State** | Computed from other state (filtered query) |
| **State Binding** | `@state="varName"` binds input to state |
| **State Expression** | `@click:state="x = y"` for simple assignments |

### The Unified View

```
Input @state="searchTerm"
              │
              ▼
        ┌───────────┐
        │   State   │
        │ searchTerm├──────┐
        │ sortOrder │      │
        │ filterDone│      │
        └───────────┘      │
              │            │
              ▼            │
        ┌───────────┐      │
        │  Derived  │      │
        │ todosQuery│◀─────┘
        └───────────┘
              │
              ▼
        ┌───────────┐
        │guitar-list│
        │:queryset  │
        └───────────┘
              │
              ▼
        ┌───────────┐
        │ Registry  │
        │ todo[1]   │
        │ todo[2]   │
        └───────────┘
```

Everything is connected through state. Changes flow automatically.

### Is This Too Complex?

It's optional complexity:

```html
<!-- Simple: No state, just attributes -->
<guitar-list model="todo" filter='{"completed": false}'></guitar-list>

<!-- Medium: State bindings, no custom state file -->
<input @state="Guitar.searchTerm">
<guitar-list model="todo" @filter:search="searchTerm"></guitar-list>

<!-- Advanced: Full state definition with derived querysets -->
<guitar-list :queryset="state.activeTodosQuery"></guitar-list>
```

You opt into complexity as needed.
