# Guitar Frontend - v7: Simplified Design

## The Key Simplifications

1. **Debounce on queryset chain**, not inputs
2. **Auto deps** via state access tracking
3. **Queryset defined as function**, passed to element
4. **`:state` auto-creates state** from input defaults

---

## 1. Debounce on Queryset Chain

Instead of debouncing inputs, debounce the queryset execution:

```typescript
const todosQuery = () => {
  return Todo.objects
    .filter({ title__icontains: state.searchTerm || undefined })
    .filter({ completed: state.filterCompleted })
    .order_by(state.sortOrder)
    .debounce(300);  // Debounce the whole query execution
};
```

### Why This Is Better

| Debounce on Input | Debounce on Queryset |
|-------------------|----------------------|
| Each input needs debounce config | One place |
| Multiple inputs = multiple debounces | All changes batched |
| Config scattered in HTML | Config with the query |
| Feels like UI concern | Feels like data concern ✓ |

### Implementation

```typescript
// In GuitarManager
debounce(ms: number): this {
  const cloned = this._clone();
  cloned._debounceMs = ms;
  return cloned;
}

// When executing, the element debounces
class GuitarListElement {
  private _debounceTimer: number | null = null;
  
  scheduleLoad() {
    const debounceMs = this._queryset?._debounceMs || 0;
    
    if (this._debounceTimer) {
      clearTimeout(this._debounceTimer);
    }
    
    if (debounceMs > 0) {
      this._debounceTimer = setTimeout(() => this.load(), debounceMs);
    } else {
      this.load();
    }
  }
}
```

---

## 2. Auto Deps via State Tracking

The queryset accesses `state.*` properties. We track those accesses and auto-subscribe:

```typescript
const todosQuery = () => {
  return Todo.objects
    .filter({ title__icontains: state.searchTerm || undefined })  // tracked
    .filter({ completed: state.filterCompleted })                   // tracked
    .order_by(state.sortOrder)                                      // tracked
    .debounce(300);
};
```

No `deps` attribute needed. When `state.searchTerm` changes → queryset re-runs → list updates.

### Implementation

```typescript
// State is a Proxy that tracks access
const state = new Proxy({}, {
  get(target, prop) {
    // Record access for current tracking context
    if (currentTracker) {
      currentTracker.deps.add(prop);
    }
    return target[prop];
  },
  set(target, prop, value) {
    const oldValue = target[prop];
    target[prop] = value;
    
    // Notify subscribers
    if (oldValue !== value) {
      stateSubscribers.get(prop)?.forEach(fn => fn(value));
    }
    return true;
  }
});

// Track deps when running a function
const trackDeps = (fn) => {
  const tracker = { deps: new Set() };
  const prevTracker = currentTracker;
  currentTracker = tracker;
  
  const result = fn();
  
  currentTracker = prevTracker;
  return { result, deps: tracker.deps };
};
```

---

## 3. Queryset as Function, Passed to Element

Define the queryset separately, pass it to the list:

```typescript
// queries.ts
export const todosQuery = () => {
  return Todo.objects
    .filter({ title__icontains: state.searchTerm || undefined })
    .filter({ completed: state.filterCompleted })
    .order_by(state.sortOrder)
    .debounce(300);
};

export const highPriorityTodos = () => {
  return Todo.objects
    .filter({ priority: 'high', completed: false })
    .order_by('-created_at');
};
```

```html
<script type="module">
  import { todosQuery } from './queries.js';
  
  // Pass to element
  document.querySelector('guitar-list').query = todosQuery;
</script>

<guitar-list id="todo-list" template="list-item"></guitar-list>
```

Or via attribute with a registered name:

```typescript
Guitar.registerQuery('todos', todosQuery);
Guitar.registerQuery('high-priority-todos', highPriorityTodos);
```

```html
<guitar-list query="todos" template="list-item"></guitar-list>
<guitar-list query="high-priority-todos" template="card"></guitar-list>
```

---

## 4. `:state` Auto-Creates State from Input Defaults

