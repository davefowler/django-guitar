"""Django app configuration for Guitar."""

from django.apps import AppConfig


class GuitarConfig(AppConfig):
    name = 'guitar'
    verbose_name = 'Django Guitar'
    default_auto_field = 'django.db.models.BigAutoField'
