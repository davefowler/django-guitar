# Example: Todos App

A collaborative todo application demonstrating Guitar's permission system with both personal and shared lists.

## Data Model

```
┌─────────────┐       ┌─────────────────────┐       ┌─────────────┐
│    User     │──M2M──│ TodoListMembership  │──M2M──│  TodoList   │
└─────────────┘       │  - role             │       └──────┬──────┘
                      │    (owner/member)   │              │
                      └─────────────────────┘              │ FK
                                                           │
                                                    ┌──────┴──────┐
                                                    │    Todo     │
                                                    │  - status   │
                                                    │  - priority │
                                                    │  - due_date │
                                                    └──────┬──────┘
                                                           │ FK
                                                    ┌──────┴──────┐
                                                    │     Tag     │
                                                    └─────────────┘
```

## Roles & Permissions

| Role | TodoList | Todos | Invite Users |
|------|----------|-------|--------------|
| **owner** | create, read, update, delete | create, read, update, delete | ✓ |
| **member** | read | create, read, update, delete | ✗ |

**Personal Lists**: Lists without memberships are personal (owner-only).

## Models

```python
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from guitar import GuitarModel


class TodoList(GuitarModel, models.Model):
    """
    A collection of todos. Can be personal (no members) or shared (with members).
    """
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    color = models.CharField(max_length=7, default='#3B82F6')  # Hex color
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='owned_todo_lists'
    )
    
    # M2M for shared lists (optional - personal lists have no members)
    members = models.ManyToManyField(
        User,
        through='TodoListMembership',
        related_name='shared_todo_lists'
    )
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self) -> str:
        return self.name
    
    class GuitarMeta:
        fields = [
            'id', 'name', 'description', 'color', 'is_archived',
            'created_at', 'updated_at', 'owner_id'
        ]
        writable_fields = ['name', 'description', 'color', 'is_archived']
        read_only_fields = ['id', 'created_at', 'updated_at', 'owner_id']
        operations = ['list', 'retrieve', 'create', 'update', 'delete']
        filterable_fields = ['owner_id', 'is_archived']
        orderable_fields = ['name', 'created_at', 'updated_at']
    
    class GuitarManager:
        def filter_read(self, request, queryset):
            """Users can see lists they own or are members of."""
            if not request.user.is_authenticated:
                return queryset.none()
            return queryset.filter(
                models.Q(owner=request.user) |
                models.Q(members=request.user)
            ).distinct()
        
        def filter_write(self, request, queryset):
            """Only owners can update lists."""
            if not request.user.is_authenticated:
                return queryset.none()
            return queryset.filter(owner=request.user)
        
        def filter_delete(self, request, queryset):
            """Only owners can delete lists."""
            if not request.user.is_authenticated:
                return queryset.none()
            return queryset.filter(owner=request.user)
        
        def check_create(self, request, data):
            """Anyone can create a list (they become the owner)."""
            data['owner_id'] = request.user.id
            return data


class TodoListMembership(GuitarModel, models.Model):
    """
    Through table for TodoList <-> User sharing.
    Allows owners to share lists with other users.
    """
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('member', 'Member'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    todo_list = models.ForeignKey(TodoList, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    added_at = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='todo_list_invitations_sent'
    )
    
    class Meta:
        unique_together = ['user', 'todo_list']
        ordering = ['-added_at']
    
    def __str__(self) -> str:
        return f"{self.user.username} - {self.todo_list.name} ({self.role})"
    
    class GuitarMeta:
        fields = ['id', 'user_id', 'todo_list_id', 'role', 'added_at', 'added_by_id']
        writable_fields = ['user_id', 'todo_list_id', 'role']
        read_only_fields = ['id', 'added_at', 'added_by_id']
        exclude_operations = ['update']  # Can only create or delete memberships
        filterable_fields = ['todo_list_id', 'user_id', 'role']
    
    class GuitarManager:
        chain_permissions = True
        
        def filter_read(self, request, queryset):
            """Can see memberships for lists you own or are a member of."""
            if not request.user.is_authenticated:
                return queryset.none()
            return queryset.filter(
                models.Q(todo_list__owner=request.user) |
                models.Q(todo_list__members=request.user)
            ).distinct()
        
        def filter_delete(self, request, queryset):
            """Only list owners can remove members."""
            if not request.user.is_authenticated:
                return queryset.none()
            return queryset.filter(
                todo_list__owner=request.user
            ).exclude(
                # Can't remove yourself as owner
                user=request.user,
                role='owner'
            )
        
        def check_create(self, request, data):
            """Only list owners can add members."""
            todo_list_id = data.get('todo_list_id')
            
            todo_list = TodoList.objects.filter(
                id=todo_list_id,
                owner=request.user
            ).first()
            
            if not todo_list:
                raise PermissionDenied("Only list owners can add members")
            
            data['added_by_id'] = request.user.id
            data['role'] = 'member'  # Always add as member, not owner
            return data


class Todo(GuitarModel, models.Model):
    """
    A single todo item within a list.
    Access is controlled via the parent TodoList.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    todo_list = models.ForeignKey(
        TodoList,
        on_delete=models.CASCADE,
        related_name='todos'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium'
    )
    due_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_todos'
    )
    
    # M2M for tags (many-to-many)
    tags = models.ManyToManyField('Tag', blank=True, related_name='todos')
    
    class Meta:
        ordering = ['-priority', 'due_date', '-created_at']
    
    def __str__(self) -> str:
        return f"{self.title} ({self.todo_list.name})"
    
    class GuitarMeta:
        fields = [
            'id', 'todo_list_id', 'title', 'description', 'status', 'priority',
            'due_date', 'completed_at', 'created_at', 'updated_at', 'created_by_id'
        ]
        writable_fields = [
            'todo_list_id', 'title', 'description', 'status', 'priority',
            'due_date'
        ]
        read_only_fields = [
            'id', 'completed_at', 'created_at', 'updated_at', 'created_by_id'
        ]
        operations = ['list', 'retrieve', 'create', 'update', 'delete']
        filterable_fields = [
            'todo_list_id', 'status', 'priority', 'created_by_id'
        ]
        orderable_fields = ['title', 'status', 'priority', 'due_date', 'created_at']
    
    class GuitarManager:
        chain_permissions = True
        
        def filter_read(self, request, queryset):
            """Can see todos in lists you own or are a member of."""
            if not request.user.is_authenticated:
                return queryset.none()
            return queryset.filter(
                models.Q(todo_list__owner=request.user) |
                models.Q(todo_list__members=request.user)
            ).distinct()
        
        def filter_write(self, request, queryset):
            """Owners and members can update todos."""
            if not request.user.is_authenticated:
                return queryset.none()
            return queryset.filter(
                models.Q(todo_list__owner=request.user) |
                models.Q(todo_list__members=request.user)
            ).distinct()
        
        def filter_delete(self, request, queryset):
            """Owners and members can delete todos."""
            return self.filter_write(request, queryset)
        
        def check_create(self, request, data):
            """Owners and members can create todos."""
            todo_list_id = data.get('todo_list_id')
            
            has_access = TodoList.objects.filter(
                id=todo_list_id
            ).filter(
                models.Q(owner=request.user) |
                models.Q(members=request.user)
            ).exists()
            
            if not has_access:
                raise PermissionDenied("Must be owner or member to add todos")
            
            data['created_by_id'] = request.user.id
            return data
        
        def pre_update(self, request, instance, data):
            """Auto-set completed_at when status changes to 'completed'."""
            if 'status' in data and data['status'] == 'completed':
                if instance.status != 'completed':
                    data['completed_at'] = timezone.now()
            elif 'status' in data and instance.status == 'completed':
                # Uncompleting - clear completed_at
                if data['status'] != 'completed':
                    data['completed_at'] = None
            return data


class Tag(GuitarModel, models.Model):
    """
    Tags for organizing todos. Can be shared across lists or personal.
    """
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, default='#6B7280')  # Hex color
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tags'
    )
    
    class Meta:
        ordering = ['name']
    
    def __str__(self) -> str:
        return self.name
    
    class GuitarMeta:
        fields = ['id', 'name', 'color', 'created_at', 'created_by_id']
        writable_fields = ['name', 'color']
        read_only_fields = ['id', 'created_at', 'created_by_id']
        operations = ['list', 'retrieve', 'create', 'update', 'delete']
        filterable_fields = ['name', 'created_by_id']
        orderable_fields = ['name', 'created_at']
    
    class GuitarManager:
        def filter_read(self, request, queryset):
            """Anyone can see all tags (they're shared)."""
            return queryset.all()
        
        def filter_write(self, request, queryset):
            """Anyone can update tags."""
            return queryset.all()
        
        def filter_delete(self, request, queryset):
            """Only tag creator can delete."""
            if not request.user.is_authenticated:
                return queryset.none()
            return queryset.filter(created_by=request.user)
        
        def check_create(self, request, data):
            """Anyone can create tags."""
            data['created_by_id'] = request.user.id
            return data
```

