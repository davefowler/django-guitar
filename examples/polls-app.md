# Example: Polls App

A polling application following Django's official tutorial structure, demonstrating Guitar's permission system.

## Data Model

```
┌─────────────┐       ┌─────────────┐
│   Question   │──FK──│    Choice    │
│ - question_  │       │ - choice_    │
│   text       │       │   text       │
│ - pub_date   │       │ - votes      │
└─────────────┘       └─────────────┘
```

## Models

```python
from django.db import models
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from guitar import GuitarModel


class Question(GuitarModel, models.Model):
    """
    A poll question with multiple choices.
    Questions can be published (visible) or unpublished (draft).
    """
    question_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')
    
    class Meta:
        ordering = ['-pub_date']
        verbose_name = 'question'
        verbose_name_plural = 'questions'
    
    def __str__(self) -> str:
        return self.question_text
    
    def was_published_recently(self) -> bool:
        """Returns True if the question was published within the last day."""
        now = timezone.now()
        return now - timezone.timedelta(days=1) <= self.pub_date <= now
    
    class GuitarMeta:
        fields = ['id', 'question_text', 'pub_date']
        writable_fields = ['question_text', 'pub_date']
        read_only_fields = ['id']
        operations = ['list', 'retrieve', 'create', 'update', 'delete']
        filterable_fields = ['question_text', 'pub_date']
        orderable_fields = ['question_text', 'pub_date']
        searchable_fields = ['question_text']
    
    class GuitarManager:
        def filter_read(self, request, queryset):
            """Anyone can see published questions."""
            return queryset.filter(pub_date__lte=timezone.now())
        
        def filter_write(self, request, queryset):
            """Only unpublished questions can be edited."""
            return queryset.filter(pub_date__gte=timezone.now())
        
        def filter_delete(self, request, queryset):
            """Only unpublished questions can be deleted."""
            return queryset.filter(pub_date__gte=timezone.now())
        
        def check_create(self, request, data):
            """Set pub_date to now if not provided."""
            if 'pub_date' not in data or not data['pub_date']:
                data['pub_date'] = timezone.now()
            return data


class Choice(GuitarModel, models.Model):
    """
    A choice for a question. Users can vote on choices.
    """
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='choices'
    )
    choice_text = models.CharField(max_length=200)
    votes = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-votes', 'choice_text']
        verbose_name = 'choice'
        verbose_name_plural = 'choices'
    
    def __str__(self) -> str:
        return self.choice_text
    
    class GuitarMeta:
        fields = ['id', 'question_id', 'choice_text', 'votes']
        writable_fields = ['question_id', 'choice_text']
        read_only_fields = ['id', 'votes']  # Votes can only be incremented via voting
        operations = ['list', 'retrieve', 'create', 'update', 'delete']
        filterable_fields = ['question_id', 'choice_text']
        orderable_fields = ['votes', 'choice_text']
    
    class GuitarManager:
        chain_permissions = True
        
        def filter_read(self, request, queryset):
            """Can see choices for published questions."""
            return queryset.filter(question__pub_date__lte=timezone.now())
        
        def filter_write(self, request, queryset):
            """Can edit choices for unpublished questions."""
            return queryset.filter(question__pub_date__gte=timezone.now())
        
        def filter_delete(self, request, queryset):
            """Can delete choices for unpublished questions."""
            return queryset.filter(question__pub_date__gte=timezone.now())
        
        def check_create(self, request, data):
            """Can only add choices to unpublished questions."""
            question_id = data.get('question_id')
            
            question = Question.objects.filter(
                id=question_id,
                pub_date__gte=timezone.now()
            ).first()
            
            if not question:
                raise PermissionDenied("Can only add choices to unpublished questions")
            
            return data
        
        def check_update(self, request, instance, data):
            """Prevent modifying votes directly - use vote endpoint instead."""
            if 'votes' in data:
                raise PermissionDenied("Cannot modify votes directly. Use the vote endpoint.")
            return data
```

---

## TypeScript Usage

