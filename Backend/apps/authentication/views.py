from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate
from django.core.cache import cache
from django.utils import timezone
import datetime

import re
from django.conf import settings
from django.db import IntegrityError
from .models import College, User, RefreshToken
from .serializers import (
    CollegeSerializer,
    CollegeDetailSerializer,
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


class UniversityListView(APIView):
    """
    Public University list endpoint for applicant registration.
    Returns active universities in Haryana so applicants can select their university by name.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        universities = University.objects.filter(is_active=True).order_by('name')
        serializer = UniversityPublicSerializer(universities, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CollegeAisheLookupView(APIView):
    """
    Public AISHE code lookup endpoint for College Applicant registration.
    Validates AISHE code format, looks up canonical College record in the database,
    and returns safe public metadata required for institutional registration.
    """
    permission_classes = [AllowAny]

    def _lookup(self, raw_code, institute_code=None):
        raw_code = (raw_code or "").strip()
        institute_code = (institute_code or "").strip()

        if not raw_code and not institute_code:
            return Response(
                {"verified": False, "detail": "AISHE code or DHE Institute code is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Both identifiers provided: check for conflicts
        if raw_code and institute_code:
            normalized_aishe = normalize_aishe_code(raw_code)
            college = College.objects.filter(institute_code=institute_code).first()
            if not college:
                return Response(
                    {"verified": False, "detail": f"No active College found matching Institute code '{institute_code}'."},
                    status=status.HTTP_404_NOT_FOUND
                )
            if college.aishe_code and college.aishe_code.upper() != normalized_aishe.upper():
                return Response(
                    {
                        "verified": False,
                        "detail": f"Conflicting identifiers: Institute code '{institute_code}' belongs to AISHE '{college.aishe_code}', not '{normalized_aishe}'."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer = CollegeDetailSerializer(college)
            return Response(
                {"verified": True, "institution": serializer.data, "message": f"Institution verified: {college.name}"},
                status=status.HTTP_200_OK
            )

        # 2. Only institute_code provided, or raw_code is purely numeric
        if institute_code or (raw_code and raw_code.isdigit()):
            target_code = institute_code or raw_code
            college = College.objects.filter(institute_code=target_code).first()
            if not college:
                return Response(
                    {"verified": False, "detail": f"No active College found matching Institute code '{target_code}'."},
                    status=status.HTTP_404_NOT_FOUND
                )
            serializer = CollegeDetailSerializer(college)
            return Response(
                {"verified": True, "institution": serializer.data, "message": f"Institution verified: {college.name}"},
                status=status.HTTP_200_OK
            )

        # 3. Standard AISHE code lookup
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

        colleges = College.objects.filter(aishe_code__iexact=normalized)
        if colleges.count() > 1:
            return Response(
                {
                    "verified": False,
                    "ambiguous": True,
                    "detail": f"Multiple institutions share AISHE code '{normalized}'. Please specify your DHE Institute Code to complete verification.",
                    "matches": [
                        {
                            "id": c.id,
                            "name": c.name,
                            "institute_code": c.institute_code,
                            "district": c.district,
                            "institute_type": c.institute_type,
                            "institute_category": c.institute_category,
                        }
                        for c in colleges
                    ]
                },
                status=status.HTTP_409_CONFLICT
            )

        college = colleges.first()
        if not college:
            return Response(
                {
                    "verified": False,
                    "detail": f"No active College found matching AISHE code '{normalized}'. Please verify the AISHE code with HSHEC."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = CollegeDetailSerializer(college)
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
        institute_code = request.query_params.get('institute_code') or request.query_params.get('instituteCode')
        return self._lookup(code, institute_code)

    def post(self, request):
        code = request.data.get('aishe_code') or request.data.get('code') or request.data.get('aisheCode')
        institute_code = request.data.get('institute_code') or request.data.get('instituteCode')
        return self._lookup(code, institute_code)



class UniversityAisheLookupView(APIView):
    """
    Public AISHE code lookup endpoint for University Applicant registration.
    Validates AISHE code format, looks up canonical University record in the database,
    and returns only the safe, public metadata required for institutional registration.
    """
    permission_classes = [AllowAny]

    def _lookup(self, raw_code, institute_code=None, university_name=None, university_id=None):
        raw_code = (raw_code or "").strip()
        institute_code = (institute_code or "").strip()
        university_name = (university_name or "").strip()
        university_id = (university_id or "").strip() if isinstance(university_id, str) else university_id

        if not raw_code and not institute_code and not university_name and not university_id:
            return Response(
                {"verified": False, "detail": "AISHE code, DHE Institute code, or University Name is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 0. University ID lookup
        if university_id:
            uni = University.objects.filter(id=university_id, is_active=True).first()
            if not uni:
                return Response(
                    {"verified": False, "detail": f"No active University found matching ID '{university_id}'."},
                    status=status.HTTP_404_NOT_FOUND
                )
            serializer = UniversityPublicSerializer(uni)
            return Response(
                {"verified": True, "institution": serializer.data, "message": f"Institution verified: {uni.name}"},
                status=status.HTTP_200_OK
            )

        # 1. Both AISHE code and institute code provided: check for conflicts
        if raw_code and institute_code:
            normalized_aishe = normalize_aishe_code(raw_code)
            uni = University.objects.filter(institute_code=institute_code, is_active=True).first()
            if not uni:
                return Response(
                    {"verified": False, "detail": f"No active University found matching Institute code '{institute_code}'."},
                    status=status.HTTP_404_NOT_FOUND
                )
            if uni.aishe_code and uni.aishe_code.upper() != normalized_aishe.upper():
                return Response(
                    {
                        "verified": False,
                        "detail": f"Conflicting identifiers: Institute code '{institute_code}' belongs to AISHE '{uni.aishe_code}', not '{normalized_aishe}'."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer = UniversityPublicSerializer(uni)
            return Response(
                {"verified": True, "institution": serializer.data, "message": f"Institution verified: {uni.name}"},
                status=status.HTTP_200_OK
            )

        # 2. Only institute_code provided, or raw_code is purely numeric
        if institute_code or (raw_code and raw_code.isdigit()):
            target_code = institute_code or raw_code
            uni = University.objects.filter(institute_code=target_code, is_active=True).first()
            if not uni:
                return Response(
                    {"verified": False, "detail": f"No active University found matching Institute code '{target_code}'."},
                    status=status.HTTP_404_NOT_FOUND
                )
            serializer = UniversityPublicSerializer(uni)
            return Response(
                {"verified": True, "institution": serializer.data, "message": f"Institution verified: {uni.name}"},
                status=status.HTTP_200_OK
            )

        # 3. Lookup by University Name when AISHE code is not provided
        if not raw_code and university_name:
            unis = University.objects.filter(name__iexact=university_name, is_active=True)
            if not unis.exists():
                unis = University.objects.filter(name__icontains=university_name, is_active=True)
            if unis.count() > 1:
                return Response(
                    {
                        "verified": False,
                        "ambiguous": True,
                        "detail": f"Multiple universities match '{university_name}'. Please select the specific university name or specify its AISHE code.",
                        "matches": [
                            {
                                "id": u.id,
                                "name": u.name,
                                "aishe_code": u.aishe_code,
                                "institute_code": u.institute_code,
                                "district": u.district,
                                "university_type": u.university_type,
                            }
                            for u in unis
                        ]
                    },
                    status=status.HTTP_409_CONFLICT
                )
            university = unis.first()
            if not university:
                return Response(
                    {
                        "verified": False,
                        "detail": f"No active University found matching name '{university_name}'. Please verify the spelling or select from the list."
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

        # 4. Standard AISHE code lookup
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

        unis = University.objects.filter(aishe_code__iexact=normalized, is_active=True)
        if unis.count() > 1:
            return Response(
                {
                    "verified": False,
                    "ambiguous": True,
                    "detail": f"Multiple universities share AISHE code '{normalized}'. Please specify your DHE Institute Code to complete verification.",
                    "matches": [
                        {
                            "id": u.id,
                            "name": u.name,
                            "institute_code": u.institute_code,
                            "district": u.district,
                            "university_type": u.university_type,
                        }
                        for u in unis
                    ]
                },
                status=status.HTTP_409_CONFLICT
            )

        university = unis.first()
        if not university:
            # If AISHE lookup didn't match and a university name was provided, fallback to name
            if university_name:
                alt_uni = University.objects.filter(name__iexact=university_name, is_active=True).first()
                if not alt_uni:
                    alt_uni = University.objects.filter(name__icontains=university_name, is_active=True).first()
                if alt_uni:
                    serializer = UniversityPublicSerializer(alt_uni)
                    return Response(
                        {
                            "verified": True,
                            "institution": serializer.data,
                            "message": f"Institution verified: {alt_uni.name}"
                        },
                        status=status.HTTP_200_OK
                    )
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
        institute_code = request.query_params.get('institute_code') or request.query_params.get('instituteCode')
        name = request.query_params.get('name') or request.query_params.get('university_name') or request.query_params.get('universityName')
        uni_id = request.query_params.get('university_id') or request.query_params.get('universityId') or request.query_params.get('id')
        return self._lookup(code, institute_code, university_name=name, university_id=uni_id)

    def post(self, request):
        code = request.data.get('aishe_code') or request.data.get('code') or request.data.get('aisheCode')
        institute_code = request.data.get('institute_code') or request.data.get('instituteCode')
        name = request.data.get('name') or request.data.get('university_name') or request.data.get('universityName')
        uni_id = request.data.get('university_id') or request.data.get('universityId') or request.data.get('id')
        return self._lookup(code, institute_code, university_name=name, university_id=uni_id)


class UniversityRegisterView(APIView):
    """
    Dedicated University Applicant Registration endpoint.
    Creates a University applicant user associated strictly with the canonical
    verified University institution record in an unverified state.
    Sends single-use email verification link and does not grant authentication tokens.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from .email_verification_service import EmailVerificationService
        from django.db import transaction

        serializer = UniversityRegisterSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    user = serializer.save()
                    raw_token, _ = EmailVerificationService.create_verification_token(user)
                    
                    # Deliver email; if delivery fails, raise exception to trigger clean atomic rollback
                    delivered = EmailVerificationService.send_verification_email(user, raw_token)
                    if not delivered:
                        raise RuntimeError("EMAIL_DELIVERY_FAILED")
            except IntegrityError:
                return Response(
                    {'email': ['A user with this email address already exists.']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except RuntimeError as exc:
                if str(exc) == "EMAIL_DELIVERY_FAILED":
                    return Response({
                        'detail': 'Unable to deliver verification email. Please check your email address or try again later.',
                        'code': 'EMAIL_DELIVERY_FAILED'
                    }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
                raise

            user_data = UserSerializer(user).data
            return Response({
                'user': user_data,
                'message': 'University applicant registered successfully. A 6-digit verification code has been sent to your email address.',
                'email': user.email,
                'verification_sent': True,
                'verification_type': 'OTP',
                'otp_sent': True,
                'redirect_to': '/auth/verify-email/otp',
                'is_email_verified': False,
                'institution_status': user.institution_status,
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RegisterView(APIView):
    """
    Applicant registration endpoint.
    Creates account in pending/unverified state and sends single-use email verification token.
    Does not issue auth tokens until email is verified.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from .email_verification_service import EmailVerificationService
        from django.db import transaction

        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    user = serializer.save()
                    raw_token, _ = EmailVerificationService.create_verification_token(user)
                    
                    # Deliver email; if delivery fails, raise exception to trigger clean atomic rollback
                    delivered = EmailVerificationService.send_verification_email(user, raw_token)
                    if not delivered:
                        raise RuntimeError("EMAIL_DELIVERY_FAILED")
            except IntegrityError:
                return Response(
                    {'email': ['A user with this email address already exists.']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except RuntimeError as exc:
                if str(exc) == "EMAIL_DELIVERY_FAILED":
                    return Response({
                        'detail': 'Unable to deliver verification email. Please check your email address or try again later.',
                        'code': 'EMAIL_DELIVERY_FAILED'
                    }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
                raise

            user_data = UserSerializer(user).data
            return Response({
                'user': user_data,
                'message': 'Account created successfully. A 6-digit verification code has been sent to your email address.',
                'email': user.email,
                'verification_sent': True,
                'verification_type': 'OTP',
                'otp_sent': True,
                'redirect_to': '/auth/verify-email/otp',
                'is_email_verified': False,
                'institution_status': user.institution_status,
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email'].strip().lower()
            password = serializer.validated_data['password']
            # E-mail addresses are stored lower-cased at registration; match legacy mixed-case rows too.
            stored = User.objects.filter(email__iexact=email).values_list('email', flat=True).first()
            login_email = stored or email
            
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
            
            user = authenticate(request, username=login_email, password=password)
            if user is not None:
                # Gating: email verification is required before sign in
                if not getattr(user, 'is_email_verified', False):
                    return Response({
                        'detail': 'Please verify your email address before signing in. Check your inbox for the verification link.',
                        'code': 'EMAIL_NOT_VERIFIED',
                        'email': user.email,
                    }, status=status.HTTP_403_FORBIDDEN)

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
                # Failure: increment login attempts count atomically
                try:
                    # cache.incr raises ValueError if key does not exist in standard backends
                    attempts = cache.incr(attempts_key)
                except (ValueError, Exception):
                    # Key doesn't exist yet; use add to atomically initialize with timeout
                    added = cache.add(attempts_key, 1, timeout=15 * 60)
                    if not added:
                        try:
                            attempts = cache.incr(attempts_key)
                        except Exception:
                            cache.set(attempts_key, 1, timeout=15 * 60)
                            attempts = 1
                    else:
                        attempts = 1

                if attempts >= 5:
                    cache.set(lockout_key, timezone.now() + datetime.timedelta(minutes=15), 15 * 60)
                    cache.delete(attempts_key)
                    return Response({
                        'detail': 'Account locked due to too many failed login attempts. Locked for 15 minutes.'
                    }, status=status.HTTP_429_TOO_MANY_REQUESTS)
                
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

        from .models import UserAuditLog
        from .password_reset import send_password_reset_email

        user = User.objects.filter(email__iexact=str(email).strip()).first()
        # Per-account cooldown so the endpoint cannot be used to flood an inbox.
        cooldown_key = f"pwd_reset_cooldown_{user.pk}" if user else None
        if user and user.is_active and user.has_usable_password() and not cache.get(cooldown_key):
            delivered = send_password_reset_email(user)
            cache.set(cooldown_key, True, 60)
            # The caller always receives the same generic answer (no account enumeration); operators see the
            # delivery outcome in the audit trail.
            UserAuditLog.objects.create(
                actor=None,
                target_user=user,
                action='PASSWORD_RESET_REQUESTED',
                details={'method': 'EMAIL_RECOVERY_LINK', 'delivery': 'SENT' if delivered else 'FAILED'}
            )

        return Response({
            'message': 'If an account exists for that email address, a password reset link has been sent.'
        }, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token')
        password = request.data.get('password')
        confirm_password = request.data.get('confirmPassword') or request.data.get('confirm_password')
        
        if not all([uid, token, password, confirm_password]):
            return Response({'detail': 'All fields are required.'}, status=status.HTTP_400_BAD_REQUEST)
            
        if password != confirm_password:
            return Response({'detail': 'Passwords do not match.'}, status=status.HTTP_400_BAD_REQUEST)
            
        from django.utils.http import urlsafe_base64_decode
        from django.utils.encoding import force_str
        from django.contrib.auth.tokens import default_token_generator
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        from .models import UserAuditLog
        
        try:
            uid_decoded = force_str(urlsafe_base64_decode(uid))
            user = User.objects.filter(pk=uid_decoded).first()
        except (TypeError, ValueError, OverflowError):
            user = None
            
        if user is not None and user.is_active and default_token_generator.check_token(user, token):
            try:
                validate_password(password, user)
            except ValidationError as e:
                return Response({'detail': e.messages[0]}, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(password)
            user.is_email_verified = True
            user.save()

            # End every existing session: outstanding access and refresh JWTs stop working.
            from rest_framework.authtoken.models import Token
            Token.objects.filter(user=user).delete()
            user.revoke_sessions()
            
            UserAuditLog.objects.create(
                actor=user,
                target_user=user,
                action='PASSWORD_RESET',
                details={'method': 'RECOVERY_TOKEN_RESET'}
            )

            return Response({
                'message': 'Password updated successfully. You may now sign in.'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'detail': 'The reset link is invalid or has expired.'
            }, status=status.HTTP_400_BAD_REQUEST)


class AccountActivationVerifyView(APIView):
    """
    Validates a single-use account activation token.
    Returns token status and masked user identity without revealing sensitive tokens.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get('token')
        return self._verify(token)

    def post(self, request):
        token = request.data.get('token')
        return self._verify(token)

    def _verify(self, token):
        if not token:
            return Response({'valid': False, 'detail': 'Activation token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        from apps.authentication.activation_service import AccountActivationService
        is_valid, token_obj, reason = AccountActivationService.verify_token(token)

        if not is_valid:
            error_map = {
                "EXPIRED_TOKEN": "This activation link has expired. Please contact your administrator.",
                "ALREADY_USED": "This activation link has already been used. Please sign in.",
                "REVOKED_TOKEN": "This activation link has been revoked. Please request a new invitation.",
                "INVALID_TOKEN": "Invalid activation link.",
            }
            return Response({
                'valid': False,
                'reason': reason,
                'detail': error_map.get(reason, "Invalid or expired activation link.")
            }, status=status.HTTP_400_BAD_REQUEST)

        user = token_obj.user
        return Response({
            'valid': True,
            'email': user.email,
            'full_name': user.full_name,
            'role': user.role,
            'role_label': user.get_role_display(),
        }, status=status.HTTP_200_OK)


class AccountActivationConfirmView(APIView):
    """
    Consumes a single-use activation token, sets initial user password,
    and activates the administrator account.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get('token')
        password = request.data.get('password')
        confirm_password = request.data.get('confirmPassword') or request.data.get('confirm_password')

        if not token or not password or not confirm_password:
            return Response({'detail': 'All fields are required.'}, status=status.HTTP_400_BAD_REQUEST)

        from apps.authentication.activation_service import AccountActivationService
        try:
            user = AccountActivationService.activate_account(token, password, confirm_password)
            return Response({
                'message': 'Account activated successfully. You can now sign in.',
                'email': user.email
            }, status=status.HTTP_200_OK)
        except Exception as e:
            from rest_framework.exceptions import ValidationError as DRFValidationError
            if isinstance(e, DRFValidationError):
                detail = e.detail.get('detail') if isinstance(e.detail, dict) else e.detail
                return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)



class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        from .authentication import invalidate_user_cache
        if request.user and getattr(request.user, 'is_authenticated', False):
            invalidate_user_cache(request.user.id)

        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            from .utils import hash_token
            hashed = hash_token(refresh_token)
            matched = RefreshToken.objects.filter(token=hashed).select_related('user').first()
            if matched:
                invalidate_user_cache(matched.user_id)
                matched.is_revoked = True
                matched.save(update_fields=['is_revoked'])
            
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
    Sends a 6-digit OTP to a mobile number through the configured SMS provider.
    The code is never returned in the response. If no provider is configured, or the provider refuses the
    message, the endpoint reports failure (503) rather than claiming the SMS was sent.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from .otp_service import OTPError, send_otp
        phone = request.data.get('phone_number') or request.data.get('phoneNumber') or request.data.get('phone')
        if not phone:
            return Response({"success": False, "detail": "Mobile number is required."}, status=status.HTTP_400_BAD_REQUEST)
        norm_phone = normalize_phone_number(phone)
        if len(norm_phone) != 10 or not norm_phone.isdigit():
            return Response({"success": False, "detail": "Please enter a valid 10-digit mobile number."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            send_otp(norm_phone)
        except OTPError as exc:
            return Response({"success": False, "detail": exc.message, "code": exc.code}, status=exc.status)
        return Response({
            "success": True,
            "message": f"OTP sent to mobile number ending in {norm_phone[-4:]}.",
            "cooldown_seconds": settings.OTP_RESEND_COOLDOWN_SECONDS,
            "expires_in_minutes": settings.OTP_TTL_MINUTES,
        }, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    """
    Verifies an OTP. On success returns a single-use `verification_token` that registration must present
    together with the same phone number.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from .otp_service import OTPError, verify_otp
        phone = request.data.get('phone_number') or request.data.get('phoneNumber') or request.data.get('phone')
        otp = request.data.get('otp') or request.data.get('otp_code') or request.data.get('otpCode')
        if not phone:
            return Response({"verified": False, "detail": "Mobile number is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not otp:
            return Response({"verified": False, "detail": "OTP code is required."}, status=status.HTTP_400_BAD_REQUEST)
        norm_phone = normalize_phone_number(phone)
        try:
            token = verify_otp(norm_phone, otp)
        except OTPError as exc:
            return Response({"verified": False, "detail": exc.message, "code": exc.code}, status=exc.status)
        return Response({
            "verified": True,
            "success": True,
            "message": "Mobile number verified successfully.",
            "phone_number": norm_phone,
            "verification_token": token,
            "expires_in_minutes": settings.PHONE_VERIFICATION_TTL_MINUTES,
        }, status=status.HTTP_200_OK)


class EmailVerificationVerifyView(APIView):
    """
    Inspects email verification token status (read-only, does not consume the token).
    Returns token status and masked email so the UI can display appropriate messaging.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get('token')
        if not token:
            return Response({'valid': False, 'reason': 'INVALID_TOKEN', 'detail': 'Verification token is required.'},
                            status=status.HTTP_400_BAD_REQUEST)
        from .email_verification_service import EmailVerificationService
        is_valid, user_or_none, reason = EmailVerificationService.verify_token(token)
        if not is_valid:
            if reason == 'ALREADY_USED' and user_or_none:
                user = getattr(user_or_none, 'user', None)
                if user and getattr(user, 'is_email_verified', False):
                    masked = EmailVerificationService.mask_email(user.email)
                    return Response({
                        'valid': False,
                        'reason': 'ALREADY_VERIFIED',
                        'code': 'ALREADY_VERIFIED',
                        'already_verified': True,
                        'account_already_verified': True,
                        'email': masked,
                        'full_name': user.full_name,
                        'institution_status': user.institution_status,
                        'detail': 'Your email address has already been verified. You can sign in.'
                    }, status=status.HTTP_200_OK)

            status_map = {
                'EXPIRED_TOKEN': (status.HTTP_410_GONE, 'This verification link has expired. Please request a new one.'),
                'ALREADY_USED': (status.HTTP_410_GONE, 'This verification link has already been used.'),
                'REVOKED_TOKEN': (status.HTTP_410_GONE, 'This verification link is no longer valid.'),
                'INVALID_TOKEN': (status.HTTP_400_BAD_REQUEST, 'Invalid verification link.'),
            }
            http_status, message = status_map.get(reason, (status.HTTP_400_BAD_REQUEST, 'Invalid verification link.'))
            return Response({'valid': False, 'reason': reason, 'code': reason, 'detail': message}, status=http_status)

        user = user_or_none.user
        email = user.email
        masked = EmailVerificationService.mask_email(email)
        return Response({
            'valid': True,
            'reason': 'VALID',
            'code': 'VALID',
            'email': masked,
            'full_name': user.full_name,
            'institution_status': user.institution_status,
            'detail': 'Verification link is valid.'
        }, status=status.HTTP_200_OK)


class EmailVerificationConfirmView(APIView):
    """
    Validates and consumes a single-use email verification token.
    Marks user.is_email_verified = True.
    Does NOT grant institutional access; institution_status remains PENDING until administrator approval.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get('token')
        if not token:
            return Response({'detail': 'Verification token is required.', 'code': 'TOKEN_REQUIRED'},
                            status=status.HTTP_400_BAD_REQUEST)
        from .email_verification_service import EmailVerificationService
        try:
            user = EmailVerificationService.confirm_email_verification(token)
            return Response({
                'success': True,
                'message': 'Email address verified successfully. Your account is now awaiting administrator approval.',
                'email': user.email,
                'is_email_verified': True,
                'institution_status': user.institution_status,
            }, status=status.HTTP_200_OK)
        except Exception as exc:
            from rest_framework.exceptions import ValidationError as DRFValidationError
            if isinstance(exc, DRFValidationError):
                code = 'VERIFICATION_FAILED'
                detail = str(exc.detail)
                resp_payload = {}
                if isinstance(exc.detail, dict):
                    code = str(exc.detail.get('code') or exc.detail.get('reason') or 'VERIFICATION_FAILED')
                    detail = str(exc.detail.get('detail') or detail)
                    for k in ('account_already_verified', 'already_verified', 'email'):
                        if k in exc.detail:
                            resp_payload[k] = exc.detail[k]
                http_status = status.HTTP_410_GONE if code in ('EXPIRED_TOKEN', 'ALREADY_USED', 'REVOKED_TOKEN') else status.HTTP_400_BAD_REQUEST
                resp_payload.update({'detail': detail, 'code': code, 'reason': code})
                return Response(resp_payload, status=http_status)
            return Response({'detail': str(exc), 'code': 'VERIFICATION_FAILED'}, status=status.HTTP_400_BAD_REQUEST)


class EmailVerificationResendView(APIView):
    """
    Requests a fresh verification email.
    Enforces cooldown (60s) and hourly rate limiting (5/hr).
    Always returns a generic success message to prevent user enumeration.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'detail': 'Email address is required.'}, status=status.HTTP_400_BAD_REQUEST)

        norm_email = (email or '').strip().lower()
        user = User.objects.filter(email__iexact=norm_email).first()
        if user and user.is_email_verified:
            from .email_otp_service import EmailOTPService
            return Response({
                'success': True,
                'already_verified': True,
                'account_already_verified': True,
                'email': EmailOTPService.mask_email(norm_email),
                'message': 'This email address is already verified. Please sign in to your account.',
                'detail': 'This email address is already verified. Please sign in to your account.',
                'code': 'ALREADY_VERIFIED',
                'redirect_to': '/auth/login',
            }, status=status.HTTP_200_OK)

        if not user:
            return Response({
                'success': False,
                'registered': False,
                'already_verified': False,
                'email': norm_email,
                'code': 'EMAIL_NOT_REGISTERED',
                'message': 'This email address is not associated with a registered account. Please sign up first.',
                'detail': 'This email address is not associated with a registered account. Please sign up first.',
                'redirect_to': '/auth/signup',
            }, status=status.HTTP_404_NOT_FOUND)

        from .email_verification_service import (
            EmailVerificationService,
            VerificationRateLimitError,
            VerificationCooldownError,
            EmailDeliveryError
        )
        try:
            EmailVerificationService.request_resend_verification(email)
        except VerificationCooldownError as exc:
            return Response({
                'detail': str(exc),
                'code': 'COOLDOWN_ACTIVE',
                'retry_after_seconds': exc.retry_after,
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except VerificationRateLimitError as exc:
            return Response({
                'detail': str(exc),
                'code': 'RATE_LIMIT_EXCEEDED',
                'retry_after_seconds': exc.retry_after,
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except EmailDeliveryError as exc:
            return Response({
                'detail': str(exc),
                'code': 'EMAIL_DELIVERY_FAILED',
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response({
            'success': True,
            'already_verified': False,
            'message': 'Verification code sent successfully. Please check your inbox.',
            'detail': 'Verification code sent successfully. Please check your inbox.',
            'redirect_to': '/auth/verify-email/otp',
            'cooldown_seconds': 60,
        }, status=status.HTTP_200_OK)


def get_client_ip(request):
    """Safely extracts client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class EmailOTPVerifyView(APIView):
    """
    Verifies a 6-digit email OTP.
    - Validates exactly 6 numeric digits.
    - Atomic row-locking prevents race conditions and double consumption.
    - Marks user.is_email_verified = True.
    - Does NOT grant institutional approval; institution_status remains PENDING until administrator review.
    - Does NOT log user in automatically; directs user to the existing login page.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp') or request.data.get('otp_code') or request.data.get('otpCode')
        ip_address = get_client_ip(request)

        if not email:
            return Response({'detail': 'Email address is required.', 'code': 'EMAIL_REQUIRED'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not otp:
            return Response({'detail': 'Verification code is required.', 'code': 'OTP_REQUIRED'},
                            status=status.HTTP_400_BAD_REQUEST)

        from .email_otp_service import (
            EmailOTPService,
            EmailOTPError,
            EmailOTPAttemptsExceededError,
            EmailOTPAlreadyVerifiedError,
            EmailOTPInvalidError
        )

        try:
            user = EmailOTPService.verify_otp(email=email, otp_code=str(otp), ip_address=ip_address)
            return Response({
                'success': True,
                'verified': True,
                'message': 'Email address verified successfully. Please proceed to login.',
                'email': user.email,
                'is_email_verified': True,
                'institution_status': user.institution_status,
                'redirect_to': '/auth/login',
            }, status=status.HTTP_200_OK)
        except EmailOTPAlreadyVerifiedError as exc:
            return Response({
                'success': True,
                'already_verified': True,
                'account_already_verified': True,
                'detail': exc.message,
                'message': exc.message,
                'code': exc.code,
                'redirect_to': '/auth/login',
            }, status=status.HTTP_200_OK)
        except EmailOTPAttemptsExceededError as exc:
            return Response({
                'success': False,
                'detail': exc.message,
                'code': exc.code,
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except EmailOTPInvalidError as exc:
            return Response({
                'success': False,
                'detail': exc.message,
                'code': exc.code,
            }, status=exc.status_code)
        except EmailOTPError as exc:
            return Response({
                'success': False,
                'detail': exc.message,
                'code': exc.code,
            }, status=exc.status_code)


class EmailOTPResendView(APIView):
    """
    Resends a 6-digit email OTP for the provided email.
    - Enforces 60-second cooldown and 5/hour rate limits.
    - Preserves anti-enumeration defense.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'detail': 'Email address is required.', 'code': 'EMAIL_REQUIRED'},
                            status=status.HTTP_400_BAD_REQUEST)
        ip_address = get_client_ip(request)

        import hashlib
        from .email_otp_service import (
            EmailOTPService,
            EmailOTPCooldownError,
            EmailOTPRateLimitError,
            EmailOTPDeliveryError,
            EmailOTPError
        )

        try:
            norm_email = email.strip().lower()
            user = User.objects.filter(email__iexact=norm_email).first()
            if user and user.is_email_verified:
                return Response({
                    'success': True,
                    'already_verified': True,
                    'account_already_verified': True,
                    'email': EmailOTPService.mask_email(norm_email),
                    'message': 'This email address is already verified. Please sign in to your account.',
                    'detail': 'This email address is already verified. Please sign in to your account.',
                    'code': 'ALREADY_VERIFIED',
                    'redirect_to': '/auth/login',
                }, status=status.HTTP_200_OK)

            if user and not user.is_email_verified:
                challenge, masked = EmailOTPService.send_verification_otp(user, ip_address=ip_address)
                return Response({
                    'success': True,
                    'message': f'A new verification code has been sent to {masked}.',
                    'email': masked,
                    'cooldown_seconds': settings.EMAIL_OTP_RESEND_COOLDOWN_SECONDS,
                    'expires_in_minutes': settings.EMAIL_OTP_TTL_MINUTES,
                }, status=status.HTTP_200_OK)

            # User not found: do not generate OTP or send email
            return Response({
                'success': False,
                'registered': False,
                'already_verified': False,
                'email': norm_email,
                'code': 'EMAIL_NOT_REGISTERED',
                'message': 'This email address is not associated with a registered account. Please sign up first.',
                'detail': 'This email address is not associated with a registered account. Please sign up first.',
                'redirect_to': '/auth/signup',
            }, status=status.HTTP_404_NOT_FOUND)
        except EmailOTPCooldownError as exc:
            return Response({
                'detail': exc.message,
                'code': exc.code,
                'retry_after_seconds': exc.retry_after,
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except EmailOTPRateLimitError as exc:
            return Response({
                'detail': exc.message,
                'code': exc.code,
                'retry_after_seconds': exc.retry_after,
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except EmailOTPDeliveryError as exc:
            return Response({
                'detail': exc.message,
                'code': exc.code,
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except EmailOTPError as exc:
            return Response({
                'detail': exc.message,
                'code': exc.code,
            }, status=exc.status_code)


class EmailOTPRequestView(APIView):
    """
    Direct request for 6-digit email verification code outside signup flow.
    - Validates email address.
    - Avoids creating a new user account.
    - Anti-enumeration timing defense.
    - Handles already-verified accounts gracefully.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'detail': 'Email address is required.', 'code': 'EMAIL_REQUIRED'},
                            status=status.HTTP_400_BAD_REQUEST)
        ip_address = get_client_ip(request)

        from .email_otp_service import (
            EmailOTPService,
            EmailOTPCooldownError,
            EmailOTPRateLimitError,
            EmailOTPDeliveryError,
            EmailOTPError
        )

        try:
            res = EmailOTPService.request_otp_for_email(email=email, ip_address=ip_address)
            return Response(res, status=status.HTTP_200_OK)
        except EmailOTPCooldownError as exc:
            return Response({
                'detail': exc.message,
                'code': exc.code,
                'retry_after_seconds': exc.retry_after,
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except EmailOTPRateLimitError as exc:
            return Response({
                'detail': exc.message,
                'code': exc.code,
                'retry_after_seconds': exc.retry_after,
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except EmailOTPDeliveryError as exc:
            return Response({
                'detail': exc.message,
                'code': exc.code,
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except EmailOTPError as exc:
            return Response({
                'detail': exc.message,
                'code': exc.code,
            }, status=exc.status_code)