---

## TypeScript Usage

```typescript
import { TodoList, Todo, TodoListMembership, Tag } from './guitar';

// ============================================================
// PERSONAL LIST: Alice creates her own list
// ============================================================

// ✓ Create a personal todo list
const myList = await TodoList.objects.create({
    name: "Personal Tasks",
    description: "My personal todo list",
    color: "#3B82F6"
});
// Returns: { id: 1, name: "Personal Tasks", owner_id: 1, ... }

// ✓ Add todos to the list
const todo1 = await Todo.objects.create({
    todo_list_id: 1,
    title: "Buy groceries",
    priority: "high",
    due_date: "2024-01-15T10:00:00Z"
});

const todo2 = await Todo.objects.create({
    todo_list_id: 1,
    title: "Call dentist",
    status: "pending",
    priority: "medium"
});

// ✓ List all todos in the list
const todos = await Todo.objects.filter({ todo_list_id: 1 });
// Returns: [{ id: 1, title: "Buy groceries", ... }, { id: 2, ... }]

// ✓ Update todo status
await Todo.objects.update({ id: 1 }, { status: "in_progress" });

// ✓ Complete a todo
await Todo.objects.update({ id: 1 }, { status: "completed" });
// Auto-sets completed_at timestamp

// ✓ Filter by status
const completedTodos = await Todo.objects.filter({
    todo_list_id: 1,
    status: "completed"
});

// ✓ Filter by priority
const urgentTodos = await Todo.objects.filter({
    todo_list_id: 1,
    priority: "urgent"
});

// ✓ Order by priority and due date
const sortedTodos = await Todo.objects
    .filter({ todo_list_id: 1 })
    .order_by('-priority', 'due_date');


// ============================================================
// SHARED LIST: Bob shares his list with Alice
// ============================================================

// Bob creates a shared list
const sharedList = await TodoList.objects.create({
    name: "Team Project",
    description: "Shared project tasks"
});

// Bob adds Alice as a member
await TodoListMembership.objects.create({
    todo_list_id: sharedList.id,
    user_id: 2,  // Alice's user ID
    role: "member"
});

// Alice can now see and interact with the list
const sharedTodos = await TodoList.objects.filter({ id: sharedList.id });
// Alice sees: [{ id: 2, name: "Team Project", ... }]

// Alice can add todos
await Todo.objects.create({
    todo_list_id: sharedList.id,
    title: "Review PR #123",
    priority: "high"
});

// Alice can update todos
await Todo.objects.update({ id: 5 }, { status: "completed" });

// ✗ Alice cannot update the list itself (only Bob can)
await TodoList.objects.update({ id: sharedList.id }, { name: "New Name" });
// Error: 404 Not Found (filtered out by filter_write)

// ✗ Alice cannot delete the list
await TodoList.objects.delete({ id: sharedList.id });
// Error: 404 Not Found

// ✗ Alice cannot add members
await TodoListMembership.objects.create({
    todo_list_id: sharedList.id,
    user_id: 3,
    role: "member"
});
// Error: 403 "Only list owners can add members"


// ============================================================
// TAGS: Shared across all users
// ============================================================

// Anyone can create tags
const workTag = await Tag.objects.create({
    name: "work",
    color: "#10B981"
});

const personalTag = await Tag.objects.create({
    name: "personal",
    color: "#F59E0B"
});

// Tags are visible to everyone
const allTags = await Tag.objects.all();
// Returns all tags created by any user

// Associate tags with todos (via M2M - would need separate endpoint)
// Note: M2M relationships may need custom handling in Guitar
```

