from django.urls import path
from .views import (
    CollegeListView,
    UniversityListView,
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
    VerifyOTPView,
    AccountActivationVerifyView,
    AccountActivationConfirmView,
    EmailVerificationVerifyView,
    EmailVerificationConfirmView,
    EmailVerificationResendView,
    EmailOTPVerifyView,
    EmailOTPResendView,
    EmailOTPRequestView,
)

urlpatterns = [
    # Public list for the signup form; /api/colleges/ is the authenticated college API (apps.college).
    path('auth/colleges/', CollegeListView.as_view(), name='college-list'),
    path('auth/universities/', UniversityListView.as_view(), name='university-list'),
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
    path('auth/password/reset/', PasswordResetRequestView.as_view(), name='password-reset-request-alias'),
    path('auth/reset-password/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('auth/password/reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm-alias'),
    path('auth/activate/verify/', AccountActivationVerifyView.as_view(), name='account-activation-verify'),
    path('auth/activate/confirm/', AccountActivationConfirmView.as_view(), name='account-activation-confirm'),
    # Email verification endpoints (link-based, backward compatible)
    path('auth/verify-email/', EmailVerificationVerifyView.as_view(), name='email-verify'),
    path('auth/verify-email/confirm/', EmailVerificationConfirmView.as_view(), name='email-verify-confirm'),
    path('auth/resend-verification/', EmailVerificationResendView.as_view(), name='email-resend-verification'),
    # 6-Digit Email OTP verification endpoints
    path('auth/verify-email/otp/', EmailOTPVerifyView.as_view(), name='email-otp-verify'),
    path('auth/verify-email/otp/resend/', EmailOTPResendView.as_view(), name='email-otp-resend'),
    path('auth/verify-email/otp/request/', EmailOTPRequestView.as_view(), name='email-otp-request'),
    path('auth/email-otp/verify/', EmailOTPVerifyView.as_view(), name='email-otp-verify-alias'),
    path('auth/email-otp/resend/', EmailOTPResendView.as_view(), name='email-otp-resend-alias'),
    path('auth/email-otp/request/', EmailOTPRequestView.as_view(), name='email-otp-request-alias'),
]


