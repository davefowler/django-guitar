"""
Django Guitar 🎸

Automatically generate a Django-like ORM for the frontend from your Django models.
"""

from guitar.models import GuitarModel
from guitar.router import GuitarRouter
from guitar.permissions import IsAuthenticated, AllowAny
from guitar.predicates import (
    predicate,
    Predicate,
    is_authenticated,
    is_staff,
    is_superuser,
    is_owner,
    is_creator,
    always_allow,
    always_deny,
)

__version__ = "0.1.0"
__all__ = [
    "GuitarModel",
    "GuitarRouter",
    "IsAuthenticated",
    "AllowAny",
    "predicate",
    "Predicate",
    "is_authenticated",
    "is_staff",
    "is_superuser",
    "is_owner",
    "is_creator",
    "always_allow",
    "always_deny",
]
