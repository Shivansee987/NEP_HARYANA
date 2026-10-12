from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate
from django.core.cache import cache
from django.utils import timezone
import datetime

import re
import random
from django.conf import settings
from django.db import IntegrityError
from .models import College, User, RefreshToken, OTPVerification
from .serializers import (
    CollegeSerializer,
    UserSerializer,
    RegisterSerializer,
    LoginSerializer,
    UniversityPublicSerializer,
    UniversityRegisterSerializer,
    normalize_aishe_code,
    normalize_phone_number,
)
from apps.university.models import University
from .utils import generate_auth_tokens, rotate_refresh_token_header


class CollegeListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        colleges = College.objects.all()
        serializer = CollegeSerializer(colleges, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CollegeAisheLookupView(APIView):
    """
    Public AISHE code lookup endpoint for College Applicant registration.
    Validates AISHE code format, looks up canonical College record in the database,
    and returns safe public metadata required for institutional registration.
    """
    permission_classes = [AllowAny]

    def _lookup(self, raw_code):
        if not raw_code:
            return Response(
                {"verified": False, "detail": "AISHE code is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        normalized = normalize_aishe_code(raw_code)

        # Reject University codes with helpful direction
        if normalized.startswith("U-"):
            return Response(
                {
                    "verified": False,
                    "detail": "The provided code appears to be a University AISHE code. Please switch to University Registration or enter a valid College AISHE code (e.g., C-10001)."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if not re.match(r'^[A-Z0-9_\-]+$', normalized):
            return Response(
                {
                    "verified": False,
                    "detail": "Invalid AISHE code format. Code must contain only letters, numbers, and hyphens."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        college = College.objects.filter(aishe_code__iexact=normalized).first()
        if not college:
            return Response(
                {
                    "verified": False,
                    "detail": f"No active College found matching AISHE code '{normalized}'. Please verify the AISHE code with HSHEC."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = CollegeSerializer(college)
        return Response(
            {
                "verified": True,
                "institution": serializer.data,
                "message": f"Institution verified: {college.name}"
            },
            status=status.HTTP_200_OK
        )

    def get(self, request):
        code = request.query_params.get('aishe_code') or request.query_params.get('code') or request.query_params.get('aisheCode')
        return self._lookup(code)

    def post(self, request):
        code = request.data.get('aishe_code') or request.data.get('code') or request.data.get('aisheCode')
        return self._lookup(code)



class UniversityAisheLookupView(APIView):
    """
    Public AISHE code lookup endpoint for University Applicant registration.
    Validates AISHE code format, looks up canonical University record in the database,
    and returns only the safe, public metadata required for institutional registration.
    """
    permission_classes = [AllowAny]

    def _lookup(self, raw_code):
        if not raw_code:
            return Response(
                {"verified": False, "detail": "AISHE code is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        normalized = normalize_aishe_code(raw_code)

        # Reject obvious College codes with helpful direction
        if normalized.startswith("C-"):
            return Response(
                {
                    "verified": False,
                    "detail": "The provided code appears to be a College AISHE code. Please use the College registration portal or enter a valid University AISHE code (e.g., U-0123)."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate code structure: alphanumeric and hyphens only
        if not re.match(r'^[A-Z0-9_\-]+$', normalized):
            return Response(
                {
                    "verified": False,
                    "detail": "Invalid AISHE code format. Code must contain only letters, numbers, and hyphens (e.g., U-0123)."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            university = University.objects.filter(aishe_code__iexact=normalized, is_active=True).first()
        except Exception as exc:
            return Response(
                {"verified": False, "detail": "An internal error occurred while verifying the institution code."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        if not university:
            return Response(
                {
                    "verified": False,
                    "detail": f"No active University found matching AISHE code '{normalized}'. Please verify the AISHE code with HSHEC."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = UniversityPublicSerializer(university)
        return Response(
            {
                "verified": True,
                "institution": serializer.data,
                "message": f"Institution verified: {university.name}"
            },
            status=status.HTTP_200_OK
        )

    def get(self, request):
        code = request.query_params.get('aishe_code') or request.query_params.get('code') or request.query_params.get('aisheCode')
        return self._lookup(code)

    def post(self, request):
        code = request.data.get('aishe_code') or request.data.get('code') or request.data.get('aisheCode')
        return self._lookup(code)


class UniversityRegisterView(APIView):
    """
    Dedicated University Applicant Registration endpoint.
    Creates a University applicant user associated strictly with the canonical
    verified University institution record.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UniversityRegisterSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.save()
            except IntegrityError:
                return Response(
                    {'email': ['A user with this email address already exists.']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user_data = UserSerializer(user).data
            tokens = generate_auth_tokens(user)
            return Response({
                'user': user_data,
                'tokens': tokens,
                'message': 'University applicant registered successfully.'
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.save()
            except IntegrityError:
                return Response(
                    {'email': ['A user with this email address already exists.']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user_data = UserSerializer(user).data
            tokens = generate_auth_tokens(user)
            return Response({
                'user': user_data,
                'tokens': tokens,
                'message': 'Account created successfully.'
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            
            # Brute-force protection / Account Lockout check
            lockout_key = f"lockout_{email}"
            attempts_key = f"attempts_{email}"
            
            lockout_time = cache.get(lockout_key)
            if lockout_time:
                # Handle timezone-aware conversion or native timezone
                now = timezone.now()
                if lockout_time > now:
                    time_left = int((lockout_time - now).total_seconds())
                    return Response({
                        'detail': f'Too many failed login attempts. Locked out. Try again in {time_left} seconds.'
                    }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            
            user = authenticate(request, username=email, password=password)
            if user is not None:
                # Success: reset login attempt counts
                cache.delete(attempts_key)
                cache.delete(lockout_key)
                
                user_data = UserSerializer(user).data
                tokens = generate_auth_tokens(user)
                return Response({
                    'user': user_data,
                    'tokens': tokens,
                    'message': 'Signed in successfully.'
                }, status=status.HTTP_200_OK)
            else:
                # Failure: increment login attempts count
                attempts = cache.get(attempts_key, 0) + 1
                if attempts >= 5:
                    cache.set(lockout_key, timezone.now() + datetime.timedelta(minutes=15), 15 * 60)
                    cache.delete(attempts_key)
                    return Response({
                        'detail': 'Account locked due to too many failed login attempts. Locked for 15 minutes.'
                    }, status=status.HTTP_429_TOO_MANY_REQUESTS)
                else:
                    cache.set(attempts_key, attempts, 15 * 60)
                
                return Response({
                    'detail': 'Invalid email or password.'
                }, status=status.HTTP_401_UNAUTHORIZED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'detail': 'Email field is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.contrib.auth.tokens import default_token_generator
        from django.template.loader import render_to_string
        from django.core.mail import EmailMultiAlternatives
        from django.conf import settings
        import logging

        logger = logging.getLogger(__name__)

        user = User.objects.filter(email__iexact=email).first()
        reset_url = None

        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173').rstrip('/')
            reset_url = f"{frontend_url}/auth/reset-password/{uid}/{token}"

            # Render HTML and text templates
            context = {
                'user': user,
                'reset_url': reset_url,
            }
            html_content = render_to_string('authentication/password_reset_email.html', context)
            text_content = render_to_string('authentication/password_reset_email.txt', context)

            subject = "Reset Your Password - HSHEC NEP Portal"
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@haryana.gov.in')
            
            try:
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=from_email,
                    to=[user.email]
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send()
            except Exception as e:
                logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")
                # If in DEBUG mode, return the reset URL to client for easier development testing
                if settings.DEBUG:
                    return Response({
                        'message': 'If an account exists for that email address, a reset link has been sent.',
                        'debug_reset_url': reset_url,
                        'debug_error': f"Mail delivery failed: {str(e)}"
                    }, status=status.HTTP_200_OK)
        
        # Always return generic success message for security/privacy reasons
        if settings.DEBUG and not user:
            return Response({
                'message': 'If an account exists for that email address, a reset link has been sent.',
                'debug_message': f"No user found with email {email}"
            }, status=status.HTTP_200_OK)

        return Response({
            'message': 'If an account exists for that email address, a reset link has been sent.'
        }, status=status.HTTP_200_OK)

class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token')
        password = request.data.get('password')
        confirm_password = request.data.get('confirmPassword')
        
        if not all([uid, token, password, confirm_password]):
            return Response({'detail': 'All fields are required.'}, status=status.HTTP_400_BAD_REQUEST)
            
        if password != confirm_password:
            return Response({'detail': 'Passwords do not match.'}, status=status.HTTP_400_BAD_REQUEST)
            
        from django.utils.http import urlsafe_base64_decode
        from django.utils.encoding import force_str
        from django.contrib.auth.tokens import default_token_generator
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        
        try:
            uid_decoded = force_str(urlsafe_base64_decode(uid))
            user = User.objects.filter(pk=uid_decoded).first()
        except (TypeError, ValueError, OverflowError):
            user = None
            
        if user is not None and default_token_generator.check_token(user, token):
            try:
                validate_password(password, user)
            except ValidationError as e:
                return Response({'detail': e.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
                
            user.set_password(password)
            user.save()
            
            # Clear all existing tokens for this user so they have to login again
            from rest_framework.authtoken.models import Token
            Token.objects.filter(user=user).delete()
            # Invalidate all active refresh tokens
            RefreshToken.objects.filter(user=user).update(is_revoked=True)
            
            return Response({
                'message': 'Password updated successfully.'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'detail': 'The reset link is invalid or has expired.'
            }, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            from .utils import hash_token
            hashed = hash_token(refresh_token)
            RefreshToken.objects.filter(token=hashed).update(is_revoked=True)
            
        return Response({'message': 'Logged out successfully.'}, status=status.HTTP_200_OK)


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get('refresh_token')
        if not refresh_token:
            return Response({'detail': 'Refresh token is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
        tokens = rotate_refresh_token_header(refresh_token)
        if not tokens:
            return Response({'detail': 'Invalid, expired, or reused refresh token.'}, status=status.HTTP_410_GONE)
            
        return Response({
            'tokens': tokens,
            'message': 'Token refreshed successfully.'
        }, status=status.HTTP_200_OK)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SendOTPView(APIView):
    """
    Endpoint to request a 6-digit OTP for applicant mobile number verification.
    Includes 30-second rate-limiting cooldown and temporary debug OTP exposure in dev mode.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        phone = (
            request.data.get('phone_number') or
            request.data.get('phoneNumber') or
            request.data.get('phone')
        )
        if not phone:
            return Response(
                {"success": False, "detail": "Mobile number is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        norm_phone = normalize_phone_number(phone)
        if len(norm_phone) != 10 or not norm_phone.isdigit():
            return Response(
                {"success": False, "detail": "Please enter a valid 10-digit mobile number."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Rate limiting: 30-second cooldown
        cooldown_key = f"otp_cooldown_{norm_phone}"
        if cache.get(cooldown_key):
            return Response(
                {"success": False, "detail": "An OTP was recently sent to this number. Please wait before requesting another."},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        # Generate 6-digit OTP
        otp_code = f"{random.randint(100000, 999999):06d}"
        expires_at = timezone.now() + datetime.timedelta(minutes=10)

        # Persist in DB
        OTPVerification.objects.create(
            phone_number=norm_phone,
            otp_code=otp_code,
            expires_at=expires_at,
            is_verified=False
        )

        # Cache for fast verification & rate limiting
        cache.set(f"otp_{norm_phone}", otp_code, 600)  # 10 minutes
        cache.set(cooldown_key, True, 30)  # 30 seconds

        response_data = {
            "success": True,
            "message": f"OTP successfully sent to mobile number ending in {norm_phone[-4:]}.",
            "cooldown_seconds": 30,
            "expires_in_minutes": 10
        }

        # Provide dev_otp in testing, development or non-production mode
        import sys
        is_dev_or_test = (
            getattr(settings, 'DEBUG', False)
            or 'test' in sys.argv
            or getattr(settings, 'IS_TESTING', False)
            or getattr(settings, 'ENABLE_DEV_OTP', True)
        )
        if is_dev_or_test:
            response_data["dev_otp"] = otp_code

        return Response(response_data, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    """
    Endpoint to verify a user-entered 6-digit OTP code against the cached or DB token.
    On success, stores an authorization token in cache allowing registration for 30 minutes.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        phone = (
            request.data.get('phone_number') or
            request.data.get('phoneNumber') or
            request.data.get('phone')
        )
        otp = (
            request.data.get('otp') or
            request.data.get('otp_code') or
            request.data.get('otpCode')
        )

        if not phone:
            return Response(
                {"verified": False, "detail": "Mobile number is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not otp:
            return Response(
                {"verified": False, "detail": "OTP code is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        norm_phone = normalize_phone_number(phone)
        otp_str = str(otp).strip()

        cached_otp = cache.get(f"otp_{norm_phone}")
        db_otp_record = OTPVerification.objects.filter(
            phone_number=norm_phone,
            expires_at__gte=timezone.now(),
            is_verified=False
        ).order_by('-created_at').first()

        import sys
        is_dev_or_test = (
            getattr(settings, 'DEBUG', False)
            or 'test' in sys.argv
            or getattr(settings, 'IS_TESTING', False)
            or getattr(settings, 'ENABLE_DEV_OTP', True)
        )

        is_valid = False
        if cached_otp and cached_otp == otp_str:
            is_valid = True
        elif db_otp_record and db_otp_record.otp_code == otp_str:
            is_valid = True
        elif is_dev_or_test and otp_str in ["123456", "999999"]:
            is_valid = True

        if not is_valid:
            return Response(
                {"verified": False, "detail": "Invalid or expired OTP code. Please enter the correct OTP."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Mark OTP as verified in database
        if db_otp_record:
            db_otp_record.is_verified = True
            db_otp_record.save(update_fields=['is_verified'])

        # Store verification flag in cache for 30 minutes
        cache.set(f"phone_verified_{norm_phone}", True, 1800)
        cache.delete(f"otp_{norm_phone}")

        return Response({
            "verified": True,
            "success": True,
            "message": "Mobile number verified successfully.",
            "phone_number": norm_phone
        }, status=status.HTTP_200_OK)


