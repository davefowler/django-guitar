"""
Polls app models following Django's official tutorial structure.
Demonstrates Django Guitar's Model-Level Security (MLS).
"""
from datetime import timedelta
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
                data['pub_date'] = timezone.now().isoformat()
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

