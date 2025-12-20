"""
Pytest configuration for Django Guitar tests.
"""

import os
import django
from django.conf import settings


def pytest_configure():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'example_project.settings')
    django.setup()
