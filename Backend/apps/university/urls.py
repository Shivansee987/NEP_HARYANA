"""
NEP Excellence Awards 2026 - University App URL Configuration
Forwards routing to versionable API package.
"""
from django.urls import include, path

urlpatterns = [
    path('', include('apps.university.api.urls')),
]
