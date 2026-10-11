from django.urls import path
from .views import (
    CollegeListView,
    CollegeAisheLookupView,
    RegisterView,
    UniversityAisheLookupView,
    UniversityRegisterView,
    LoginView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    LogoutView,
    RefreshTokenView,
    MeView,
    SendOTPView,
    VerifyOTPView
)

urlpatterns = [
    # Public list for the signup form; /api/colleges/ is the authenticated college API (apps.college).
    path('auth/colleges/', CollegeListView.as_view(), name='college-list'),
    path('auth/college/lookup/', CollegeAisheLookupView.as_view(), name='college-aishe-lookup'),
    path('auth/colleges/lookup/', CollegeAisheLookupView.as_view(), name='colleges-aishe-lookup'),
    # OTP verification endpoints
    path('auth/otp/send/', SendOTPView.as_view(), name='otp-send'),
    path('auth/otp/verify/', VerifyOTPView.as_view(), name='otp-verify'),
    path('auth/send-otp/', SendOTPView.as_view(), name='send-otp'),
    path('auth/verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    # University AISHE lookup and applicant registration
    path('auth/university/lookup/', UniversityAisheLookupView.as_view(), name='university-aishe-lookup'),
    path('auth/universities/lookup/', UniversityAisheLookupView.as_view(), name='universities-aishe-lookup'),
    path('auth/university/register/', UniversityRegisterView.as_view(), name='university-register'),
    path('auth/university/signup/', UniversityRegisterView.as_view(), name='university-signup'),
    # College and general registration
    path('auth/signup/', RegisterView.as_view(), name='signup'),
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/refresh/', RefreshTokenView.as_view(), name='refresh'),
    path('auth/me/', MeView.as_view(), name='me'),
    path('auth/forgot-password/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('auth/reset-password/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
]


