# Research Notes

This directory contains AI-assisted research and design documents for Django Guitar. These are working documents and brainstorming notes, not official documentation.

## Frontend Framework Design

We're designing a Django-like frontend framework that uses Web Components and reactive state.

### Start Here

📄 **[guitar-frontend-summary.md](guitar-frontend-summary.md)** - Complete summary of the frontend framework design

### Research History

| Version | Document | Focus |
|---------|----------|-------|
| v1 | [frontend-framework-research.md](frontend-framework-research.md) | Initial research: `.render()`, Django Forms, HTMX influences |
| v2 | [frontend-framework-refined.md](frontend-framework-refined.md) | `_renders` field, template files, custom elements, registry |
| v3 | [frontend-framework-v3.md](frontend-framework-v3.md) | Auto-generated elements, queryset functions, todo app |
| v4 | [frontend-framework-v4.md](frontend-framework-v4.md) | Behavior files, `@event` syntax, declarative `data-guitar-*` |
| v5 | [frontend-framework-v5-state.md](frontend-framework-v5-state.md) | Unified state model (UI + model state) |
| v6 | [frontend-framework-v6-syntax.md](frontend-framework-v6-syntax.md) | Vue-style `:` and `@` syntax, `deps` attribute |
| v7 | [frontend-framework-v7-final.md](frontend-framework-v7-final.md) | Debounce on queryset, `:state` auto-creates state |
| v8 | [frontend-framework-v8-slots.md](frontend-framework-v8-slots.md) | Empty/loading states, Django's `{% empty %}` pattern |

## Key Decisions

1. **Custom Elements** - Web Components work natively in React, Vue, Svelte, vanilla
2. **Templates** - Django/Nunjucks syntax + `@click`, `@change` event bindings
3. **State** - `:state="varName"` auto-creates and two-way binds from input defaults
4. **Debounce** - `.debounce(300)` on queryset chain, not on individual inputs
5. **Auto-tracking** - Dependencies detected from `state.*` access, no explicit declaration
6. **Empty/Loading** - Django's `{% empty %}` pattern + `<template name="loading">`

## Example Usage (from Summary)

```html
<!-- State auto-created from inputs -->
<input type="search" :state="searchTerm" value="">
<select :state="sortOrder">
  <option value="-created_at" selected>Newest</option>
</select>

<!-- List auto-updates when state changes -->
<guitar-list 
  model="todo"
  :filter="{ title__icontains: state.searchTerm }"
  :order="state.sortOrder"
  :debounce="300"
></guitar-list>
```

## Contributing

These notes evolve through conversation. When continuing this work:

1. Read `guitar-frontend-summary.md` for current state
2. Build on the latest version (v8)
3. Keep the Django-like philosophy in mind
