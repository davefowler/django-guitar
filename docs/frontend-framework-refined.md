# Guitar Frontend Framework - Refined Proposal

Based on feedback, this document refines the initial research with more concrete proposals.

## Table of Contents

1. [Rendering Strategy Refined](#rendering-strategy-refined)
2. [Template Files (HTML + Optional TS)](#template-files-html--optional-ts)
3. [Custom Elements for Views](#custom-elements-for-views)
4. [Event System & Custom Events](#event-system--custom-events)
5. [Central Object Registry](#central-object-registry)
6. [Wiring Up Search/Refresh](#wiring-up-searchrefresh)
7. [Revised Architecture](#revised-architecture)

---

## Rendering Strategy Refined

### The Problem with Network Roundtrips

Original proposal had two issues:
1. Extra network request just for rendering
2. Hard to integrate with React/Vue virtual DOM

### Solution: Render Field on Response

Instead of a separate render endpoint, add rendered HTML as a field in the normal API response:

```typescript
// Request
const charts = await Chart.objects
  .filter({ dashboard_id: 1 })
  .render('card', 'list-item')  // Request these templates
  .all();

// Response - each object has a _renders field
[
  {
    id: 1,
    name: "Sales Chart",
    chart_type: "bar",
    // ... other fields
    _renders: {
      card: '<div class="chart-card">...</div>',
      'list-item': '<li class="chart-list-item">...</li>',
    }
  },
  // ...
]
```

### Backend Implementation

```python
# guitar/router.py - Enhanced list endpoint

def list_items(request: HttpRequest) -> List[Dict[str, Any]]:
    # ... existing filter/query logic ...
    
    # Check for render templates requested
    render_templates = request.GET.get('_render', '').split(',')
    render_templates = [t.strip() for t in render_templates if t.strip()]
    
    results = []
    for obj in queryset:
        data = self._serialize_instance(obj, model_class)
        
        # Add rendered templates if requested
        if render_templates:
            data['_renders'] = {}
            for template_name in render_templates:
                template_path = f'guitar/{model_name}/{template_name}.html'
                try:
                    html = render_to_string(template_path, {
                        model_name: obj,
                        'request': request,
                    })
                    data['_renders'][template_name] = html
                except TemplateDoesNotExist:
                    pass
        
        results.append(data)
    
    return results
```

### TypeScript Client Update

```typescript
// In GuitarManager class
render(...templates: string[]): this {
  const cloned = this._clone();
  cloned._renderTemplates = templates;
  return cloned;
}

private _buildQueryParams(): QueryParams {
  const params: QueryParams = { ...this._filters };
  
  // ... existing params ...
  
  if (this._renderTemplates?.length) {
    params._render = this._renderTemplates.join(',');
  }
  
  return params;
}
```

### Usage Patterns

```typescript
// Get data with pre-rendered card template
const charts = await Chart.objects
  .filter({ dashboard_id: 1 })
  .render('card')
  .all();

// Use the rendered HTML
charts.forEach(chart => {
  container.innerHTML += chart._renders.card;
});

// Or access via helper
const html = Chart.getRenderedHtml(chart, 'card');
```

### Client-Side Rendering Fallback

For updates and when server render isn't available, we need a JS template engine that's compatible with Django templates:

```typescript
// If _renders.card doesn't exist, render client-side
const html = Chart.getRenderedHtml(chart, 'card');

// Implementation
static getRenderedHtml(instance: Chart, template: string): string {
  // Check for server-rendered version first
  if (instance._renders?.[template]) {
    return instance._renders[template];
  }
  
  // Fall back to client-side rendering
  return GuitarTemplates.render('chart', template, instance);
}
```

### JS-Compatible Django Templates

For client-side rendering, we need a lightweight Django template subset in JS. Options:

1. **Nunjucks** - Very similar to Django/Jinja2 syntax
2. **Custom lightweight parser** - Just handle `{{ var }}`, `{% if %}`, `{% for %}`
3. **Build-time compilation** - Compile Django templates to JS functions

Recommendation: **Nunjucks** with a thin wrapper:

```typescript
// guitar/template-engine.ts
import nunjucks from 'nunjucks';

// Configure to be Django-compatible
const env = nunjucks.configure({
  autoescape: true,
});

// Add Django-like filters
env.addFilter('date', (val, format) => formatDate(val, format));
env.addFilter('default', (val, def) => val ?? def);
env.addFilter('truncatewords', (val, count) => truncateWords(val, count));

export const renderTemplate = (
  templateString: string, 
  context: Record<string, unknown>
): string => {
  return env.renderString(templateString, context);
};
```

This means **one template file works on both backend and frontend**:

```html
<!-- guitar/templates/chart/card.html -->
<!-- Works in Django AND in browser via Nunjucks -->
<div class="chart-card" data-guitar-model="chart" data-guitar-id="{{ chart.id }}">
  <h3>{{ chart.name }}</h3>
  <span class="chart-type">{{ chart.chart_type }}</span>
  
  {% if chart.created_at %}
    <time datetime="{{ chart.created_at }}">
      {{ chart.created_at|date:"M d, Y" }}
    </time>
  {% endif %}
  
  {% for tag in chart.tags %}
    <span class="tag">{{ tag }}</span>
  {% endfor %}
</div>
```

---

## Template Files (HTML + Optional TS)

### File Structure

Templates are plain HTML files, with optional TypeScript for interactivity:

```
guitar/
├── templates/
│   ├── chart/
│   │   ├── card.html           # Template (required)
│   │   ├── card.ts             # Interactivity (optional)
│   │   ├── list-item.html
│   │   ├── list-item.ts
│   │   ├── edit.html
│   │   └── edit.ts
│   └── todo/
│       ├── card.html
│       └── card.ts
```

### Template File (card.html)

Pure HTML with Django/Nunjucks-compatible template syntax:

```html
<!-- guitar/templates/chart/card.html -->
<div class="chart-card" 
     data-guitar-model="chart" 
     data-guitar-id="{{ chart.id }}"
     data-guitar-component="chart-card">
  
  <header class="chart-card__header">
    <h3 class="chart-card__title" data-guitar-field="name" data-guitar-editable>
      {{ chart.name }}
    </h3>
    <span class="chart-card__type badge">{{ chart.chart_type }}</span>
  </header>
  
  <div class="chart-card__preview">
    <!-- Chart visualization goes here -->
  </div>
  
  <footer class="chart-card__footer">
    <time datetime="{{ chart.created_at }}">
      {{ chart.created_at|date:"M d, Y" }}
    </time>
    
    <div class="chart-card__actions">
      <button data-action="edit">Edit</button>
      <button data-action="delete">Delete</button>
    </div>
  </footer>
</div>
```

### Interactivity File (card.ts)

Optional TypeScript file that enhances the template with behavior:

```typescript
// guitar/templates/chart/card.ts
import { defineComponent } from '@guitar/components';
import type { Chart } from '../models/Chart';

export default defineComponent<Chart>({
  // Component name - matches data-guitar-component attribute
  name: 'chart-card',
  
  // Called when component is mounted to DOM
  onMount(element, chart) {
    console.log('Chart card mounted:', chart.id);
  },
  
  // Called when component is removed from DOM
  onUnmount(element, chart) {
    console.log('Chart card unmounted:', chart.id);
  },
  
  // Called when the underlying data changes
  onUpdate(element, oldChart, newChart) {
    // Could do animations, etc.
    element.classList.add('updating');
    setTimeout(() => element.classList.remove('updating'), 300);
  },
  
  // Action handlers - triggered by data-action attributes
  actions: {
    edit(element, chart, event) {
      Guitar.navigate(`/charts/${chart.id}/edit`);
    },
    
    delete(element, chart, event) {
      if (confirm(`Delete "${chart.name}"?`)) {
        Chart.objects.filter({ id: chart.id }).delete();
      }
    },
  },
  
  // Custom event handlers
  on: {
    click(element, chart, event) {
      Chart.emit('selected', chart);
    },
    
    dblclick(element, chart, event) {
      this.actions.edit(element, chart, event);
    },
  },
});
```

### How It's Wired Up

The Guitar runtime automatically:

1. **Loads templates** - Fetches HTML template files (or bundles them at build time)
2. **Registers components** - Finds matching `.ts` files and registers them
3. **Binds on render** - When HTML is inserted, finds `data-guitar-component` elements and initializes them

```typescript
// guitar/runtime.ts

// Template registry
const templates: Map<string, string> = new Map();
const components: Map<string, ComponentDefinition> = new Map();

// Load a template
export const loadTemplate = async (model: string, name: string): Promise<string> => {
  const key = `${model}/${name}`;
  
  if (!templates.has(key)) {
    // In dev: fetch from server
    // In prod: already bundled
    const response = await fetch(`/guitar/templates/${key}.html`);
    templates.set(key, await response.text());
  }
  
  return templates.get(key)!;
};

// Register a component
export const registerComponent = (definition: ComponentDefinition): void => {
  components.set(definition.name, definition);
};

// Initialize components in a container
export const initComponents = (container: Element): void => {
  const elements = container.querySelectorAll('[data-guitar-component]');
  
  elements.forEach(element => {
    const componentName = element.getAttribute('data-guitar-component');
    const component = components.get(componentName);
    
    if (component) {
      const model = element.getAttribute('data-guitar-model');
      const id = element.getAttribute('data-guitar-id');
      
      // Get the data from registry
      const data = GuitarRegistry.get(model, id);
      
      // Initialize
      component.onMount?.(element, data);
      
      // Bind actions
      bindActions(element, component, data);
      
      // Bind events
      bindEvents(element, component, data);
    }
  });
};
```

### Build-Time Template Bundling

For production, templates are bundled at build time:

```typescript
// guitar/templates/index.ts (auto-generated)
export const templates = {
  chart: {
    card: `<div class="chart-card" data-guitar-model="chart"...`,
    'list-item': `<li class="chart-list-item"...`,
  },
  todo: {
    card: `<div class="todo-card"...`,
  },
};

// Components auto-imported
import chartCard from './chart/card';
import chartListItem from './chart/list-item';
import todoCard from './todo/card';

export const components = {
  'chart-card': chartCard,
  'chart-list-item': chartListItem,
  'todo-card': todoCard,
};
```

---

## Custom Elements for Views

### The Vision

Generic views as custom elements - declarative, composable, Django-like:

```html
<guitar-list 
  model="chart" 
  template="card"
  filter='{"dashboard_id": 1}'
  order-by="-created_at"
  paginate-by="20"
></guitar-list>

<guitar-detail
  model="chart"
  item-id="123"
  template="full"
></guitar-detail>

<guitar-edit
  model="chart"
  item-id="123"
  fields="name,chart_type,query"
  auto-save
></guitar-edit>
```

### ListView Custom Element

```typescript
// guitar/elements/guitar-list.ts
import { GuitarRegistry } from '../registry';

class GuitarListElement extends HTMLElement {
  private _queryset: any = null;
  private _unsubscribe: (() => void) | null = null;
  
  // Observed attributes
  static get observedAttributes() {
    return ['model', 'template', 'filter', 'order-by', 'paginate-by', 'search-field'];
  }
  
  connectedCallback() {
    this.load();
    this.subscribeToUpdates();
  }
  
  disconnectedCallback() {
    this._unsubscribe?.();
  }
  
  attributeChangedCallback(name: string, oldValue: string, newValue: string) {
    if (oldValue !== newValue) {
      this.load();
    }
  }
  
  async load() {
    const model = this.getAttribute('model');
    const template = this.getAttribute('template') || 'list-item';
    const filter = JSON.parse(this.getAttribute('filter') || '{}');
    const orderBy = this.getAttribute('order-by');
    const limit = parseInt(this.getAttribute('paginate-by') || '50');
    
    // Show loading state
    this.classList.add('loading');
    
    try {
      // Get model class from registry
      const ModelClass = GuitarRegistry.getModel(model);
      
      // Build queryset
      let qs = ModelClass.objects.filter(filter);
      if (orderBy) {
        qs = qs.order_by(...orderBy.split(','));
      }
      qs = qs.limit(limit).render(template);
      
      // Fetch data
      const items = await qs.all();
      
      // Register items in global registry
      items.forEach(item => GuitarRegistry.set(model, item.id, item));
      
      // Render
      this.innerHTML = items.map(item => item._renders[template]).join('');
      
      // Initialize components
      Guitar.initComponents(this);
      
    } catch (error) {
      this.innerHTML = `<div class="error">Error loading ${model}s</div>`;
    } finally {
      this.classList.remove('loading');
    }
  }
  
  subscribeToUpdates() {
    const model = this.getAttribute('model');
    const ModelClass = GuitarRegistry.getModel(model);
    
    // Re-render individual items on update
    const handleUpdate = (item: any) => {
      const element = this.querySelector(
        `[data-guitar-model="${model}"][data-guitar-id="${item.id}"]`
      );
      if (element && item._renders) {
        const template = this.getAttribute('template') || 'list-item';
        element.outerHTML = item._renders[template];
        Guitar.initComponents(this);
      }
    };
    
    // Add new items on create
    const handleCreate = (item: any) => {
      // Reload to get proper ordering
      this.load();
    };
    
    // Remove items on delete
    const handleDelete = (item: any) => {
      const element = this.querySelector(
        `[data-guitar-model="${model}"][data-guitar-id="${item.id}"]`
      );
      element?.remove();
    };
    
    ModelClass.on('updated', handleUpdate);
    ModelClass.on('created', handleCreate);
    ModelClass.on('deleted', handleDelete);
    
    this._unsubscribe = () => {
      ModelClass.off('updated', handleUpdate);
      ModelClass.off('created', handleCreate);
      ModelClass.off('deleted', handleDelete);
    };
  }
  
  // Public method to trigger refresh
  refresh() {
    this.load();
  }
}

customElements.define('guitar-list', GuitarListElement);
```

### DetailView Custom Element

```typescript
// guitar/elements/guitar-detail.ts
class GuitarDetailElement extends HTMLElement {
  static get observedAttributes() {
    return ['model', 'item-id', 'template'];
  }
  
  connectedCallback() {
    this.load();
    this.subscribeToUpdates();
  }
  
  async load() {
    const model = this.getAttribute('model');
    const id = this.getAttribute('item-id');
    const template = this.getAttribute('template') || 'detail';
    
    if (!id) {
      this.innerHTML = '<div class="empty">No item selected</div>';
      return;
    }
    
    this.classList.add('loading');
    
    try {
      const ModelClass = GuitarRegistry.getModel(model);
      const item = await ModelClass.objects.render(template).get({ id: parseInt(id) });
      
      GuitarRegistry.set(model, item.id, item);
      this.innerHTML = item._renders[template];
      Guitar.initComponents(this);
      
    } catch (error) {
      this.innerHTML = `<div class="error">Error loading ${model}</div>`;
    } finally {
      this.classList.remove('loading');
    }
  }
  
  subscribeToUpdates() {
    const model = this.getAttribute('model');
    const ModelClass = GuitarRegistry.getModel(model);
    
    const handleUpdate = (item: any) => {
      if (String(item.id) === this.getAttribute('item-id')) {
        this.load();
      }
    };
    
    ModelClass.on('updated', handleUpdate);
    // Store for cleanup
  }
}

customElements.define('guitar-detail', GuitarDetailElement);
```

### EditView Custom Element

```typescript
// guitar/elements/guitar-edit.ts
class GuitarEditElement extends HTMLElement {
  private _autoSaveTimeout: number | null = null;
  
  static get observedAttributes() {
    return ['model', 'item-id', 'fields', 'auto-save', 'auto-save-delay'];
  }
  
  get autoSave(): boolean {
    return this.hasAttribute('auto-save');
  }
  
  get autoSaveDelay(): number {
    return parseInt(this.getAttribute('auto-save-delay') || '1000');
  }
  
  connectedCallback() {
    this.load();
  }
  
  async load() {
    const model = this.getAttribute('model');
    const id = this.getAttribute('item-id');
    const fieldsAttr = this.getAttribute('fields');
    const fields = fieldsAttr ? fieldsAttr.split(',') : null;
    
    const ModelClass = GuitarRegistry.getModel(model);
    const item = id ? await ModelClass.objects.get({ id: parseInt(id) }) : null;
    
    // Generate form HTML
    this.innerHTML = this.renderForm(ModelClass, item, fields);
    
    // Bind form events
    this.bindFormEvents();
  }
  
  renderForm(ModelClass: any, item: any, fields: string[] | null): string {
    const meta = ModelClass._meta;  // Field metadata from generated client
    const editableFields = fields || meta.writableFields;
    
    let html = `<form class="guitar-edit-form" data-guitar-model="${ModelClass._name}">`;
    
    if (item) {
      html += `<input type="hidden" name="id" value="${item.id}">`;
    }
    
    for (const field of editableFields) {
      const fieldMeta = meta.fields[field];
      html += this.renderField(field, fieldMeta, item?.[field]);
    }
    
    // Only show submit button if not auto-save
    if (!this.autoSave) {
      html += `<button type="submit">Save</button>`;
    } else {
      html += `<div class="save-indicator" hidden></div>`;
    }
    
    html += `</form>`;
    return html;
  }
  
  renderField(name: string, meta: any, value: any): string {
    // Field rendering based on type and widget
    const widget = meta.widget || this.getDefaultWidget(meta.type);
    
    switch (widget) {
      case 'textarea':
        return `
          <div class="form-field">
            <label for="${name}">${meta.label || name}</label>
            <textarea name="${name}" id="${name}">${value || ''}</textarea>
          </div>
        `;
      
      case 'select':
        const options = meta.choices.map((c: any) => 
          `<option value="${c[0]}" ${value === c[0] ? 'selected' : ''}>${c[1]}</option>`
        ).join('');
        return `
          <div class="form-field">
            <label for="${name}">${meta.label || name}</label>
            <select name="${name}" id="${name}">${options}</select>
          </div>
        `;
      
      case 'checkbox':
        return `
          <div class="form-field">
            <label>
              <input type="checkbox" name="${name}" ${value ? 'checked' : ''}>
              ${meta.label || name}
            </label>
          </div>
        `;
      
      default:
        return `
          <div class="form-field">
            <label for="${name}">${meta.label || name}</label>
            <input type="text" name="${name}" id="${name}" value="${value || ''}">
          </div>
        `;
    }
  }
  
  bindFormEvents() {
    const form = this.querySelector('form');
    if (!form) return;
    
    if (this.autoSave) {
      // Auto-save on change
      form.addEventListener('input', (e) => {
        this.scheduleAutoSave();
      });
    } else {
      // Submit on form submit
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        this.save();
      });
    }
  }
  
  scheduleAutoSave() {
    if (this._autoSaveTimeout) {
      clearTimeout(this._autoSaveTimeout);
    }
    
    this.showIndicator('saving');
    
    this._autoSaveTimeout = window.setTimeout(() => {
      this.save();
    }, this.autoSaveDelay);
  }
  
  async save() {
    const form = this.querySelector('form') as HTMLFormElement;
    const formData = new FormData(form);
    const data: Record<string, any> = {};
    
    formData.forEach((value, key) => {
      if (key !== 'id') {
        data[key] = value;
      }
    });
    
    const model = this.getAttribute('model');
    const id = formData.get('id');
    const ModelClass = GuitarRegistry.getModel(model);
    
    try {
      let result;
      if (id) {
        // Update existing
        result = await ModelClass.objects.filter({ id: parseInt(id as string) }).update(data);
        ModelClass.emit('updated', result[0]);
      } else {
        // Create new
        result = await ModelClass.objects.create(data);
        ModelClass.emit('created', result);
      }
      
      this.showIndicator('saved');
      this.dispatchEvent(new CustomEvent('guitar-save', { detail: result }));
      
    } catch (error) {
      this.showIndicator('error');
      this.dispatchEvent(new CustomEvent('guitar-error', { detail: error }));
    }
  }
  
  showIndicator(state: 'saving' | 'saved' | 'error') {
    const indicator = this.querySelector('.save-indicator');
    if (!indicator) return;
    
    indicator.removeAttribute('hidden');
    indicator.textContent = state === 'saving' ? 'Saving...' 
                          : state === 'saved' ? 'Saved' 
                          : 'Error saving';
    indicator.className = `save-indicator ${state}`;
    
    if (state === 'saved') {
      setTimeout(() => indicator.setAttribute('hidden', ''), 2000);
    }
  }
}

customElements.define('guitar-edit', GuitarEditElement);
```

### Passing Objects to Custom Elements

You asked about passing objects. There are a few approaches:

#### 1. JSON in Attribute (Simple)

```html
<guitar-detail 
  model="chart" 
  item-id="123"
  config='{"showActions": true, "editable": false}'
></guitar-detail>
```

#### 2. Property Assignment (JavaScript)

```html
<guitar-edit id="chart-editor"></guitar-edit>

<script>
  const editor = document.getElementById('chart-editor');
  editor.config = {
    model: 'chart',
    itemId: 123,
    onSuccess: (chart) => {
      console.log('Saved:', chart);
      Guitar.navigate(`/charts/${chart.id}`);
    },
    onError: (error) => {
      showToast('Error saving: ' + error.message);
    },
  };
</script>
```

The custom element handles this:

```typescript
class GuitarEditElement extends HTMLElement {
  private _config: EditConfig = {};
  
  set config(value: EditConfig) {
    this._config = { ...this._config, ...value };
    this.load();
  }
  
  get config(): EditConfig {
    return this._config;
  }
}
```

#### 3. Preset Configurations (Best of Both)

Define configs in TypeScript, reference by name in HTML:

```typescript
// configs/chart-views.ts
Guitar.defineConfig('chart-detail-editable', {
  model: 'chart',
  template: 'full',
  editable: true,
  onSuccess: (chart) => Guitar.navigate(`/charts/${chart.id}`),
});

Guitar.defineConfig('chart-detail-readonly', {
  model: 'chart', 
  template: 'full',
  editable: false,
});
```

```html
<!-- Use by name -->
<guitar-detail config="chart-detail-editable" item-id="123"></guitar-detail>
```

```typescript
// Custom element looks up config
class GuitarDetailElement extends HTMLElement {
  connectedCallback() {
    const configName = this.getAttribute('config');
    if (configName) {
      this._config = Guitar.getConfig(configName);
    }
    // Merge with attribute overrides
    if (this.getAttribute('item-id')) {
      this._config.itemId = this.getAttribute('item-id');
    }
    this.load();
  }
}
```

#### 4. TypeScript-Defined Custom Elements

For complex configs, create derived custom elements:

```typescript
// elements/chart-detail-editor.ts
import { GuitarEditElement } from '@guitar/elements';

class ChartDetailEditor extends GuitarEditElement {
  constructor() {
    super();
    this.config = {
      model: 'chart',
      fields: ['name', 'chart_type', 'query', 'config'],
      widgets: {
        query: 'code-editor',
        config: 'json-editor',
      },
      autoSave: true,
      autoSaveDelay: 1500,
      onSuccess: (chart) => {
        showToast(`Saved "${chart.name}"`);
      },
    };
  }
}

customElements.define('chart-detail-editor', ChartDetailEditor);
```

```html
<!-- Simple to use, all config in TS -->
<chart-detail-editor item-id="123"></chart-detail-editor>
```

---

## Event System & Custom Events

### Model Events

Every model class has built-in events:

```typescript
// Built-in events emitted automatically
type ModelEvent = 
  | 'created'     // After successful create
  | 'updated'     // After successful update
  | 'deleted'     // After successful delete
  | 'selected'    // When item is selected (user-triggered)
  | 'deselected'  // When item is deselected
  | 'error';      // On any error

// Listen to events
Chart.on('updated', (chart, meta) => {
  console.log('Chart updated:', chart);
  console.log('Changed fields:', meta.changedFields);
});

// Events include metadata
interface EventMeta {
  changedFields?: string[];  // For update
  previousValue?: any;       // For update
  source?: 'local' | 'remote';  // Where change originated
}
```

### Triggering Events

Events are triggered automatically by the client, but you can also trigger manually:

```typescript
// Automatic - these emit events
await Chart.objects.create({ name: 'New Chart' });  // Emits 'created'
await Chart.objects.filter({ id: 1 }).update({ name: 'Updated' });  // Emits 'updated'
await Chart.objects.filter({ id: 1 }).delete();  // Emits 'deleted'

// Manual - for custom interactions
Chart.emit('selected', chart);  // User selected a chart
Chart.emit('deselected', chart);  // User deselected

// Custom events
Chart.emit('starred', chart);  // Custom event
Chart.emit('shared', { chart, users: [1, 2, 3] });  // With extra data
```

### Defining Custom Events

```typescript
// In your app code
type ChartCustomEvents = {
  starred: { chart: Chart; starred: boolean };
  shared: { chart: Chart; userIds: number[] };
  duplicated: { original: Chart; copy: Chart };
};

// Type-safe event handling
Chart.on<ChartCustomEvents>('starred', ({ chart, starred }) => {
  showToast(starred ? 'Chart starred!' : 'Star removed');
});
```

### Event Handlers in Components

Components can declare event handlers:

```typescript
// guitar/templates/chart/card.ts
export default defineComponent<Chart>({
  name: 'chart-card',
  
  // DOM events
  on: {
    click(el, chart, event) {
      Chart.emit('selected', chart);
    },
    
    dblclick(el, chart, event) {
      Guitar.navigate(`/charts/${chart.id}/edit`);
    },
  },
  
  // Model events - react to changes
  subscribe: {
    // When THIS chart is updated
    updated(el, chart, newData) {
      // Re-render this element
      el.outerHTML = GuitarTemplates.render('chart', 'card', newData);
    },
    
    // When THIS chart is selected
    selected(el, chart) {
      el.classList.add('selected');
    },
    
    deselected(el, chart) {
      el.classList.remove('selected');
    },
  },
});
```

### Event Propagation

Events propagate up through the model hierarchy:

```typescript
// Global listener for all models
Guitar.on('*:updated', (model, instance, meta) => {
  console.log(`${model} updated:`, instance);
});

// Listen to specific model
Guitar.on('chart:updated', (chart, meta) => {
  console.log('Chart updated:', chart);
});

// Listen to all events on a model
Chart.on('*', (eventName, data) => {
  console.log(`Chart event ${eventName}:`, data);
});
```

---

## Central Object Registry

### The Problem

When you have the same object displayed in multiple places (list view + detail view), updates need to sync:

```
┌─────────────────────────────────────────────────────────┐
│                       Todo App                          │
├─────────────────────┬───────────────────────────────────┤
│   List (sidebar)    │         Detail View               │
│                     │                                   │
│  □ Buy groceries    │   ┌─────────────────────────┐    │
│  ☑ Clean room       │   │ Title: Clean room       │    │
│  □ Call mom    ◄────┼───│                         │    │
│                     │   │ [Edit title here...]    │    │
│                     │   └─────────────────────────┘    │
└─────────────────────┴───────────────────────────────────┘

When you edit "Clean room" in the detail view,
the list on the left should update too.
```

### Solution: Global Object Registry

A central store of all loaded objects, with reactive updates:

```typescript
// guitar/registry.ts

class ObjectRegistry {
  // Storage: model -> id -> data
  private _store: Map<string, Map<string | number, any>> = new Map();
  
  // Subscribers: model -> id -> Set<callback>
  private _subscribers: Map<string, Map<string | number, Set<Function>>> = new Map();
  
  // Get or create model store
  private getModelStore(model: string): Map<string | number, any> {
    if (!this._store.has(model)) {
      this._store.set(model, new Map());
    }
    return this._store.get(model)!;
  }
  
  // Set/update an object
  set(model: string, id: string | number, data: any): void {
    const store = this.getModelStore(model);
    const existing = store.get(id);
    
    store.set(id, data);
    
    // Notify subscribers
    if (existing) {
      this.notify(model, id, 'updated', data, existing);
    } else {
      this.notify(model, id, 'created', data);
    }
  }
  
  // Get an object
  get(model: string, id: string | number): any | undefined {
    return this._store.get(model)?.get(id);
  }
  
  // Delete an object
  delete(model: string, id: string | number): void {
    const store = this._store.get(model);
    const existing = store?.get(id);
    
    if (existing) {
      store!.delete(id);
      this.notify(model, id, 'deleted', existing);
    }
  }
  
  // Subscribe to changes for a specific object
  subscribe(
    model: string, 
    id: string | number, 
    callback: (event: string, data: any, previous?: any) => void
  ): () => void {
    if (!this._subscribers.has(model)) {
      this._subscribers.set(model, new Map());
    }
    const modelSubs = this._subscribers.get(model)!;
    
    if (!modelSubs.has(id)) {
      modelSubs.set(id, new Set());
    }
    modelSubs.get(id)!.add(callback);
    
    // Return unsubscribe function
    return () => {
      modelSubs.get(id)?.delete(callback);
    };
  }
  
  // Notify subscribers
  private notify(
    model: string, 
    id: string | number, 
    event: string, 
    data: any, 
    previous?: any
  ): void {
    // Notify specific object subscribers
    this._subscribers.get(model)?.get(id)?.forEach(callback => {
      callback(event, data, previous);
    });
    
    // Emit model event
    const ModelClass = this.getModel(model);
    ModelClass?.emit(event, data, { previousValue: previous });
  }
  
  // Get all objects of a model
  getAll(model: string): any[] {
    const store = this._store.get(model);
    return store ? Array.from(store.values()) : [];
  }
  
  // Query the registry (for local filtering)
  query(model: string, filter: Record<string, any>): any[] {
    const all = this.getAll(model);
    return all.filter(item => {
      return Object.entries(filter).every(([key, value]) => {
        return item[key] === value;
      });
    });
  }
  
  // Model class registry
  private _models: Map<string, any> = new Map();
  
  registerModel(name: string, ModelClass: any): void {
    this._models.set(name, ModelClass);
  }
  
  getModel(name: string): any {
    return this._models.get(name);
  }
}

export const GuitarRegistry = new ObjectRegistry();
```

### Automatic Registration

The Guitar client automatically registers objects when fetched:

```typescript
// In GuitarManager.all()
async all(): Promise<TRead[]> {
  const results = await guitarFetch<TRead[]>(...);
  
  // Register all results
  results.forEach(item => {
    GuitarRegistry.set(this._modelName, item.id, item);
  });
  
  return results;
}

// In GuitarManager.update()
async update(data: TUpdate): Promise<TRead[]> {
  // ... perform update ...
  
  // Update registry
  results.forEach(item => {
    GuitarRegistry.set(this._modelName, item.id, item);
  });
  
  return results;
}
```

### Reactive DOM Updates

When registry changes, DOM elements auto-update:

```typescript
// guitar/reactive.ts

// Find and update all DOM elements for an object
export const updateDOMForObject = (model: string, id: string | number): void => {
  const selector = `[data-guitar-model="${model}"][data-guitar-id="${id}"]`;
  const elements = document.querySelectorAll(selector);
  
  elements.forEach(element => {
    const template = element.getAttribute('data-guitar-template');
    const data = GuitarRegistry.get(model, id);
    
    if (template && data && data._renders?.[template]) {
      // Use pre-rendered HTML if available
      element.outerHTML = data._renders[template];
    } else if (template && data) {
      // Re-render client-side
      const html = GuitarTemplates.render(model, template, data);
      element.outerHTML = html;
    }
    
    // Re-initialize components
    Guitar.initComponents(element.parentElement!);
  });
};

// Subscribe to registry changes
GuitarRegistry.onAny((model, id, event, data) => {
  if (event === 'updated') {
    updateDOMForObject(model, id);
  } else if (event === 'deleted') {
    // Remove elements
    const selector = `[data-guitar-model="${model}"][data-guitar-id="${id}"]`;
    document.querySelectorAll(selector).forEach(el => el.remove());
  }
});
```

### The Todo Sync Example

```html
<!-- Both views reference the same todo -->
<aside class="sidebar">
  <guitar-list model="todo" template="list-item"></guitar-list>
</aside>

<main>
  <guitar-detail model="todo" item-id="123" template="full"></guitar-detail>
</main>
```

When you edit in the detail view:

```typescript
// In guitar-edit element
async save() {
  const result = await Todo.objects.filter({ id: 123 }).update({ title: 'New Title' });
  
  // This automatically:
  // 1. Updates GuitarRegistry with new data
  // 2. Emits Todo 'updated' event
  // 3. All subscribed elements re-render
}
```

The list item and detail view both update because:

1. They're both subscribed to `Todo.on('updated', ...)`
2. Or they're watching `GuitarRegistry.subscribe('todo', 123, ...)`
3. The reactive system finds all `[data-guitar-model="todo"][data-guitar-id="123"]` elements and updates them

---

## Wiring Up Search/Refresh

### The Question: Push vs Pull?

When a search field changes, how does the list update?

**Pull (List polls for changes):**
```html
<input id="search" type="text">
<guitar-list 
  model="todo" 
  watch-input="#search"
  filter-field="title__icontains"
></guitar-list>
```

**Push (Search pushes to list):**
```html
<input 
  type="text"
  data-guitar-target="#todo-list"
  data-guitar-filter-field="title__icontains"
>
<guitar-list id="todo-list" model="todo"></guitar-list>
```

### Recommendation: Both, with Push as Primary

The list element can declare what to watch (pull), but inputs can also target lists (push).

#### Push Pattern (Input Controls List)

```html
<input 
  type="search"
  placeholder="Search todos..."
  data-guitar-target="guitar-list[model='todo']"
  data-guitar-filter-field="title__icontains"
  data-guitar-debounce="300"
>

<guitar-list model="todo" template="list-item"></guitar-list>
```

```typescript
// guitar/search.ts - Search input handler

document.addEventListener('input', (e) => {
  const input = e.target as HTMLInputElement;
  const target = input.getAttribute('data-guitar-target');
  const filterField = input.getAttribute('data-guitar-filter-field');
  
  if (!target || !filterField) return;
  
  const debounce = parseInt(input.getAttribute('data-guitar-debounce') || '0');
  
  // Debounce if needed
  clearTimeout(input._debounceTimer);
  input._debounceTimer = setTimeout(() => {
    // Find target list
    const listElement = document.querySelector(target) as GuitarListElement;
    
    if (listElement) {
      // Update filter and reload
      listElement.setFilter(filterField, input.value);
    }
  }, debounce);
});
```

```typescript
// In GuitarListElement
class GuitarListElement extends HTMLElement {
  private _dynamicFilters: Record<string, any> = {};
  
  setFilter(field: string, value: any) {
    if (value === '' || value === null || value === undefined) {
      delete this._dynamicFilters[field];
    } else {
      this._dynamicFilters[field] = value;
    }
    this.load();
  }
  
  clearFilters() {
    this._dynamicFilters = {};
    this.load();
  }
  
  async load() {
    // Merge static and dynamic filters
    const staticFilter = JSON.parse(this.getAttribute('filter') || '{}');
    const combinedFilter = { ...staticFilter, ...this._dynamicFilters };
    
    // ... rest of load logic
  }
}
```

#### Pull Pattern (List Watches Input)

```html
<input id="search-input" type="search">

<guitar-list 
  model="todo"
  template="list-item"
  watch="#search-input"
  watch-field="title__icontains"
  watch-debounce="300"
></guitar-list>
```

```typescript
// In GuitarListElement
connectedCallback() {
  this.load();
  this.setupWatch();
}

setupWatch() {
  const watchSelector = this.getAttribute('watch');
  if (!watchSelector) return;
  
  const watchField = this.getAttribute('watch-field');
  const debounce = parseInt(this.getAttribute('watch-debounce') || '0');
  
  const input = document.querySelector(watchSelector) as HTMLInputElement;
  if (!input) return;
  
  let timer: number;
  input.addEventListener('input', () => {
    clearTimeout(timer);
    timer = window.setTimeout(() => {
      this.setFilter(watchField!, input.value);
    }, debounce);
  });
}
```

#### Filter Tabs Pattern

```html
<nav class="filters">
  <button 
    class="active"
    data-guitar-target="#todo-list"
    data-guitar-filter='{}'
  >All</button>
  
  <button 
    data-guitar-target="#todo-list"
    data-guitar-filter='{"completed": false}'
  >Active</button>
  
  <button 
    data-guitar-target="#todo-list"
    data-guitar-filter='{"completed": true}'
  >Completed</button>
</nav>

<guitar-list id="todo-list" model="todo" template="list-item"></guitar-list>
```

```typescript
// Filter button handler
document.addEventListener('click', (e) => {
  const button = (e.target as Element).closest('[data-guitar-filter]');
  if (!button) return;
  
  const target = button.getAttribute('data-guitar-target');
  const filter = JSON.parse(button.getAttribute('data-guitar-filter') || '{}');
  
  const listElement = document.querySelector(target) as GuitarListElement;
  if (listElement) {
    listElement.replaceFilters(filter);
  }
  
  // Update active state
  button.parentElement?.querySelectorAll('[data-guitar-filter]').forEach(btn => {
    btn.classList.toggle('active', btn === button);
  });
});
```

---

## Revised Architecture

Based on all the refinements:

```
@guitar/core
├── registry.ts          # Central object store
├── events.ts            # Event system
├── templates.ts         # Template engine (Nunjucks wrapper)
├── reactive.ts          # DOM update system
└── init.ts              # Initialization

@guitar/elements
├── guitar-list.ts       # <guitar-list> custom element
├── guitar-detail.ts     # <guitar-detail> custom element
├── guitar-edit.ts       # <guitar-edit> custom element
└── index.ts             # Register all elements

@guitar/components
├── define.ts            # defineComponent helper
├── actions.ts           # Action binding system
└── lifecycle.ts         # Mount/unmount handling

@guitar/client
├── manager.ts           # GuitarManager (queryset-like)
├── fetch.ts             # API fetching
└── models/              # Generated model files

templates/               # User's templates
├── chart/
│   ├── card.html        # Template
│   ├── card.ts          # Optional interactivity
│   └── list-item.html
└── todo/
    ├── card.html
    └── card.ts
```

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                           User Action                                │
│                    (click, type, submit, etc.)                       │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          Guitar Client                               │
│              Chart.objects.filter(...).update(...)                   │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          Django Backend                              │
│                    Process request, return data                      │
│               (optionally with _renders.template)                    │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Guitar Registry                                │
│                   Store/update object data                           │
│                   Notify subscribers                                 │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Event System                                  │
│                Chart.emit('updated', data)                           │
│                   Notify all listeners                               │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│    Custom Elements        │   │    Component Handlers     │
│   <guitar-list>           │   │   chart-card.ts           │
│   <guitar-detail>         │   │   subscribe.updated()     │
│   Auto re-render          │   │   Update single element   │
└───────────────────────────┘   └───────────────────────────┘
                    │                       │
                    └───────────┬───────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          Updated DOM                                 │
│              All views of the object are in sync                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Summary of Key Decisions

| Topic | Decision |
|-------|----------|
| **Rendering** | Backend returns `_renders.{template}` field with pre-rendered HTML |
| **Client-side fallback** | Nunjucks (Django-compatible) for client-side rendering |
| **Template files** | Plain `.html` files + optional `.ts` for interactivity |
| **Views** | Custom elements: `<guitar-list>`, `<guitar-detail>`, `<guitar-edit>` |
| **Config passing** | Named configs + property assignment + attribute overrides |
| **Events** | Model events with `Chart.on('updated', ...)` pattern |
| **Object sync** | Central `GuitarRegistry` with reactive updates |
| **Search/filter** | Push pattern (input targets list) as primary |

This gives Django developers:
- **Familiar templates** (Django/Jinja2 syntax works everywhere)
- **Declarative views** (Custom elements like Django CBVs)
- **Minimal JavaScript** (Most behavior in HTML attributes)
- **Automatic sync** (Edit anywhere, updates everywhere)
- **Escape hatches** (TypeScript when needed for complex logic)