```typescript
import { Question, Choice } from './guitar';

// ============================================================
// LISTING QUESTIONS
// ============================================================

// Get all published questions
const questions = await Question.objects.all();
// Returns only questions where pub_date <= now

// Filter by date
const recentQuestions = await Question.objects.filter({
    pub_date__year: 2024,
    pub_date__month: 1
});

// Search questions
const results = await Question.objects.search('favorite programming language');

// Order by publication date
const latestQuestions = await Question.objects
    .order_by('-pub_date')
    .limit(10);


// ============================================================
// CREATING QUESTIONS (DRAFT)
// ============================================================

// Create a new question (becomes draft/unpublished)
const question = await Question.objects.create({
    question_text: "What's your favorite programming language?",
    pub_date: new Date()  // Will be published immediately
});

// Or create as draft (future date)
const draftQuestion = await Question.objects.create({
    question_text: "What's your favorite framework?",
    pub_date: new Date('2025-01-01')  // Future date = draft
});

// Add choices to the draft question
await Choice.objects.create({
    question_id: draftQuestion.id,
    choice_text: "Django"
});

await Choice.objects.create({
    question_id: draftQuestion.id,
    choice_text: "Flask"
});

await Choice.objects.create({
    question_id: draftQuestion.id,
    choice_text: "FastAPI"
});


// ============================================================
// VIEWING QUESTIONS AND CHOICES
// ============================================================

// Get a question with its choices
const question = await Question.objects
    .get({ id: 1 })
    .prefetch_related('choices');

console.log(question.question_text);  // "What's your favorite..."
console.log(question.choices);        // [{ id: 1, choice_text: "Django", votes: 0 }, ...]

// Get choices for a question
const choices = await Choice.objects.filter({ question_id: 1 });
// Returns choices ordered by votes (descending)

// Get top choice
const topChoice = await Choice.objects
    .filter({ question_id: 1 })
    .order_by('-votes')
    .first();


// ============================================================
// VOTING
// ============================================================

// Note: Votes are read-only via the API
// You'd need a custom endpoint to increment votes:
// POST /api/vote/{choice_id}/

// But you can see vote counts
const choice = await Choice.objects.get({ id: 1 });
console.log(choice.votes);  // Current vote count


// ============================================================
// EDITING DRAFTS
// ============================================================

// Update draft question
await Question.objects
    .filter({ id: draftQuestion.id })
    .update({ question_text: "Updated question text" });

// Update choices in draft
await Choice.objects
    .filter({ id: choiceId })
    .update({ choice_text: "Updated choice" });

// Delete draft question
await Question.objects.delete({ id: draftQuestion.id });

// ✗ Cannot edit published questions
await Question.objects
    .filter({ id: publishedQuestionId })
    .update({ question_text: "New text" });
// Error: 404 Not Found (filtered out by filter_write)

// ✗ Cannot delete published questions
await Question.objects.delete({ id: publishedQuestionId });
// Error: 404 Not Found
```

---

## Edge Cases Demonstrated

### 1. Time-Based Permissions
Questions are editable only before publication:
```python
def filter_write(self, request, queryset):
    return queryset.filter(pub_date__gte=timezone.now())
```

### 2. Cascading Permissions
Choices inherit access from their parent Question:
```python
def filter_read(self, request, queryset):
    return queryset.filter(question__pub_date__lte=timezone.now())
```

### 3. Read-Only Fields
Votes can't be modified directly via API:
```python
read_only_fields = ['id', 'votes']  # Votes incremented via voting endpoint

def check_update(self, request, instance, data):
    if 'votes' in data:
        raise PermissionDenied("Cannot modify votes directly")
    return data
```

### 4. Validation on Create
Prevent adding choices to published questions:
```python
def check_create(self, request, data):
    question_id = data.get('question_id')
    question = Question.objects.filter(
        id=question_id,
        pub_date__gte=timezone.now()
    ).first()
    
    if not question:
        raise PermissionDenied("Can only add choices to unpublished questions")
    return data
```

---

## API Endpoints Generated

```
# Questions
GET    /guitar/question/              → list (published only)
GET    /guitar/question/{id}/          → retrieve
POST   /guitar/question/               → create (becomes draft if future date)
PATCH  /guitar/question/{id}/          → update (draft only)
DELETE /guitar/question/{id}/           → delete (draft only)

# Choices
GET    /guitar/choice/                 → list (for published questions)
GET    /guitar/choice/{id}/            → retrieve
POST   /guitar/choice/                 → create (draft questions only)
PATCH  /guitar/choice/{id}/           → update (draft questions only, votes read-only)
DELETE /guitar/choice/{id}/           → delete (draft questions only)
```

---

## Possible Extensions

1. **Vote Endpoint** - Custom endpoint to increment votes:
   ```python
   @router.post('/vote/{choice_id}/')
   def vote(request, choice_id: int):
       choice = get_object_or_404(Choice, id=choice_id)
       choice.votes += 1
       choice.save()
       return {'votes': choice.votes}
   ```

2. **User Votes** - Track which users voted:
   ```python
   class Vote(models.Model):
       user = models.ForeignKey(User, on_delete=models.CASCADE)
       choice = models.ForeignKey(Choice, on_delete=models.CASCADE)
       voted_at = models.DateTimeField(auto_now_add=True)
   ```

3. **Question Categories** - Add categories/tags:
   ```python
   category = models.CharField(max_length=50, choices=CATEGORIES)
   ```

4. **Question Expiration** - Auto-close polls:
   ```python
   end_date = models.DateTimeField(null=True, blank=True)
   ```

5. **Multiple Choice** - Allow selecting multiple choices

6. **Question Comments** - Add comments to questions

7. **Question Polling** - Real-time vote updates via WebSockets

