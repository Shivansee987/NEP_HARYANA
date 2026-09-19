"""
NEP Excellence Awards 2026 - College App URL Configuration (Phase 7B)
Forwards routing to versionable API package.
"""
from django.urls import include, path

urlpatterns = [
    path('', include('apps.college.api.urls')),
]