The `:state` attribute does two things:
1. **Creates the state variable** (if it doesn't exist)
2. **Two-way binds** the input to it

```html
<!-- This creates state.searchTerm = '' and binds it -->
<input type="search" :state="searchTerm" value="">

<!-- This creates state.sortOrder = '-created_at' and binds it -->
<select :state="sortOrder">
  <option value="-created_at" selected>Newest</option>
  <option value="-priority">Priority</option>
</select>

<!-- This creates state.filterCompleted = null and binds it -->
<input type="checkbox" :state="filterCompleted" indeterminate>
```

### How It Works

```typescript
// On element init, find all :state bindings
document.querySelectorAll('[\\:state]').forEach(el => {
  const stateName = el.getAttribute(':state');
  
  // Get initial value from element
  let initialValue;
  if (el instanceof HTMLInputElement) {
    if (el.type === 'checkbox') {
      initialValue = el.indeterminate ? null : el.checked;
    } else {
      initialValue = el.value;
    }
  } else if (el instanceof HTMLSelectElement) {
    initialValue = el.value;
  }
  
  // Create state if doesn't exist
  if (!(stateName in state)) {
    state[stateName] = initialValue;
  }
  
  // Bind: state → element
  stateSubscribers.get(stateName)?.add((value) => {
    if (el instanceof HTMLInputElement && el.type === 'checkbox') {
      el.checked = value;
    } else {
      el.value = value;
    }
  });
  
  // Bind: element → state
  el.addEventListener('input', () => {
    if (el instanceof HTMLInputElement && el.type === 'checkbox') {
      state[stateName] = el.checked;
    } else {
      state[stateName] = el.value;
    }
  });
});
```

### Button State Setting

For buttons that set state values:

```html
<!-- :state:set="var = value" -->
<button :state:set="filterCompleted = null" :class:active="filterCompleted === null">
  All
</button>
<button :state:set="filterCompleted = false" :class:active="filterCompleted === false">
  Active
</button>
<button :state:set="filterCompleted = true" :class:active="filterCompleted === true">
  Done
</button>
```

---

## Complete Example

### queries.ts

```typescript
import { state } from '@guitar/core';
import { Todo } from './guitar/models/Todo';

export const todosQuery = () => {
  let qs = Todo.objects;
  
  // These state accesses are auto-tracked
  if (state.searchTerm) {
    qs = qs.filter({ title__icontains: state.searchTerm });
  }
  
  if (state.filterCompleted !== null) {
    qs = qs.filter({ completed: state.filterCompleted });
  }
  
  qs = qs.order_by(state.sortOrder || '-created_at');
  
  // Debounce on the query, not inputs
  return qs.debounce(300);
};
```

### index.html

```html
<!DOCTYPE html>
<html>
<head>
  <script type="module">
    import { Guitar } from '@guitar/core';
    import { todosQuery } from './queries.js';
    
    Guitar.registerQuery('todos', todosQuery);
    Guitar.init();
  </script>
</head>
<body>
  <div class="todo-app">
    <aside>
      <h1>Todos</h1>
      
      <!-- :state creates and binds state.searchTerm, default '' -->
      <input 
        type="search" 
        :state="searchTerm" 
        value=""
        placeholder="Search..."
      >
      
      <!-- :state creates and binds state.sortOrder, default '-created_at' -->
      <select :state="sortOrder">
        <option value="-created_at" selected>Newest</option>
        <option value="-priority">Priority</option>
        <option value="due_date">Due Date</option>
      </select>
      
      <!-- Buttons set state.filterCompleted -->
      <nav class="filters">
        <button 
          :state:set="filterCompleted = null" 
          :class:active="filterCompleted === null"
        >All</button>
        <button 
          :state:set="filterCompleted = false" 
          :class:active="filterCompleted === false"
        >Active</button>
        <button 
          :state:set="filterCompleted = true" 
          :class:active="filterCompleted === true"
        >Done</button>
      </nav>
      
      <!-- List uses registered query, auto-updates on state changes -->
      <guitar-list query="todos" template="list-item"></guitar-list>
      
      <!-- Quick add form -->
      <form @submit.prevent="createTodo">
        <input type="text" name="title" placeholder="Add todo..." required>
        <button type="submit">Add</button>
      </form>
    </aside>
    
    <main>
      <!-- Show when selected -->
      <todo-edit 
        :show="state.selectedTodoId" 
        :item-id="state.selectedTodoId"
      ></todo-edit>
      
      <!-- Empty state -->
      <div :show="!state.selectedTodoId" class="empty">
        Select a todo
      </div>
    </main>
  </div>
</body>
</html>
```

### Template: list-item.html

```html
<li :class="{ completed: todo.completed, selected: state.selectedTodoId === todo.id }">
  <input 
    type="checkbox" 
    :checked="todo.completed"
    @change="toggleComplete"
  >
  
  <span @click="state.selectedTodoId = todo.id">
    {{ todo.title }}
  </span>
  
  <button @click="deleteTodo" @confirm="Delete?">×</button>
</li>
```

```typescript
// list-item.ts
export const actions = {
  toggleComplete: async (todo, el, e) => {
    await Todo.objects.filter({ id: todo.id }).update({
      completed: e.target.checked
    });
  },
  
  deleteTodo: async (todo) => {
    await Todo.objects.filter({ id: todo.id }).delete();
  },
};
```

---

## Summary

| Concept | Implementation |
|---------|----------------|
| **Debounce** | `.debounce(300)` on queryset chain |
| **Dependencies** | Auto-tracked from `state.*` access |
| **Queryset** | Function passed to element via `query` prop |
| **State binding** | `:state="varName"` creates + binds |
| **State default** | Taken from input's initial value |
| **State setting** | `:state:set="var = value"` on buttons |

### The Flow

```
Input :state="searchTerm"
         │
         │ creates & binds
         ▼
    state.searchTerm ◄─────────────────┐
         │                              │
         │ auto-tracked                 │
         ▼                              │
    todosQuery()                        │
         │                              │
         │ .debounce(300)               │
         ▼                              │
    <guitar-list>                       │
         │                              │
         │ on item click                │
         ▼                              │
    state.selectedTodoId = id ──────────┘
         │
         │ triggers :show
         ▼
    <todo-edit :item-id="state.selectedTodoId">
```

Everything flows through state. Queryset debounces. Inputs auto-create state. Clean! 🎸
