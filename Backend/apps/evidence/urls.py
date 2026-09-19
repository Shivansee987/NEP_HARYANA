"""
NEP Excellence Awards 2026 - Evidence App URL Configuration
Forwards routing to versionable API package.
"""
from django.urls import include, path

urlpatterns = [
    path('', include('apps.evidence.api.urls')),
]
