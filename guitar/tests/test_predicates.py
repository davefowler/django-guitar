"""
Tests for Guitar predicates - composable permission logic.
"""

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User, AnonymousUser

from guitar import predicate, Predicate
from guitar.predicates import (
    is_authenticated,
    is_staff,
    is_superuser,
    is_owner,
    is_creator,
    always_allow,
    always_deny,
)


class MockObject:
    """Mock object for testing predicates."""
    
    def __init__(self, user=None, created_by=None, status='draft', is_public=False):
        self.user = user
        self.user_id = user.id if user else None
        self.created_by = created_by
        self.created_by_id = created_by.id if created_by else None
        self.status = status
        self.is_public = is_public


class PredicateTests(TestCase):
    """Tests for the Predicate class and @predicate decorator."""
    
    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.user = User.objects.create_user('testuser', 'test@test.com', 'pass')
        self.other_user = User.objects.create_user('other', 'other@test.com', 'pass')
        self.staff_user = User.objects.create_user('staff', 'staff@test.com', 'pass', is_staff=True)
        self.superuser = User.objects.create_superuser('admin', 'admin@test.com', 'pass')
        
        self.obj = MockObject(user=self.user, created_by=self.user)
        self.other_obj = MockObject(user=self.other_user, created_by=self.other_user)
    
    def _make_request(self, user):
        """Create a mock request with the given user."""
        request = self.factory.get('/')
        request.user = user
        return request
    
    # === Basic predicate tests ===
    
    def test_predicate_decorator(self):
        """Test the @predicate decorator creates a Predicate."""
        @predicate
        def my_pred(request, obj):
            return True
        
        self.assertIsInstance(my_pred, Predicate)
        self.assertEqual(my_pred.name, 'my_pred')
    
    def test_predicate_decorator_with_name(self):
        """Test @predicate with custom name."""
        @predicate(name="custom_name")
        def my_pred(request, obj):
            return True
        
        self.assertEqual(my_pred.name, 'custom_name')
    
    def test_predicate_evaluation(self):
        """Test predicate returns correct boolean."""
        @predicate
        def always_true(request, obj):
            return True
        
        @predicate
        def always_false(request, obj):
            return False
        
        request = self._make_request(self.user)
        
        self.assertTrue(always_true(request, self.obj))
        self.assertFalse(always_false(request, self.obj))
    
    # === Built-in predicate tests ===
    
    def test_is_authenticated_with_authenticated_user(self):
        """is_authenticated returns True for authenticated users."""
        request = self._make_request(self.user)
        self.assertTrue(is_authenticated(request))
    
    def test_is_authenticated_with_anonymous_user(self):
        """is_authenticated returns False for anonymous users."""
        request = self._make_request(AnonymousUser())
        self.assertFalse(is_authenticated(request))
    
    def test_is_staff_with_staff_user(self):
        """is_staff returns True for staff users."""
        request = self._make_request(self.staff_user)
        self.assertTrue(is_staff(request))
    
    def test_is_staff_with_regular_user(self):
        """is_staff returns False for regular users."""
        request = self._make_request(self.user)
        self.assertFalse(is_staff(request))
    
    def test_is_superuser_with_superuser(self):
        """is_superuser returns True for superusers."""
        request = self._make_request(self.superuser)
        self.assertTrue(is_superuser(request))
    
    def test_is_owner_with_owner(self):
        """is_owner returns True when user owns the object."""
        request = self._make_request(self.user)
        self.assertTrue(is_owner(request, self.obj))
    
    def test_is_owner_with_non_owner(self):
        """is_owner returns False when user doesn't own the object."""
        request = self._make_request(self.other_user)
        self.assertFalse(is_owner(request, self.obj))
    
    def test_is_creator_with_creator(self):
        """is_creator returns True when user created the object."""
        request = self._make_request(self.user)
        self.assertTrue(is_creator(request, self.obj))
    
    def test_always_allow(self):
        """always_allow returns True."""
        request = self._make_request(self.user)
        self.assertTrue(always_allow(request, self.obj))
    
    def test_always_deny(self):
        """always_deny returns False."""
        request = self._make_request(self.user)
        self.assertFalse(always_deny(request, self.obj))
    
    # === Composition tests ===
    
    def test_or_composition(self):
        """Test | (or) composition."""
        @predicate
        def is_owner_pred(request, obj):
            return obj.user == request.user
        
        @predicate
        def is_admin_pred(request, obj):
            return request.user.is_staff
        
        can_view = is_owner_pred | is_admin_pred
        
        # Owner can view
        request = self._make_request(self.user)
        self.assertTrue(can_view(request, self.obj))
        
        # Admin can view (even not owner)
        request = self._make_request(self.staff_user)
        self.assertTrue(can_view(request, self.obj))
        
        # Non-owner non-admin cannot view
        request = self._make_request(self.other_user)
        self.assertFalse(can_view(request, self.obj))
    
    def test_and_composition(self):
        """Test & (and) composition."""
        @predicate
        def is_owner_pred(request, obj):
            return obj.user == request.user
        
        @predicate
        def is_draft(request, obj):
            return obj.status == 'draft'
        
        can_delete = is_owner_pred & is_draft
        
        # Owner of draft can delete
        request = self._make_request(self.user)
        self.assertTrue(can_delete(request, self.obj))
        
        # Non-owner cannot delete even if draft
        request = self._make_request(self.other_user)
        self.assertFalse(can_delete(request, self.obj))
        
        # Owner cannot delete published
        published_obj = MockObject(user=self.user, status='published')
        request = self._make_request(self.user)
        self.assertFalse(can_delete(request, published_obj))
    
    def test_not_composition(self):
        """Test ~ (not) composition."""
        @predicate
        def is_published(request, obj):
            return obj.status == 'published'
        
        is_not_published = ~is_published
        
        request = self._make_request(self.user)
        
        # Draft is not published
        self.assertTrue(is_not_published(request, self.obj))
        
        # Published is published
        published_obj = MockObject(user=self.user, status='published')
        self.assertFalse(is_not_published(request, published_obj))
    
    def test_complex_composition(self):
        """Test complex predicate composition."""
        @predicate
        def is_owner_pred(request, obj):
            return obj.user == request.user
        
        @predicate
        def is_admin_pred(request, obj):
            return request.user.is_staff
        
        @predicate
        def is_published(request, obj):
            return obj.status == 'published'
        
        # (owner OR admin) AND NOT published
        can_edit = (is_owner_pred | is_admin_pred) & ~is_published
        
        request = self._make_request(self.user)
        
        # Owner can edit draft
        self.assertTrue(can_edit(request, self.obj))
        
        # Owner cannot edit published
        published_obj = MockObject(user=self.user, status='published')
        self.assertFalse(can_edit(request, published_obj))
        
        # Admin can edit draft (not their own)
        request = self._make_request(self.staff_user)
        self.assertTrue(can_edit(request, self.obj))
    
    # === Curry tests ===
    
    def test_curry(self):
        """Test predicate currying."""
        @predicate
        def has_status(request, obj, status):
            return obj.status == status
        
        is_draft = has_status.curry('draft')
        is_published = has_status.curry('published')
        
        request = self._make_request(self.user)
        
        self.assertTrue(is_draft(request, self.obj))
        self.assertFalse(is_published(request, self.obj))
        
        published_obj = MockObject(user=self.user, status='published')
        self.assertFalse(is_draft(request, published_obj))
        self.assertTrue(is_published(request, published_obj))
    
    def test_curry_with_composition(self):
        """Test curried predicates can be composed."""
        @predicate
        def has_role(request, obj, role):
            # Mock role check
            return role == 'admin' and request.user.is_staff
        
        is_admin_role = has_role.curry('admin')
        is_editor_role = has_role.curry('editor')
        
        can_manage = is_admin_role | is_editor_role
        
        request = self._make_request(self.staff_user)
        self.assertTrue(can_manage(request, self.obj))
        
        request = self._make_request(self.user)
        self.assertFalse(can_manage(request, self.obj))
    
    # === Edge cases ===
    
    def test_predicate_with_none_object(self):
        """Test predicate handles None object (for create operations)."""
        request = self._make_request(self.user)
        
        # is_owner returns True for None (allows create)
        self.assertTrue(is_owner(request, None))
        
        # is_creator returns True for None
        self.assertTrue(is_creator(request, None))
    
    def test_predicate_with_missing_attribute(self):
        """Test predicate handles objects missing expected attributes."""
        @predicate
        def check_nonexistent(request, obj):
            return obj.nonexistent_field == 'value'
        
        request = self._make_request(self.user)
        # Should return False, not raise
        self.assertFalse(check_nonexistent(request, self.obj))
    
    def test_predicate_repr(self):
        """Test predicate string representation."""
        @predicate
        def my_pred(request, obj):
            return True
        
        self.assertEqual(repr(my_pred), '<Predicate: my_pred>')
        
        composed = my_pred | my_pred
        self.assertIn('|', repr(composed))
