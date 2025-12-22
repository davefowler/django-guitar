# Guitar Frontend - v8: Empty & Loading States (Django-Style)

## Django's Approach

### The `{% empty %}` Tag

In Django templates, you handle empty states inside a `{% for %}` loop:

```html
{% for todo in todo_list %}
  <li>{{ todo.title }}</li>
{% empty %}
  <li class="empty">No todos yet. Add one!</li>
{% endfor %}
```

### ListView's Context

Django's `ListView` provides:
- `object_list` - the queryset results
- `is_paginated` - whether results are paginated
- `paginator` - the paginator object

You check emptiness yourself:

```html
{% if object_list %}
  <ul>
    {% for obj in object_list %}...{% endfor %}
  </ul>
{% else %}
  <p class="empty-state">Nothing here yet.</p>
{% endif %}
```

### No Built-in Loading State

Django is server-rendered, so there's no "loading" state - the page arrives fully rendered. Loading states are a client-side concern.

---

## Guitar's Approach: Follow Django, Add Loading

### Option 1: `{% empty %}` in Template (Django-Style)

Keep the Django pattern in our Nunjucks templates:

```html
<!-- guitar/templates/todo/list.html -->
<ul class="todo-list">
  {% for todo in todos %}
    <li>{{ todo.title }}</li>
  {% empty %}
    <li class="empty-state">
      <p>No todos found</p>
      <button @click="createFirst">Create your first todo</button>
    </li>
  {% endfor %}
</ul>
```

The `<guitar-list>` element renders this template, passing `todos` as context. If empty, the `{% empty %}` block renders.

**Pros:** Exactly like Django. One template file.
**Cons:** Empty state tied to template, can't override per-instance.

### Option 2: Inline Empty Content (HTML Standard)

Use the element's children as the empty state:

```html
<guitar-list query="todos" template="list-item">
  <!-- Children are the empty state -->
  <div class="empty-state">
    <img src="/empty-todos.svg" alt="">
    <p>No todos yet</p>
    <button @click="createTodo">Add your first todo</button>
  </div>
</guitar-list>
```

When results exist, children are replaced with rendered items.
When empty, children stay visible.

**Pros:** Simple, standard HTML, easy to customize per-instance.
**Cons:** Slightly different from Django's `{% empty %}`.

### Option 3: Named Templates (Most Flexible)

```html
<guitar-list 
  query="todos" 
  template="list-item"
  empty-template="empty-state"
  loading-template="loading-skeleton"
></guitar-list>
```

With templates:

```html
<!-- guitar/templates/todo/list-item.html -->
<li>{{ todo.title }}</li>

<!-- guitar/templates/todo/empty-state.html -->
<div class="empty-state">
  <p>No todos found</p>
</div>

<!-- guitar/templates/todo/loading-skeleton.html -->
<div class="skeleton">
  <div class="skeleton-item"></div>
  <div class="skeleton-item"></div>
  <div class="skeleton-item"></div>
</div>
```

**Pros:** Reusable templates, very flexible.
**Cons:** More files to manage.

---

## Recommended: Combine All Three

### 1. Default: `{% empty %}` in Template

```html
<!-- guitar/templates/todo/list.html -->
<ul class="todo-list">
  {% for todo in todos %}
    {% include "todo/list-item.html" %}
  {% empty %}
    <li class="empty-state">No todos</li>
  {% endfor %}
</ul>
```

### 2. Override: Inline Children

```html
<!-- Override empty state for this instance -->
<guitar-list query="todos" template="list">
  <div class="custom-empty">
    <p>Your custom empty message</p>
  </div>
</guitar-list>
```

### 3. Override: Named Template

```html
<!-- Use a different empty template -->
<guitar-list 
  query="todos" 
  template="list"
  empty="onboarding-empty"
></guitar-list>
```

### Priority

1. `empty` attribute → use that template
2. Has children → use children as empty state
3. Neither → use `{% empty %}` from main template

---

## Loading State

Django doesn't have this, but we need it for client-side rendering.

### Default Loading (Built-in)

```html
<guitar-list query="todos" template="list-item">
  <!-- Shows default spinner while loading -->
</guitar-list>
```

The element has a default loading indicator (spinner, skeleton, etc.).

### Custom Loading: Inline

