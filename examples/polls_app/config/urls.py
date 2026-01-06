"""
URL configuration for polls_app project.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('guitar/', include('guitar.urls')),
    # Serve React app for all other routes
    path('', TemplateView.as_view(template_name='index.html'), name='index'),
]

