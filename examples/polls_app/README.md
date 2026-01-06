# Django Guitar Polls App Example

A complete React SPA example using Django Guitar, following Django's official tutorial structure.

## Features

- **Django Backend** with Question and Choice models
- **React Frontend** (TypeScript + Vite) using the generated Guitar client
- **Model-Level Security** - Published questions are visible, drafts are editable
- **Full CRUD** - Create, read, update, delete operations
- **Real-time UI** - Modern React components with beautiful styling

## Project Structure

```
polls_app/
├── polls/              # Django app with models
│   ├── models.py       # Question and Choice models
│   └── admin.py        # Django admin configuration
├── config/             # Django project settings
│   ├── settings.py
│   └── urls.py
├── frontend/           # React SPA
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── guitar/      # Generated TypeScript client (run generate_guitar_client)
│   │   └── App.tsx
│   └── package.json
└── manage.py
```

## Setup Instructions

### 1. Backend Setup

```bash
cd polls_app

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser (optional, for admin)
python manage.py createsuperuser

# Generate TypeScript client
python manage.py generate_guitar_client

# Run Django server
python manage.py runserver
```

The Django server will run on `http://localhost:8000`

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The React app will run on `http://localhost:5173`

### 3. Generate Sample Data (Optional)

You can create sample questions via:
- Django admin: `http://localhost:8000/admin`
- The React app's "Create Question" form

## Usage

### Viewing Questions

- Navigate to the home page to see all published questions
- Click on a question to view its details and vote

### Creating Questions

1. Click "Create Question" in the header
2. Enter question text
3. Add at least 2 choices
4. Click "Create Question"

Questions are created as drafts (unpublished) first, then immediately published so they appear in the list.

### Voting

- Click on a question to view its choices
- Click "Vote" next to a choice
- Note: In this example, voting is simulated (the votes field is read-only in the API)
- In a production app, you'd create a custom endpoint to increment votes

## API Endpoints

Django Guitar automatically generates these endpoints:

- `GET /guitar/question/` - List published questions
- `GET /guitar/question/{id}/` - Get question details
- `POST /guitar/question/` - Create question
- `PATCH /guitar/question/{id}/` - Update question (drafts only)
- `DELETE /guitar/question/{id}/` - Delete question (drafts only)

- `GET /guitar/choice/` - List choices
- `GET /guitar/choice/{id}/` - Get choice details
- `POST /guitar/choice/` - Create choice (for draft questions)
- `PATCH /guitar/choice/{id}/` - Update choice (draft questions only)
- `DELETE /guitar/choice/{id}/` - Delete choice (draft questions only)

## Model-Level Security

The app demonstrates Django Guitar's Model-Level Security:

- **Published questions** (`pub_date <= now`) are visible to everyone
- **Draft questions** (`pub_date > now`) can only be edited/deleted by their creator
- **Choices** inherit permissions from their parent question
- **Votes** are read-only (can't be modified via API)

## TypeScript Client

The generated TypeScript client provides type-safe access to your Django models:

```typescript
import { Question, Choice } from './guitar'

// List questions
const questions = await Question.objects.all()

// Filter questions
const recent = await Question.objects.filter({ pub_date__year: 2024 })

// Get question with choices
const question = await Question.objects
  .get({ id: 1 })
  .prefetch_related('choices')

// Create question
const newQuestion = await Question.objects.create({
  question_text: "What's your favorite language?",
  pub_date: new Date().toISOString()
})
```

## Development

### Regenerating TypeScript Client

After making changes to models:

```bash
# Run migrations
python manage.py makemigrations
python manage.py migrate

# Regenerate TypeScript client
python manage.py generate_guitar_client
```

### Building for Production

```bash
# Build React app
cd frontend
npm run build

# The built files will be in frontend/dist/
# Serve them with Django or a static file server
```

## Troubleshooting

### CORS Errors

If you see CORS errors, make sure:
1. `django-cors-headers` is installed
2. `corsheaders` is in `INSTALLED_APPS`
3. `CorsMiddleware` is in `MIDDLEWARE`
4. `CORS_ALLOWED_ORIGINS` includes your frontend URL

### TypeScript Client Not Found

Run `python manage.py generate_guitar_client` to generate the client in `frontend/src/guitar/`

### Questions Not Appearing

Make sure questions have `pub_date <= now()` to be visible. Draft questions (future dates) won't appear in the list.

## Next Steps

- Add user authentication
- Create a custom vote endpoint to increment votes
- Add question categories/tags
- Implement real-time updates with WebSockets
- Add question expiration dates
- Implement user voting history

## License

This is an example project demonstrating Django Guitar. Feel free to use it as a starting point for your own projects.