---

## Edge Cases Demonstrated

### 1. Personal vs Shared Lists
Personal lists have no memberships - only the owner can access:
```python
def filter_read(self, request, queryset):
    return queryset.filter(
        Q(owner=request.user) | Q(members=request.user)
    )
```

### 2. Auto-tracking Completion
Using `pre_update` to automatically set `completed_at`:
```python
def pre_update(self, request, instance, data):
    if 'status' in data and data['status'] == 'completed':
        if instance.status != 'completed':
            data['completed_at'] = timezone.now()
    return data
```

### 3. Cascading Permissions
Todos inherit access from their parent TodoList:
```python
def filter_read(self, request, queryset):
    return queryset.filter(
        Q(todo_list__owner=request.user) |
        Q(todo_list__members=request.user)
    )
```

### 4. Shared Resources (Tags)
Tags are visible to everyone but only creators can delete:
```python
def filter_read(self, request, queryset):
    return queryset.all()  # Everyone can see

def filter_delete(self, request, queryset):
    return queryset.filter(created_by=request.user)  # Only creator
```

### 5. Preventing Owner Removal
Owners can't remove themselves from their own lists:
```python
def filter_delete(self, request, queryset):
    return queryset.filter(
        todo_list__owner=request.user
    ).exclude(
        user=request.user,
        role='owner'
    )
```

