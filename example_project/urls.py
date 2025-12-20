"""
URL configuration for the example project.
"""

from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI

from guitar import GuitarRouter
from guitar.permissions import IsAuthenticated
from example_project.dashboard.models import Dashboard, DashboardMembership, Chart

# Create the Ninja API with guitar as the base
api = NinjaAPI(title="Dashboard API", version="1.0.0", urls_namespace="guitar")

# Create and configure Guitar router
guitar_router = GuitarRouter(
    default_permission_classes=[IsAuthenticated],
)

# Register all Guitar models
guitar_router.register(Dashboard)
guitar_router.register(DashboardMembership)
guitar_router.register(Chart)

# Add Guitar router to the API at root level
api.add_router("", guitar_router.urls)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('guitar/', api.urls),
]
