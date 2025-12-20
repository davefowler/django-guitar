"""
Composable predicates for Guitar permissions.

Inspired by django-rules, predicates allow reusable permission logic
that can be composed with | (or), & (and), and ~ (not) operators.

Example:
    from guitar import predicate
    
    @predicate
    def is_owner(request, obj):
        return obj.user == request.user
    
    @predicate
    def is_admin(request, obj):
        return request.user.is_staff
    
    # Compose predicates
    can_edit = is_owner | is_admin
    can_delete = is_owner & ~is_published
    
    # Use in check_* methods
    if not can_edit(request, instance):
        raise PermissionDenied()
"""

from typing import Any, Callable, Optional, Tuple
from functools import wraps


class Predicate:
    """
    A composable predicate for permission checks.
    
    Predicates wrap functions that take (request, obj, *args, **kwargs)
    and return a boolean indicating if the permission is granted.
    """
    
    def __init__(
        self,
        fn: Callable[..., bool],
        name: Optional[str] = None,
        bind: bool = False,
    ) -> None:
        """
        Initialize a predicate.
        
        Args:
            fn: The predicate function (request, obj, *args, **kwargs) -> bool
            name: Optional name for the predicate (defaults to function name)
            bind: If True, the first argument is 'self' (for method predicates)
        """
        self.fn = fn
        self.name = name or getattr(fn, '__name__', 'predicate')
        self.bind = bind
        self._curried_args: Tuple = ()
        self._curried_kwargs: dict = {}
        
        # Preserve function metadata
        wraps(fn)(self)
    
    def __call__(self, request: Any, obj: Any = None, *args, **kwargs) -> bool:
        """
        Evaluate the predicate.
        
        Args:
            request: The HTTP request object
            obj: The object being checked (can be None for create operations)
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
            
        Returns:
            True if the predicate passes, False otherwise
        """
        # Merge curried arguments
        all_args = self._curried_args + args
        all_kwargs = {**self._curried_kwargs, **kwargs}
        
        try:
            return bool(self.fn(request, obj, *all_args, **all_kwargs))
        except (AttributeError, TypeError):
            # If the object doesn't have the required attributes, deny
            return False
    
    def curry(self, *args, **kwargs) -> 'Predicate':
        """
        Return a new predicate with some arguments pre-filled.
        
        Example:
            @predicate
            def has_role(request, obj, role):
                return obj.memberships.filter(user=request.user, role=role).exists()
            
            can_manage = has_role.curry('admin') | has_role.curry('owner')
        """
        curried = Predicate(self.fn, name=f"{self.name}(*)")
        curried._curried_args = self._curried_args + args
        curried._curried_kwargs = {**self._curried_kwargs, **kwargs}
        return curried
    
    def __or__(self, other: 'Predicate') -> 'Predicate':
        """
        Combine predicates with OR (|).
        
        Returns a new predicate that passes if either predicate passes.
        """
        def or_fn(request, obj, *args, **kwargs):
            return self(request, obj, *args, **kwargs) or other(request, obj, *args, **kwargs)
        
        return Predicate(or_fn, name=f"({self.name} | {other.name})")
    
    def __and__(self, other: 'Predicate') -> 'Predicate':
        """
        Combine predicates with AND (&).
        
        Returns a new predicate that passes only if both predicates pass.
        """
        def and_fn(request, obj, *args, **kwargs):
            return self(request, obj, *args, **kwargs) and other(request, obj, *args, **kwargs)
        
        return Predicate(and_fn, name=f"({self.name} & {other.name})")
    
    def __invert__(self) -> 'Predicate':
        """
        Negate a predicate with NOT (~).
        
        Returns a new predicate that passes if the original fails.
        """
        def not_fn(request, obj, *args, **kwargs):
            return not self(request, obj, *args, **kwargs)
        
        return Predicate(not_fn, name=f"~{self.name}")
    
    def __xor__(self, other: 'Predicate') -> 'Predicate':
        """
        Combine predicates with XOR (^).
        
        Returns a new predicate that passes if exactly one predicate passes.
        """
        def xor_fn(request, obj, *args, **kwargs):
            a = self(request, obj, *args, **kwargs)
            b = other(request, obj, *args, **kwargs)
            return a != b
        
        return Predicate(xor_fn, name=f"({self.name} ^ {other.name})")
    
    def __repr__(self) -> str:
        return f"<Predicate: {self.name}>"


def predicate(fn: Callable[..., bool] = None, name: Optional[str] = None) -> Predicate:
    """
    Decorator to create a composable predicate.
    
    Usage:
        @predicate
        def is_owner(request, obj):
            return obj.user == request.user
        
        @predicate(name="custom_name")
        def my_predicate(request, obj):
            return True
    
    Args:
        fn: The predicate function
        name: Optional custom name for the predicate
        
    Returns:
        A Predicate instance
    """
    def decorator(fn: Callable[..., bool]) -> Predicate:
        return Predicate(fn, name=name)
    
    if fn is not None:
        # Called without arguments: @predicate
        return decorator(fn)
    
    # Called with arguments: @predicate(name="...")
    return decorator


# Common built-in predicates
@predicate
def is_authenticated(request, obj=None):
    """Check if the user is authenticated."""
    return bool(request.user and request.user.is_authenticated)


@predicate
def is_staff(request, obj=None):
    """Check if the user is a staff member."""
    return bool(request.user and request.user.is_staff)


@predicate
def is_superuser(request, obj=None):
    """Check if the user is a superuser."""
    return bool(request.user and request.user.is_superuser)


@predicate
def is_owner(request, obj):
    """Check if the user owns the object (via 'user' field)."""
    if obj is None:
        return True
    return getattr(obj, 'user', None) == request.user or getattr(obj, 'user_id', None) == request.user.id


@predicate
def is_creator(request, obj):
    """Check if the user created the object (via 'created_by' field)."""
    if obj is None:
        return True
    return getattr(obj, 'created_by', None) == request.user or getattr(obj, 'created_by_id', None) == request.user.id


@predicate
def always_allow(request, obj=None):
    """Always return True."""
    return True


@predicate
def always_deny(request, obj=None):
    """Always return False."""
    return False
