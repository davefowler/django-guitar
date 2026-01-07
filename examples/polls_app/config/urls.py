"""
URL configuration for polls_app project.
"""
from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI

from guitar import GuitarRouter
from polls.models import Question, Choice

# Create the Ninja API
api = NinjaAPI(title="Polls API", version="1.0.0", urls_namespace="guitar")

# Create and configure Guitar router (no auth required for demo)
guitar_router = GuitarRouter()

# Register all Guitar models
guitar_router.register(Question)
guitar_router.register(Choice)

# Add Guitar router to the API at root level
api.add_router("", guitar_router.urls)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('guitar/', api.urls),
]