```html
<guitar-list query="todos" template="list-item">
  <template loading>
    <div class="my-loading">
      <div class="pulse"></div>
      <p>Loading your todos...</p>
    </div>
  </template>
  
  <template empty>
    <p>No todos yet</p>
  </template>
</guitar-list>
```

### Custom Loading: Named Template

```html
<guitar-list 
  query="todos" 
  template="list-item"
  loading="fancy-skeleton"
  empty="onboarding"
></guitar-list>
```

---

## About `<template>` and Slots

### Is `<template slot="">` Standard?

The `<template>` element is standard HTML - it holds content that isn't rendered immediately.

**Slots** come from Web Components / Shadow DOM:
```html
<!-- Shadow DOM style -->
<my-element>
  <span slot="header">Title</span>
</my-element>
```

Since we're not using Shadow DOM, we can use `<template>` with a custom attribute:

```html
<guitar-list query="todos" template="list-item">
  <template name="loading">
    <div class="skeleton">...</div>
  </template>
  
  <template name="empty">
    <div class="empty-state">...</div>
  </template>
</guitar-list>
```

### Implementation

```typescript
class GuitarListElement extends HTMLElement {
  getSlot(name: string): string | null {
    const template = this.querySelector(`template[name="${name}"]`);
    return template?.innerHTML || null;
  }
  
  async load() {
    // Show loading
    const loadingContent = this.getSlot('loading') || this.defaultLoading;
    this.innerHTML = loadingContent;
    
    // Fetch
    const items = await this.query().all();
    
    if (items.length === 0) {
      // Show empty
      const emptyContent = this.getSlot('empty') 
        || this.getAttribute('empty')  // named template
        || this.defaultEmpty;
      this.innerHTML = emptyContent;
    } else {
      // Render items
      this.innerHTML = items.map(item => 
        renderTemplate(this.template, { [this.model]: item })
      ).join('');
    }
  }
}
```

---

## Full Example

### The Template (Django-style with {% empty %})

```html
<!-- guitar/templates/todo/list.html -->
<ul class="todo-list">
  {% for todo in todos %}
    <li 
      class="{{ 'completed' if todo.completed }}"
      @click="state.selectedTodoId = todo.id"
    >
      <input type="checkbox" :checked="todo.completed" @change="toggle">
      <span>{{ todo.title }}</span>
    </li>
  {% empty %}
    <li class="empty-state">
      <p>No todos match your search</p>
    </li>
  {% endfor %}
</ul>
```

### Usage with Defaults

```html
<!-- Uses {% empty %} from template -->
<guitar-list query="todos" template="list"></guitar-list>
```

### Usage with Override

```html
<!-- Override empty state for onboarding -->
<guitar-list query="todos" template="list">
  <template name="empty">
    <div class="onboarding">
      <h2>Welcome! 👋</h2>
      <p>Create your first todo to get started</p>
      <button @click="showCreateModal">Create Todo</button>
    </div>
  </template>
  
  <template name="loading">
    <div class="skeleton-list">
      <div class="skeleton-item"></div>
      <div class="skeleton-item"></div>
      <div class="skeleton-item"></div>
    </div>
  </template>
</guitar-list>
```

### Global Defaults

```typescript
// Set global defaults
Guitar.defaults.loading = `
  <div class="guitar-loading">
    <div class="spinner"></div>
  </div>
`;

Guitar.defaults.empty = `
  <div class="guitar-empty">
    <p>No items found</p>
  </div>
`;
```

---

## Summary

| State | Django Pattern | Guitar Pattern |
|-------|---------------|----------------|
| **Empty** | `{% empty %}` in `{% for %}` | Same, or override via `<template name="empty">` |
| **Loading** | N/A (server-rendered) | `<template name="loading">` or default spinner |

### Priority for Empty State

1. `empty="template-name"` attribute
2. `<template name="empty">` child
3. `{% empty %}` in the main template
4. Global `Guitar.defaults.empty`

### Priority for Loading State

1. `loading="template-name"` attribute
2. `<template name="loading">` child
3. Global `Guitar.defaults.loading`
4. Built-in spinner

This follows Django's pattern while adding the client-side loading state we need. The `{% empty %}` block in templates keeps things Django-familiar, while `<template name="">` allows per-instance overrides.