---

## API Endpoints Generated

```
# Todo Lists
GET    /guitar/todolist/              → list (owned + shared)
GET    /guitar/todolist/{id}/         → retrieve
POST   /guitar/todolist/              → create (becomes owner)
PATCH  /guitar/todolist/{id}/         → update (owner only)
DELETE /guitar/todolist/{id}/         → delete (owner only)

# Todos
GET    /guitar/todo/                  → list (via list ownership/membership)
GET    /guitar/todo/{id}/             → retrieve
POST   /guitar/todo/                  → create (owner/member)
PATCH  /guitar/todo/{id}/             → update (owner/member)
DELETE /guitar/todo/{id}/             → delete (owner/member)

# Memberships
GET    /guitar/todolistmembership/    → list (see your lists' members)
POST   /guitar/todolistmembership/    → create (owner invites)
DELETE /guitar/todolistmembership/{id}/ → delete (owner removes)

# Tags
GET    /guitar/tag/                   → list (all tags)
GET    /guitar/tag/{id}/              → retrieve
POST   /guitar/tag/                   → create (anyone)
PATCH  /guitar/tag/{id}/              → update (anyone)
DELETE /guitar/tag/{id}/              → delete (creator only)
```

---

## Possible Extensions

1. **Todo Comments** - Add a `Comment` model with FK to `Todo`:
   ```python
   class Comment(GuitarModel, models.Model):
       todo = models.ForeignKey(Todo, on_delete=models.CASCADE)
       text = models.TextField()
       created_by = models.ForeignKey(User, ...)
       # Inherits permissions from todo via chain_permissions
   ```

2. **Recurring Todos** - Add `recurrence_pattern` and `next_due_date` fields

3. **Todo Dependencies** - Add `depends_on` FK to `Todo` (self-referential)

4. **Sub-todos** - Add `parent` FK to `Todo` for nested todos

5. **Todo Attachments** - Add file upload support (separate endpoint)

6. **List Templates** - Clonable lists with `clone_from_id`

7. **Smart Lists** - Filtered views (e.g., "Overdue", "High Priority")

8. **Activity Log** - Track all changes (write-only model)

