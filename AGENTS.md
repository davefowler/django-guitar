# Django Guitar - AI Agent Guide

This document provides context for AI agents working on the Django Guitar project.

## Project Overview

Django Guitar is a framework that automatically generates a fully-typed TypeScript client from Django models, bringing Django's familiar ORM syntax to the frontend.

```typescript
// Frontend code that feels like Django
const charts = await Chart.objects.filter({ user_id: currentUser.id });
```

## Directory Structure

```
/workspace/
├── guitar/                 # Core Django app (Python)
│   ├── models.py          # GuitarModel mixin, GuitarMeta, GuitarManager
│   ├── router.py          # Auto-generates Django Ninja API endpoints
│   ├── permissions.py     # Permission classes
│   └── management/
│       └── commands/
│           └── generate_guitar_client.py  # TypeScript generation command
│
├── frontend/              # Generated TypeScript client
│   └── src/
│       └── guitar/
│           ├── client.ts  # Base GuitarManager class, fetch utilities
│           ├── types.ts   # Shared types
│           └── models/    # Generated model files (Chart.ts, etc.)
│
├── example_project/       # Example Django project using Guitar
│   └── dashboard/
│       └── models.py      # Dashboard, Chart, DashboardMembership examples
│
├── docs/                  # Official documentation (mkdocs)
│   ├── getting-started.md
│   ├── api-reference.md
│   ├── permission-patterns.md
│   └── typescript-client.md
│
├── notes/                 # AI research & brainstorming notes
│   └── (see below)
│
└── examples/              # Example app documentation
    └── dashboard-app.md
```

## Key Files to Understand

| File | Purpose |
|------|---------|
| `guitar/models.py` | Core `GuitarModel` mixin with `GuitarMeta` and `GuitarManager` |
| `guitar/router.py` | Auto-generates REST endpoints from Guitar models |
| `frontend/src/guitar/client.ts` | TypeScript `GuitarManager` with Django-like queryset API |
| `example_project/dashboard/models.py` | Real-world example with permissions |

## AI Research Notes

The `notes/` directory contains research and design documents for new features. These are working documents, not official docs.

### Frontend Framework Research

We're designing a Django-like frontend framework using Web Components. Key documents:

| Document | Description |
|----------|-------------|
| [guitar-frontend-summary.md](notes/guitar-frontend-summary.md) | **START HERE** - Complete summary of the frontend framework design |
| [frontend-framework-research.md](notes/frontend-framework-research.md) | Initial research on `.render()`, Django Forms, HTMX influences |
| [frontend-framework-refined.md](notes/frontend-framework-refined.md) | Refined with `_renders` field, template files, custom elements |
| [frontend-framework-v3.md](notes/frontend-framework-v3.md) | Auto-generated elements from templates, todo app example |
| [frontend-framework-v4.md](notes/frontend-framework-v4.md) | Behavior files, `@event` syntax, declarative wiring |
| [frontend-framework-v5-state.md](notes/frontend-framework-v5-state.md) | Unified state model, UI state + model state |
| [frontend-framework-v6-syntax.md](notes/frontend-framework-v6-syntax.md) | Vue-style `:` and `@` syntax, deps attribute |
| [frontend-framework-v7-final.md](notes/frontend-framework-v7-final.md) | Debounce on queryset, `:state` auto-creates state |
| [frontend-framework-v8-slots.md](notes/frontend-framework-v8-slots.md) | Empty/loading states following Django's `{% empty %}` |

### Key Frontend Framework Decisions

1. **Custom Elements (Web Components)** - Core components work in React, Vue, Svelte, or vanilla JS
2. **Templates** - Django/Nunjucks syntax with `@event` bindings for interactivity
3. **State** - `:state="varName"` auto-creates and binds state from input defaults
4. **Debounce** - `.debounce(300)` on queryset chain, not on inputs
5. **Dependencies** - Auto-tracked from `state.*` access, no explicit deps needed
6. **Empty states** - Follow Django's `{% empty %}` pattern

## Development Guidelines

### Python (Backend)

- Uses Django Ninja for API generation
- Model-Level Security (MLS) via `GuitarManager` class
- Permissions defined on models, not scattered across views

### TypeScript (Frontend)

- Strict linting: always specify return types
- Use function expressions over declarations
- Styled Components for styling (when applicable)

### When Adding Features

1. Check existing patterns in `guitar/models.py` and `guitar/router.py`
2. Review the example in `example_project/dashboard/models.py`
3. For frontend framework work, read `notes/guitar-frontend-summary.md` first

## Running the Project

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Generate TypeScript client
python manage.py generate_guitar_client

# Serve docs locally
mkdocs serve
```

## Links

- [README.md](README.md) - Project overview and quick start
- [docs/getting-started.md](docs/getting-started.md) - Detailed setup guide
- [notes/guitar-frontend-summary.md](notes/guitar-frontend-summary.md) - Frontend framework design
