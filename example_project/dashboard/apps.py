"""Django app configuration for Dashboard."""

from django.apps import AppConfig


class DashboardConfig(AppConfig):
    name = 'example_project.dashboard'
    verbose_name = 'Dashboard'
    default_auto_field = 'django.db.models.BigAutoField'
