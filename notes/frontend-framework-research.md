# Guitar Frontend Framework Research

A research document exploring how to build a Django-like frontend experience for Guitar, enabling backend-focused Django developers to build rich frontends with minimal JavaScript.

## Table of Contents

1. [Vision & Goals](#vision--goals)
2. [The `.render()` Concept](#the-render-concept)
3. [Influences from Django Forms](#influences-from-django-forms)
4. [Influences from Django Class-Based Views](#influences-from-django-class-based-views)
5. [HTMX Influences](#htmx-influences)
6. [Template Organization](#template-organization)
7. [Event System & Interactivity](#event-system--interactivity)
8. [Auto-Save & Easy Editing Patterns](#auto-save--easy-editing-patterns)
9. [Framework Integrations](#framework-integrations)
10. [Todo App Example](#todo-app-example)
11. [Proposed Architecture](#proposed-architecture)
12. [Implementation Roadmap](#implementation-roadmap)

---

## Vision & Goals

### The Problem

Django developers love the ORM, the admin, the forms, and the "batteries included" philosophy. But when it comes to building modern, interactive frontends, they're often forced into a completely different paradigm: React, Vue, or other JavaScript frameworks that feel alien to the Django way of thinking.

Guitar already bridges the gap for **data access** with its Django-like TypeScript client:

```typescript
const charts = await Chart.objects.filter({ dashboard_id: 1 });
```

But what about **rendering**? Django developers think in templates, not JSX. They want:

```python
# This feels natural to a Django developer
charts = Chart.objects.filter(dashboard=dashboard)
html = charts.render('card')  # Returns rendered HTML for all charts
```

### Goals

1. **Django-Like Templates** - Use familiar templating patterns, not JSX
2. **Multiple Views Per Model** - Card, edit, full-screen, list-item variants
3. **Minimal JavaScript** - Behaviors declared in HTML, like HTMX
4. **Auto-Save & Inline Editing** - Built-in patterns for common interactions
5. **Framework Agnostic** - Works standalone or integrates with React/Vue/Svelte
6. **Type Safety** - Keep TypeScript benefits where needed

---

## The `.render()` Concept

### Core Idea

Extend the Guitar queryset chain with a `.render()` method that returns HTML:

```typescript
// Current Guitar API - returns data
const charts = await Chart.objects.filter({ dashboard_id: 1 }).all();

// Proposed - returns rendered HTML
const html = await Chart.objects.filter({ dashboard_id: 1 }).render('card');

// Or with a queryset that's already been fetched
const charts = await Chart.objects.filter({ dashboard_id: 1 }).all();
const html = Chart.render(charts, 'card');
```

### Two Rendering Modes

#### 1. Server-Side Rendering (SSR)

Templates live on the Django backend, rendered via a new endpoint:

```typescript
// Makes request to /guitar/chart/render/?template=card&dashboard_id=1
const html = await Chart.objects.filter({ dashboard_id: 1 }).render('card');
```

Backend implementation:
```python
# guitar/templates/chart/card.html
<div class="chart-card" data-guitar-model="chart" data-guitar-id="{{ chart.id }}">
    <h3>{{ chart.name }}</h3>
    <span class="chart-type">{{ chart.chart_type }}</span>
    <div class="chart-preview">
        {% include "chart/partials/preview.html" %}
    </div>
</div>
```

**Pros:**
- Use existing Django template skills
- Full Django template power (tags, filters, includes)
- SEO-friendly
- Works without JavaScript for initial render

**Cons:**
- Network roundtrip for each render
- Harder to integrate with React/Vue virtual DOM

#### 2. Client-Side Rendering (CSR)

Templates defined in TypeScript/JavaScript, compiled at build time:

```typescript
// guitar-templates/chart/card.ts
export const card: GuitarTemplate<Chart> = {
  render: (chart) => html`
    <div class="chart-card" data-guitar-model="chart" data-guitar-id="${chart.id}">
      <h3>${chart.name}</h3>
      <span class="chart-type">${chart.chart_type}</span>
    </div>
  `,
};

// Usage
const html = await Chart.objects.filter({ dashboard_id: 1 }).render('card');
```

**Pros:**
- No network roundtrip for rendering
- Better integration with frontend frameworks
- Can use tagged template literals for type safety

**Cons:**
- Templates in TypeScript, not Django templates
- Requires build step

### Recommended: Hybrid Approach

Support both modes, with client-side as the default for interactive apps:

```typescript
// Configure per-model or globally
configure({
  renderMode: 'client', // or 'server'
  templatePath: '/guitar/templates/', // for server mode
});

// Server-side render (useful for emails, PDFs, SEO)
const html = await Chart.objects.filter({ dashboard_id: 1 }).render('card', { mode: 'server' });

// Client-side render (default for interactivity)
const html = await Chart.objects.filter({ dashboard_id: 1 }).render('card');
```

---

## Influences from Django Forms

Django Forms provide a powerful pattern for:
1. **Field definition** - What fields exist and their types
2. **Validation** - Client and server-side
3. **Rendering** - Multiple output formats (as_p, as_table, as_ul, individual fields)
4. **Widget customization** - How each field type renders

### Applying to Guitar Frontend

#### Field-Level Rendering

```typescript
// Auto-generated from GuitarMeta
interface ChartFieldRenderers {
  name: FieldRenderer<string>;
  chart_type: FieldRenderer<string>;  // Could be select with choices
  query: FieldRenderer<string>;       // Could be code editor
  config: FieldRenderer<object>;      // Could be JSON editor
}

// Usage
const nameField = Chart.fields.name.render(chart, {
  editable: true,
  widget: 'input',  // or 'textarea', 'select', etc.
});
```

#### Form Rendering Modes

```typescript
// Like Django's form.as_p, form.as_table
const editForm = await Chart.renderForm(chart, {
  layout: 'vertical',  // or 'horizontal', 'inline', 'table'
  fields: ['name', 'chart_type', 'query'],  // Optional field selection
  widgets: {
    query: 'code-editor',
    chart_type: 'select',
  },
});
```

#### Validation Integration

```typescript
// Define validation rules in GuitarMeta
class Chart(GuitarModel, models.Model):
    class GuitarMeta:
        fields = ['id', 'name', 'chart_type', 'query']
        writable_fields = ['name', 'chart_type', 'query']
        
        # NEW: Frontend validation hints
        validation = {
            'name': {'required': True, 'max_length': 255},
            'chart_type': {'choices': ['bar', 'line', 'pie', 'scatter', 'table']},
            'query': {'required': True},
        }
```

Generated TypeScript:

```typescript
// Auto-generated validation
const ChartValidation = {
  name: { required: true, maxLength: 255 },
  chartType: { 
    required: true,
    choices: ['bar', 'line', 'pie', 'scatter', 'table'],
  },
  query: { required: true },
};

// Form with validation
const form = Chart.createForm(chart, {
  onValidationError: (field, errors) => { /* ... */ },
  onSubmit: async (data) => {
    await Chart.objects.filter({ id: chart.id }).update(data);
  },
});
```

#### Widget System

Inspired by Django's widget system, but for the frontend:

```typescript
// Built-in widgets
type Widget = 
  | 'text-input'
  | 'textarea'
  | 'select'
  | 'checkbox'
  | 'radio'
  | 'date-picker'
  | 'datetime-picker'
  | 'number-input'
  | 'json-editor'
  | 'code-editor'
  | 'rich-text'
  | 'file-upload'
  | 'color-picker';

// Custom widgets
Guitar.registerWidget('chart-type-picker', {
  render: (field, value, onChange) => html`
    <div class="chart-type-picker">
      ${['bar', 'line', 'pie'].map(type => html`
        <button 
          class="${value === type ? 'active' : ''}"
          onclick="${() => onChange(type)}"
        >
          <icon name="${type}-chart" />
          ${type}
        </button>
      `)}
    </div>
  `,
});
```

---

## Influences from Django Class-Based Views

Django's CBVs provide standardized patterns for common operations:
- `ListView` - Display a list of objects
- `DetailView` - Display a single object
- `CreateView` - Form to create an object
- `UpdateView` - Form to edit an object
- `DeleteView` - Confirmation to delete an object

### Applying to Guitar Frontend

#### GuitarListView

```typescript
// Define a ListView-like component
const ChartList = Guitar.ListView({
  model: Chart,
  template: 'list-item',
  
  // Like Django's get_queryset()
  getQueryset: (params) => {
    return Chart.objects
      .filter({ dashboard_id: params.dashboardId })
      .order_by('-created_at');
  },
  
  // Pagination
  paginate_by: 20,
  
  // Context additions
  getContext: (charts) => ({
    totalCount: charts.length,
    isEmpty: charts.length === 0,
  }),
  
  // Empty state
  emptyTemplate: 'empty-state',
});

// Usage
const html = await ChartList.render({ dashboardId: 1 });
```

#### GuitarDetailView

```typescript
const ChartDetail = Guitar.DetailView({
  model: Chart,
  template: 'full',
  
  // Like Django's get_object()
  getObject: (params) => {
    return Chart.objects.get({ id: params.id });
  },
  
  // Related objects
  selectRelated: ['dashboard'],
  
  // Context additions
  getContext: async (chart) => ({
    relatedCharts: await Chart.objects
      .filter({ dashboard_id: chart.dashboard_id })
      .exclude({ id: chart.id })
      .limit(5)
      .all(),
  }),
});
```

#### GuitarEditView

```typescript
const ChartEdit = Guitar.EditView({
  model: Chart,
  template: 'edit-form',
  fields: ['name', 'chart_type', 'query', 'config'],
  
  // Widgets per field
  widgets: {
    query: 'code-editor',
    config: 'json-editor',
  },
  
  // Success handling
  onSuccess: (chart) => {
    Guitar.navigate(`/charts/${chart.id}`);
  },
  
  // Auto-save support
  autoSave: {
    enabled: true,
    debounce: 1000,  // ms
    showIndicator: true,
  },
});
```

#### GuitarDeleteView

```typescript
const ChartDelete = Guitar.DeleteView({
  model: Chart,
  template: 'delete-confirm',
  
  // Confirmation message
  getMessage: (chart) => `Delete "${chart.name}"?`,
  
  // Success handling
  onSuccess: () => {
    Guitar.navigate('/charts');
  },
});
```

---

## HTMX Influences

HTMX's genius is adding interactivity through HTML attributes, not JavaScript. This is extremely Django-friendly.

### Key HTMX Patterns to Adopt

#### 1. Declarative Actions

```html
<!-- HTMX style -->
<button hx-post="/charts/1/delete/" hx-confirm="Delete this chart?">
  Delete
</button>

<!-- Guitar equivalent -->
<button 
  data-guitar-action="delete"
  data-guitar-model="chart"
  data-guitar-id="1"
  data-guitar-confirm="Delete this chart?"
>
  Delete
</button>
```

#### 2. Target Updates

```html
<!-- Update a specific element with the response -->
<button 
  data-guitar-action="update"
  data-guitar-model="chart"
  data-guitar-id="1"
  data-guitar-data='{"name": "New Name"}'
  data-guitar-target="#chart-1"
  data-guitar-template="card"
>
  Rename
</button>
```

#### 3. Swap Strategies

```html
<!-- Different ways to update the DOM -->
<div 
  data-guitar-action="list"
  data-guitar-model="chart"
  data-guitar-filter='{"dashboard_id": 1}'
  data-guitar-template="list-item"
  data-guitar-swap="innerHTML"  <!-- or beforeend, afterbegin, outerHTML, etc. -->
>
  Loading charts...
</div>
```

#### 4. Trigger Events

```html
<!-- Load on different events -->
<input 
  type="text"
  data-guitar-action="search"
  data-guitar-model="chart"
  data-guitar-filter-field="name__icontains"
  data-guitar-target="#search-results"
  data-guitar-template="list-item"
  data-guitar-trigger="keyup changed delay:300ms"
/>
```

#### 5. Loading States

```html
<button 
  data-guitar-action="create"
  data-guitar-model="chart"
>
  <span data-guitar-loading="hide">Create Chart</span>
  <span data-guitar-loading="show" hidden>Creating...</span>
</button>
```

### Guitar Attribute System

Building on HTMX's approach, here's a proposed attribute system:

```typescript
// Core attributes
interface GuitarAttributes {
  // Model & Identity
  'data-guitar-model': string;      // Model name: 'chart'
  'data-guitar-id': string;         // Instance ID: '123'
  
  // Actions
  'data-guitar-action': 
    | 'get'      // Fetch and render single object
    | 'list'     // Fetch and render multiple objects
    | 'create'   // Create new object
    | 'update'   // Update existing object
    | 'delete'   // Delete object
    | 'search'   // Search with debounce
    | 'refresh'; // Re-fetch and re-render
  
  // Filtering & Querying
  'data-guitar-filter': string;     // JSON filter: '{"status": "active"}'
  'data-guitar-filter-field': string; // For inputs: 'name__icontains'
  'data-guitar-order': string;      // Ordering: '-created_at'
  'data-guitar-limit': string;      // Pagination: '20'
  
  // Rendering
  'data-guitar-template': string;   // Template name: 'card'
  'data-guitar-target': string;     // CSS selector: '#chart-list'
  'data-guitar-swap': 
    | 'innerHTML'
    | 'outerHTML'
    | 'beforebegin'
    | 'afterbegin'
    | 'beforeend'
    | 'afterend'
    | 'delete'
    | 'none';
  
  // Form handling
  'data-guitar-form': string;       // Form ID to submit
  'data-guitar-data': string;       // Static data JSON
  'data-guitar-field': string;      // Field name for input
  
  // Events & Triggers
  'data-guitar-trigger': string;    // Event trigger: 'click', 'keyup delay:300ms'
  'data-guitar-confirm': string;    // Confirmation message
  
  // Loading states
  'data-guitar-loading': 'show' | 'hide' | 'disable' | 'class:loading';
  
  // Success/Error handling
  'data-guitar-on-success': string; // JS expression or event name
  'data-guitar-on-error': string;   // JS expression or event name
}
```

### Initialization

```html
<script>
  // Auto-initialize all Guitar elements
  Guitar.init();
  
  // Or with configuration
  Guitar.init({
    // Default templates directory
    templates: '/static/guitar/templates/',
    
    // Global event handlers
    onSuccess: (action, result) => console.log('Success:', action),
    onError: (action, error) => console.error('Error:', action, error),
    
    // CSRF handling
    csrfToken: '{{ csrf_token }}',
  });
</script>
```

---

## Template Organization

### Folder Structure

Templates organized by model name, making them auto-discoverable:

```
frontend/
├── src/
│   ├── guitar/
│   │   ├── client.ts
│   │   ├── models/
│   │   │   ├── Chart.ts
│   │   │   └── Dashboard.ts
│   │   └── templates/           # NEW: Templates directory
│   │       ├── chart/           # Templates for Chart model
│   │       │   ├── card.ts      # Card view
│   │       │   ├── list-item.ts # List item view
│   │       │   ├── edit.ts      # Edit form
│   │       │   ├── detail.ts    # Full detail view
│   │       │   └── delete.ts    # Delete confirmation
│   │       ├── dashboard/       # Templates for Dashboard model
│   │       │   ├── card.ts
│   │       │   ├── sidebar.ts
│   │       │   └── header.ts
│   │       └── _base/           # Shared templates
│   │           ├── empty-state.ts
│   │           ├── loading.ts
│   │           └── error.ts
```

### Template Definition

```typescript
// frontend/src/guitar/templates/chart/card.ts
import { defineTemplate, html } from '@guitar/templates';
import type { Chart } from '../../models/Chart';

export default defineTemplate<Chart>({
  name: 'card',
  
  // The render function
  render: (chart, ctx) => html`
    <div 
      class="chart-card"
      data-guitar-model="chart"
      data-guitar-id="${chart.id}"
    >
      <header class="chart-card__header">
        <h3 class="chart-card__title">${chart.name}</h3>
        <span class="chart-card__type badge">${chart.chart_type}</span>
      </header>
      
      <div class="chart-card__preview">
        ${ctx.slots?.preview || html`<div class="chart-placeholder"></div>`}
      </div>
      
      <footer class="chart-card__footer">
        <time datetime="${chart.created_at}">
          ${ctx.formatDate(chart.created_at)}
        </time>
        
        ${ctx.editable ? html`
          <div class="chart-card__actions">
            <button 
              data-guitar-action="navigate"
              data-guitar-href="/charts/${chart.id}/edit"
            >
              Edit
            </button>
            <button 
              data-guitar-action="delete"
              data-guitar-confirm="Delete ${chart.name}?"
              data-guitar-target="closest .chart-card"
              data-guitar-swap="delete"
            >
              Delete
            </button>
          </div>
        ` : ''}
      </footer>
    </div>
  `,
  
  // Optional: Styles (using Styled Components pattern)
  styles: css`
    .chart-card {
      background: white;
      border-radius: 8px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
      padding: 16px;
    }
    
    .chart-card__header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    
    .chart-card__title {
      margin: 0;
      font-size: 1.1em;
    }
  `,
});
```

### Template Registration & Discovery

```typescript
// frontend/src/guitar/templates/index.ts
// Auto-generated by Guitar CLI

import chartCard from './chart/card';
import chartListItem from './chart/list-item';
import chartEdit from './chart/edit';
import dashboardCard from './dashboard/card';
// ... more imports

export const templates = {
  chart: {
    card: chartCard,
    'list-item': chartListItem,
    edit: chartEdit,
  },
  dashboard: {
    card: dashboardCard,
  },
};

// Register with Guitar
Guitar.registerTemplates(templates);
```

### Using Templates

```typescript
// Via queryset
const html = await Chart.objects
  .filter({ dashboard_id: 1 })
  .render('card', { editable: true });

// Via static method
const html = Chart.render(chartData, 'card', { editable: true });

// Via HTML attributes
<div 
  data-guitar-action="list"
  data-guitar-model="chart"
  data-guitar-filter='{"dashboard_id": 1}'
  data-guitar-template="card"
  data-guitar-context='{"editable": true}'
>
</div>
```

---

## Event System & Interactivity

### Extending the Model Class

Add event handling capabilities to the generated model classes:

```typescript
// Auto-generated Chart class with events
export class ChartModel {
  static objects = new ChartManager();
  
  // Event listeners
  private static _listeners: Map<string, Set<Function>> = new Map();
  
  static on(event: ChartEvent, handler: Function): void {
    if (!this._listeners.has(event)) {
      this._listeners.set(event, new Set());
    }
    this._listeners.get(event)!.add(handler);
  }
  
  static off(event: ChartEvent, handler: Function): void {
    this._listeners.get(event)?.delete(handler);
  }
  
  static emit(event: ChartEvent, data: any): void {
    this._listeners.get(event)?.forEach(handler => handler(data));
  }
}

type ChartEvent = 
  | 'created'
  | 'updated'
  | 'deleted'
  | 'selected'
  | 'deselected'
  | 'clicked'
  | 'doubleClicked';
```

### DOM Event Binding

Automatically bind events based on `data-guitar-*` attributes:

```html
<div 
  class="chart-card"
  data-guitar-model="chart"
  data-guitar-id="123"
  data-guitar-on-click="select"
  data-guitar-on-dblclick="edit"
>
  <!-- Chart content -->
</div>
```

```typescript
// Initialize event bindings
Guitar.init();

// Listen for model events
Chart.on('selected', (chart) => {
  console.log('Chart selected:', chart);
  showDetailPanel(chart);
});

Chart.on('updated', (chart) => {
  // Re-render all instances of this chart
  Guitar.refresh('[data-guitar-model="chart"][data-guitar-id="' + chart.id + '"]');
});
```

### Custom Actions

Define custom actions beyond CRUD:

```typescript
// Define custom action
Chart.registerAction('duplicate', async (chart) => {
  const duplicate = await Chart.objects.create({
    ...chart,
    name: `${chart.name} (copy)`,
  });
  Chart.emit('created', duplicate);
  return duplicate;
});

// Use in HTML
<button 
  data-guitar-action="duplicate"
  data-guitar-model="chart"
  data-guitar-id="123"
  data-guitar-on-success="refresh:#chart-list"
>
  Duplicate
</button>
```

### Keyboard Shortcuts

```typescript
// Register keyboard shortcuts
Guitar.shortcuts({
  'chart': {
    'e': 'edit',           // 'e' to edit selected chart
    'Delete': 'delete',    // Delete key to delete
    'd': 'duplicate',      // 'd' to duplicate
    'Escape': 'deselect',  // Escape to deselect
  },
});
```

---

## Auto-Save & Easy Editing Patterns

### Inline Editing

Transform any displayed field into an editable field:

```typescript
// Template with inline editing
export default defineTemplate<Chart>({
  name: 'editable-card',
  
  render: (chart, ctx) => html`
    <div class="chart-card" data-guitar-model="chart" data-guitar-id="${chart.id}">
      
      <!-- Inline editable title -->
      <h3 
        data-guitar-field="name"
        data-guitar-editable
        data-guitar-autosave
      >
        ${chart.name}
      </h3>
      
      <!-- Select field -->
      <select 
        data-guitar-field="chart_type"
        data-guitar-autosave
      >
        <option value="bar" ${chart.chart_type === 'bar' ? 'selected' : ''}>Bar</option>
        <option value="line" ${chart.chart_type === 'line' ? 'selected' : ''}>Line</option>
        <option value="pie" ${chart.chart_type === 'pie' ? 'selected' : ''}>Pie</option>
      </select>
      
    </div>
  `,
});
```

### Auto-Save Configuration

```typescript
Guitar.configure({
  autoSave: {
    enabled: true,
    debounce: 1000,  // Wait 1 second after last change
    
    // Show saving indicator
    indicator: {
      saving: html`<span class="save-indicator saving">Saving...</span>`,
      saved: html`<span class="save-indicator saved">Saved</span>`,
      error: html`<span class="save-indicator error">Error saving</span>`,
    },
    
    // Retry on failure
    retry: {
      attempts: 3,
      delay: 1000,
    },
    
    // Conflict resolution
    onConflict: async (local, remote) => {
      // Show diff and let user choose
      return await showConflictDialog(local, remote);
    },
  },
});
```

### Form Patterns

```typescript
// Quick edit mode - transforms view into form
const EditableChart = Guitar.Editable({
  model: Chart,
  viewTemplate: 'card',
  editTemplate: 'edit-form',
  
  // Toggle on double-click
  editTrigger: 'dblclick',
  
  // Save on blur or Ctrl+Enter
  saveTrigger: ['blur', 'ctrl+enter'],
  
  // Cancel on Escape
  cancelTrigger: 'escape',
  
  // Validate before save
  validate: (data) => {
    if (!data.name?.trim()) {
      return { name: 'Name is required' };
    }
    return null;
  },
});
```

### Optimistic Updates

```typescript
Guitar.configure({
  optimisticUpdates: true,  // Update UI immediately, rollback on error
});

// Or per-action
<button 
  data-guitar-action="update"
  data-guitar-model="chart"
  data-guitar-id="123"
  data-guitar-data='{"starred": true}'
  data-guitar-optimistic
>
  ⭐ Star
</button>
```

---

## Framework Integrations

### Vanilla JavaScript

Works out of the box with no framework:

```html
<!DOCTYPE html>
<html>
<head>
  <script src="/static/guitar/guitar.min.js"></script>
</head>
<body>
  <div id="app">
    <!-- Declarative Guitar elements -->
    <div 
      data-guitar-action="list"
      data-guitar-model="chart"
      data-guitar-template="card"
    ></div>
  </div>
  
  <script>
    Guitar.init({ baseUrl: '/guitar/' });
  </script>
</body>
</html>
```

### React Integration

Provide React hooks and components:

```tsx
// React hooks
import { useGuitar, useGuitarQuery, useGuitarMutation } from '@guitar/react';

const ChartList: React.FC<{ dashboardId: number }> = ({ dashboardId }) => {
  // Query with familiar Django syntax
  const { data: charts, loading, error } = useGuitarQuery(
    Chart.objects.filter({ dashboard_id: dashboardId }).order_by('-created_at')
  );
  
  // Mutations
  const [deleteChart] = useGuitarMutation(Chart.objects.delete);
  
  if (loading) return <Loading />;
  if (error) return <Error error={error} />;
  
  return (
    <div className="chart-list">
      {charts.map(chart => (
        <GuitarRender 
          key={chart.id}
          model={Chart}
          data={chart}
          template="card"
          context={{ editable: true }}
        />
      ))}
    </div>
  );
};
```

```tsx
// Guitar components
import { GuitarList, GuitarDetail, GuitarEdit } from '@guitar/react';

// ListView equivalent
<GuitarList
  model={Chart}
  filter={{ dashboard_id: 1 }}
  template="card"
  emptyState={<EmptyCharts />}
  pagination={{ pageSize: 20 }}
/>

// DetailView equivalent
<GuitarDetail
  model={Chart}
  id={chartId}
  template="full"
  selectRelated={['dashboard']}
/>

// EditView equivalent
<GuitarEdit
  model={Chart}
  id={chartId}
  fields={['name', 'chart_type', 'query']}
  widgets={{ query: CodeEditor }}
  onSuccess={(chart) => navigate(`/charts/${chart.id}`)}
/>
```

### Vue Integration

```vue
<template>
  <GuitarList
    :model="Chart"
    :filter="{ dashboard_id: dashboardId }"
    template="card"
  >
    <template #empty>
      <EmptyCharts />
    </template>
  </GuitarList>
</template>

<script setup>
import { Chart } from '@/guitar';
import { GuitarList } from '@guitar/vue';

const props = defineProps(['dashboardId']);
</script>
```

### Svelte Integration

```svelte
<script>
  import { Chart } from '$lib/guitar';
  import { GuitarList } from '@guitar/svelte';
  
  export let dashboardId;
</script>

<GuitarList
  model={Chart}
  filter={{ dashboard_id: dashboardId }}
  template="card"
  let:charts
>
  {#each charts as chart}
    <GuitarRender model={Chart} data={chart} template="card" />
  {/each}
  
  <svelte:fragment slot="empty">
    <EmptyCharts />
  </svelte:fragment>
</GuitarList>
```

### HTMX Integration

For Django developers who already use HTMX:

```html
<!-- Use Guitar for data, HTMX for swapping -->
<div 
  hx-get="/guitar/chart/?dashboard_id=1&_template=card"
  hx-trigger="load"
  hx-target="this"
>
  Loading...
</div>

<!-- Guitar handles the rendering, HTMX handles the DOM -->
<button 
  hx-post="/guitar/chart/"
  hx-vals='{"name": "New Chart", "dashboard_id": 1}'
  hx-target="#chart-list"
  hx-swap="afterbegin"
  hx-headers='{"X-Guitar-Template": "card"}'
>
  Add Chart
</button>
```

---

## Todo App Example

Let's design how a simple todo app would work with Guitar Frontend:

### Django Model

```python
# models.py
from guitar import GuitarModel

class Todo(GuitarModel, models.Model):
    title = models.CharField(max_length=255)
    completed = models.BooleanField(default=False)
    priority = models.CharField(max_length=20, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], default='medium')
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    
    class Meta:
        ordering = ['-priority', 'due_date', '-created_at']
    
    class GuitarMeta:
        fields = ['id', 'title', 'completed', 'priority', 'due_date', 'created_at']
        writable_fields = ['title', 'completed', 'priority', 'due_date']
        filterable_fields = ['completed', 'priority', 'due_date']
        searchable_fields = ['title']
        
        # NEW: Frontend configuration
        templates = {
            'list-item': {
                'editable': True,
                'autosave': True,
            },
            'card': {},
            'edit': {
                'widgets': {
                    'due_date': 'date-picker',
                    'priority': 'radio-group',
                },
            },
        }
    
    class GuitarManager:
        def filter_read(self, request, queryset):
            return queryset.filter(user=request.user)
        
        def check_create(self, request, data):
            data['user_id'] = request.user.id
            return data
```

### Templates

```typescript
// templates/todo/list-item.ts
export default defineTemplate<Todo>({
  name: 'list-item',
  
  render: (todo, ctx) => html`
    <li 
      class="todo-item ${todo.completed ? 'completed' : ''} priority-${todo.priority}"
      data-guitar-model="todo"
      data-guitar-id="${todo.id}"
      data-guitar-on-click="select"
    >
      <!-- Checkbox for completion -->
      <input 
        type="checkbox"
        ${todo.completed ? 'checked' : ''}
        data-guitar-field="completed"
        data-guitar-autosave
      />
      
      <!-- Editable title -->
      <span 
        class="todo-title"
        data-guitar-field="title"
        data-guitar-editable
        data-guitar-autosave
      >
        ${todo.title}
      </span>
      
      <!-- Priority badge -->
      <span class="todo-priority badge badge-${todo.priority}">
        ${todo.priority}
      </span>
      
      <!-- Due date -->
      ${todo.due_date ? html`
        <time class="todo-due" datetime="${todo.due_date}">
          ${ctx.formatDate(todo.due_date, 'relative')}
        </time>
      ` : ''}
      
      <!-- Actions -->
      <div class="todo-actions">
        <button 
          data-guitar-action="delete"
          data-guitar-confirm="Delete this todo?"
          data-guitar-target="closest .todo-item"
          data-guitar-swap="delete"
        >
          ✕
        </button>
      </div>
    </li>
  `,
});
```

```typescript
// templates/todo/edit.ts
export default defineTemplate<Todo>({
  name: 'edit',
  
  render: (todo, ctx) => html`
    <form 
      class="todo-edit"
      data-guitar-model="todo"
      data-guitar-id="${todo?.id || 'new'}"
      data-guitar-action="${todo ? 'update' : 'create'}"
      data-guitar-on-success="close"
    >
      <div class="form-group">
        <label for="title">Title</label>
        <input 
          type="text"
          id="title"
          name="title"
          value="${todo?.title || ''}"
          required
          autofocus
        />
      </div>
      
      <div class="form-group">
        <label>Priority</label>
        <div class="radio-group" data-guitar-field="priority">
          ${['low', 'medium', 'high'].map(p => html`
            <label>
              <input 
                type="radio" 
                name="priority" 
                value="${p}"
                ${(todo?.priority || 'medium') === p ? 'checked' : ''}
              />
              ${p}
            </label>
          `)}
        </div>
      </div>
      
      <div class="form-group">
        <label for="due_date">Due Date</label>
        <input 
          type="date"
          id="due_date"
          name="due_date"
          value="${todo?.due_date || ''}"
        />
      </div>
      
      <div class="form-actions">
        <button type="button" data-guitar-action="cancel">Cancel</button>
        <button type="submit">Save</button>
      </div>
    </form>
  `,
});
```

### Full App HTML

```html
<!DOCTYPE html>
<html>
<head>
  <title>Guitar Todo</title>
  <link rel="stylesheet" href="/static/todo/styles.css">
  <script src="/static/guitar/guitar.min.js"></script>
</head>
<body>
  <div class="todo-app">
    <!-- Sidebar with list -->
    <aside class="todo-sidebar">
      <header>
        <h1>My Todos</h1>
        
        <!-- Search -->
        <input 
          type="search"
          placeholder="Search todos..."
          data-guitar-action="search"
          data-guitar-model="todo"
          data-guitar-filter-field="title__icontains"
          data-guitar-target="#todo-list"
          data-guitar-template="list-item"
          data-guitar-trigger="keyup changed delay:300ms"
        />
      </header>
      
      <!-- Filter tabs -->
      <nav class="todo-filters">
        <button 
          class="active"
          data-guitar-action="list"
          data-guitar-model="todo"
          data-guitar-target="#todo-list"
          data-guitar-template="list-item"
        >
          All
        </button>
        <button 
          data-guitar-action="list"
          data-guitar-model="todo"
          data-guitar-filter='{"completed": false}'
          data-guitar-target="#todo-list"
          data-guitar-template="list-item"
        >
          Active
        </button>
        <button 
          data-guitar-action="list"
          data-guitar-model="todo"
          data-guitar-filter='{"completed": true}'
          data-guitar-target="#todo-list"
          data-guitar-template="list-item"
        >
          Completed
        </button>
      </nav>
      
      <!-- Todo list -->
      <ul 
        id="todo-list"
        data-guitar-action="list"
        data-guitar-model="todo"
        data-guitar-template="list-item"
        data-guitar-trigger="load"
      >
        <!-- Auto-populated on load -->
      </ul>
      
      <!-- Add todo -->
      <footer>
        <form 
          data-guitar-action="create"
          data-guitar-model="todo"
          data-guitar-target="#todo-list"
          data-guitar-swap="afterbegin"
          data-guitar-template="list-item"
          data-guitar-on-success="reset"
        >
          <input 
            type="text" 
            name="title" 
            placeholder="Add a todo..."
            required
          />
          <button type="submit">Add</button>
        </form>
      </footer>
    </aside>
    
    <!-- Main content - detail/edit view -->
    <main class="todo-main">
      <div 
        id="todo-detail"
        data-guitar-listen="todo:selected"
        data-guitar-action="get"
        data-guitar-model="todo"
        data-guitar-template="detail"
      >
        <div class="empty-state">
          <p>Select a todo to view details</p>
        </div>
      </div>
    </main>
  </div>
  
  <script>
    Guitar.init({
      baseUrl: '/guitar/',
      
      // Auto-save config
      autoSave: {
        enabled: true,
        debounce: 500,
      },
      
      // Keyboard shortcuts
      shortcuts: {
        'todo': {
          'n': () => document.querySelector('[name="title"]').focus(),
          'e': 'edit',
          'Delete': 'delete',
          'Space': 'toggle:completed',
        },
      },
    });
    
    // Listen for selection
    Todo.on('selected', (todo) => {
      document.querySelectorAll('.todo-item').forEach(el => {
        el.classList.toggle('selected', el.dataset.guitarId === String(todo.id));
      });
    });
  </script>
</body>
</html>
```

### What This Achieves

With minimal JavaScript, we have:

1. ✅ **List view** with filtering (All/Active/Completed)
2. ✅ **Search** with debounce
3. ✅ **Inline editing** of title (click to edit)
4. ✅ **Toggle completion** via checkbox (auto-saved)
5. ✅ **Quick add** via form at bottom
6. ✅ **Detail view** on selection
7. ✅ **Delete** with confirmation
8. ✅ **Keyboard shortcuts** for power users
9. ✅ **Auto-save** on all edits

All using declarative HTML attributes - the Django developer's dream!

---

## Proposed Architecture

### Package Structure

```
@guitar/core          - Core templating and rendering engine
@guitar/templates     - Template utilities and base templates
@guitar/forms         - Form handling and validation
@guitar/htmx          - HTMX-style attribute processing
@guitar/react         - React bindings
@guitar/vue           - Vue bindings
@guitar/svelte        - Svelte bindings
```

### Core Module Structure

```
frontend/src/guitar/
├── core/
│   ├── template-engine.ts   # Template rendering
│   ├── event-system.ts      # Model event emitter
│   ├── attribute-parser.ts  # Parse data-guitar-* attributes
│   └── auto-save.ts         # Auto-save functionality
├── forms/
│   ├── validation.ts        # Client-side validation
│   ├── widgets/             # Widget implementations
│   │   ├── text-input.ts
│   │   ├── select.ts
│   │   ├── date-picker.ts
│   │   └── ...
│   └── form-builder.ts      # Form generation
├── views/
│   ├── list-view.ts         # ListView component
│   ├── detail-view.ts       # DetailView component
│   ├── edit-view.ts         # EditView component
│   └── delete-view.ts       # DeleteView component
├── templates/
│   ├── index.ts             # Template registry
│   └── base/                # Base templates
├── client.ts                # Existing API client
├── models/                  # Generated models
└── index.ts                 # Main exports
```

### Generation Command Updates

Extend `generate_guitar_client` to also generate templates:

```bash
python manage.py generate_guitar_client --templates
```

This would:
1. Generate base template files for each model
2. Generate template type definitions
3. Generate template registry

---

## Implementation Roadmap

### Phase 1: Core Template System
- [ ] Template definition format (`defineTemplate`)
- [ ] Template registry and discovery
- [ ] Basic `.render()` method on querysets
- [ ] Server-side render endpoint

### Phase 2: Attribute System (HTMX-like)
- [ ] `data-guitar-*` attribute parser
- [ ] Core actions: get, list, create, update, delete
- [ ] Target and swap handling
- [ ] Loading states

### Phase 3: Forms & Editing
- [ ] Widget system
- [ ] Validation integration
- [ ] Inline editing (`data-guitar-editable`)
- [ ] Auto-save functionality

### Phase 4: Event System
- [ ] Model event emitter
- [ ] DOM event binding
- [ ] Custom actions
- [ ] Keyboard shortcuts

### Phase 5: Framework Integrations
- [ ] React hooks and components
- [ ] Vue composables and components
- [ ] Svelte bindings
- [ ] HTMX integration helpers

### Phase 6: Polish & DX
- [ ] CLI for template scaffolding
- [ ] DevTools integration
- [ ] Documentation and examples
- [ ] Performance optimizations

---

## Open Questions

1. **Template Syntax** - Use tagged template literals (`html\`...\``) or a template DSL?
   
2. **CSS Strategy** - Styled Components, CSS Modules, or plain CSS classes?

3. **Build Integration** - How to integrate with existing frontend build tools?

4. **Server-Side Priority** - Should SSR be the default for better Django alignment?

5. **Reactivity** - Add a reactive layer for automatic re-rendering on data changes?

6. **State Management** - How to handle shared state between components?

---

## Conclusion

This research proposes a Django-like frontend framework that:

1. **Feels Familiar** - Templates, forms, and CBV patterns that Django developers know
2. **Minimizes JavaScript** - HTMX-inspired declarative attributes
3. **Enables Rapid Development** - Auto-generated templates and forms
4. **Stays Flexible** - Works standalone or with any framework
5. **Maintains Type Safety** - TypeScript where it matters

The goal is to let Django developers build modern, interactive frontends without leaving their comfort zone - bringing the "batteries included" philosophy to the frontend.
