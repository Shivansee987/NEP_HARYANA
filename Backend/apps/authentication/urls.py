from django.urls import path
from .views import (
    CollegeListView,
    RegisterView,
    LoginView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    LogoutView,
    RefreshTokenView,
    MeView
)

urlpatterns = [
    # Public list for the signup form; /api/colleges/ is the authenticated college API (apps.college).
    path('auth/colleges/', CollegeListView.as_view(), name='college-list'),
    path('auth/signup/', RegisterView.as_view(), name='signup'),
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/refresh/', RefreshTokenView.as_view(), name='refresh'),
    path('auth/me/', MeView.as_view(), name='me'),
    path('auth/forgot-password/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('auth/reset-password/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
]

