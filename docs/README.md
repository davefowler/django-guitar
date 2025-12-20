# Django Guitar Documentation

## Building the Docs

```bash
# Install dependencies
pip install mkdocs-material mkdocstrings[python]

# Serve locally
mkdocs serve

# Build static site
mkdocs build
```

## Structure

```
docs/
├── index.md              # Home page
├── getting-started.md    # Quick start guide
├── api-reference.md      # Full API reference
├── permission-patterns.md # Permission cookbook
└── typescript-client.md  # Frontend guide

examples/
└── dashboard-app.md      # Full example application

spec.md                   # Technical specification
```

