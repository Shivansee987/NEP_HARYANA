import datetime
import re
from django.core.cache import cache
from django.utils import timezone
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from .models import User, College
from apps.university.models import University


def normalize_aishe_code(code: str) -> str:
    """Normalize AISHE code consistently across lookup and registration."""
    if not code:
        return ""
    code = str(code).strip()
    # Normalize unicode hyphens/dashes to standard ASCII hyphen
    for dash in ["\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2015", "\u2212"]:
        code = code.replace(dash, "-")
    return code.upper()


def normalize_phone_number(phone: str) -> str:
    """Normalize phone number to standard 10-digit format."""
    if not phone:
        return ""
    cleaned = re.sub(r'[^0-9+]', '', str(phone).strip())
    if cleaned.startswith("+91"):
        cleaned = cleaned[3:]
    elif cleaned.startswith("91") and len(cleaned) == 12:
        cleaned = cleaned[2:]
    elif cleaned.startswith("0") and len(cleaned) == 11:
        cleaned = cleaned[1:]
    return cleaned


def is_phone_verified(phone: str) -> bool:
    """Authoritative check for whether phone number was verified via OTP."""
    norm = normalize_phone_number(phone)
    if not norm:
        return False
    if cache.get(f"phone_verified_{norm}"):
        return True
    from .models import OTPVerification
    return OTPVerification.objects.filter(
        phone_number=norm,
        is_verified=True,
        created_at__gte=timezone.now() - datetime.timedelta(hours=2)
    ).exists()


class CollegeSerializer(serializers.ModelSerializer):
    class Meta:
        model = College
        fields = ['id', 'name', 'aishe_code']


class UniversityPublicSerializer(serializers.ModelSerializer):
    """Safe public university representation for lookup and registration."""
    class Meta:
        model = University
        fields = ['id', 'name', 'aishe_code', 'university_type', 'state', 'address', 'contact_email', 'contact_phone']


class UserSerializer(serializers.ModelSerializer):
    fullName = serializers.CharField(source='full_name', read_only=True)
    phoneNumber = serializers.CharField(source='phone_number', read_only=True)
    collegeId = serializers.SerializerMethodField()
    college_id = serializers.SerializerMethodField()
    college_name = serializers.SerializerMethodField()
    universityId = serializers.SerializerMethodField()
    university_id = serializers.SerializerMethodField()
    university_name = serializers.SerializerMethodField()
    institution_type = serializers.SerializerMethodField()
    institution_name = serializers.SerializerMethodField()
    aishe_code = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'full_name', 'fullName', 'role',
            'phone_number', 'phoneNumber',
            'collegeId', 'college_id', 'college_name',
            'universityId', 'university_id', 'university_name',
            'institution_type', 'institution_name',
            'aishe_code'
        ]

    def get_collegeId(self, obj):
        return obj.college.id if obj.college else None

    def get_college_id(self, obj):
        return obj.college.id if obj.college else None

    def get_college_name(self, obj):
        if obj.college:
            return obj.college.name
        if obj.university:
            return obj.university.name
        if obj.role == 'admin':
            return "Higher Education Department"
        if obj.role == 'committee':
            return "Screening Committee"
        return "Govt College Example"

    def get_universityId(self, obj):
        return obj.university.id if obj.university else None

    def get_university_id(self, obj):
        return obj.university.id if obj.university else None

    def get_university_name(self, obj):
        return obj.university.name if obj.university else None

    def get_institution_type(self, obj):
        if obj.university:
            return "UNIVERSITY"
        if obj.college:
            return "COLLEGE"
        return None

    def get_institution_name(self, obj):
        if obj.university:
            return obj.university.name
        if obj.college:
            return obj.college.name
        if obj.role == 'admin':
            return "Higher Education Department"
        if obj.role == 'committee':
            return "Screening Committee"
        return ""

    def get_aishe_code(self, obj):
        if obj.college:
            return obj.college.aishe_code
        if obj.university:
            return obj.university.aishe_code
        if obj.role == 'admin':
            return "DHE-HR"
        if obj.role == 'committee':
            return "SC-HR"
        return ""


class RegisterSerializer(serializers.Serializer):
    """
    General registration serializer for colleges.
    Protects against privilege escalation (disallows requesting admin or reviewer roles).
    """
    fullName = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    phoneNumber = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    collegeId = serializers.IntegerField(required=False, allow_null=True)
    aisheCode = serializers.CharField(required=False, allow_blank=True)
    institutionType = serializers.CharField(required=False, default="COLLEGE")
    role = serializers.CharField(required=False, default="principal")
    password = serializers.CharField(write_only=True, required=True)

    def validate_email(self, value):
        normalized = value.strip().lower()
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return normalized

    def validate_role(self, value):
        # Disallow privilege escalation: public signup cannot request privileged roles
        if value in ['admin', 'committee', 'committee_chair', 'university_admin']:
            raise serializers.ValidationError("Privileged roles cannot be requested during public registration.")
        if value not in ['principal', 'nodal_officer']:
            raise serializers.ValidationError(f"Invalid registration role '{value}'.")
        return value

    def validate_collegeId(self, value):
        if value is not None:
            if not College.objects.filter(id=value).exists():
                raise serializers.ValidationError("Selected institution does not exist.")
        return value

    def validate(self, attrs):
        role = attrs.get('role', 'principal')
        college_id = attrs.get('collegeId')
        institution_type = attrs.get('institutionType', 'COLLEGE').upper()

        phone = attrs.get('phoneNumber') or attrs.get('phone_number')
        if phone and phone.strip():
            norm_phone = normalize_phone_number(phone)
            if len(norm_phone) != 10 or not norm_phone.isdigit():
                raise serializers.ValidationError({"phoneNumber": "Enter a valid 10-digit mobile number."})
            if not is_phone_verified(norm_phone):
                raise serializers.ValidationError({"phoneNumber": "Mobile number is not verified. Please verify using OTP."})
            attrs['phone_number'] = norm_phone

        if institution_type == 'UNIVERSITY' or role == 'nodal_officer':
            aishe = attrs.get('aisheCode')
            if not aishe:
                raise serializers.ValidationError({"aisheCode": "AISHE code is required for University registration."})
            normalized_aishe = normalize_aishe_code(aishe)
            uni = University.objects.filter(aishe_code__iexact=normalized_aishe, is_active=True).first()
            if not uni:
                raise serializers.ValidationError({"aisheCode": f"No active University found matching AISHE code '{normalized_aishe}'."})
            attrs['verified_university'] = uni
            attrs['role'] = 'nodal_officer'
        else:
            if role == 'principal' and college_id is None:
                raise serializers.ValidationError({"collegeId": "Institution is required for College Principal role."})
        return attrs

    def create(self, validated_data):
        role = validated_data.get('role', 'principal')
        university = validated_data.get('verified_university')

        college = None
        if not university:
            college_id = validated_data.get('collegeId')
            if role == 'principal' and college_id is not None:
                college = College.objects.get(id=college_id)
            elif college_id is not None:
                college = College.objects.filter(id=college_id).first()

        user = User.objects.create_user(
            email=validated_data['email'],
            full_name=validated_data['fullName'].strip(),
            role=role,
            password=validated_data['password'],
            college=college,
            university=university,
            phone_number=validated_data.get('phone_number', '')
        )
        return user


class UniversityRegisterSerializer(serializers.Serializer):
    """
    Dedicated University Applicant Registration Serializer.
    Guarantees:
    - Fixed institution type: UNIVERSITY.
    - Fixed role: nodal_officer (University Nodal Officer).
    - Uniqueness of email.
    - Normalization and authoritative lookup of AISHE code against University model.
    - Rejection of client-supplied institution IDs, privileged roles, or unverified codes.
    - Existing canonical University record reuse without duplicate creation or field tampering.
    """
    fullName = serializers.CharField(required=True, min_length=2, max_length=255)
    email = serializers.EmailField(required=True)
    phoneNumber = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    aisheCode = serializers.CharField(required=True, max_length=50)
    designation = serializers.CharField(required=False, default="University Nodal Officer", max_length=150)
    institutionType = serializers.CharField(required=False, default="UNIVERSITY")
    role = serializers.CharField(required=False, default="nodal_officer")
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    confirmPassword = serializers.CharField(write_only=True, required=False, allow_blank=True)

    def validate_email(self, value):
        normalized = value.strip().lower()
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError("A user with this email address already exists.")
        return normalized

    def validate_role(self, value):
        # Strict security: reject any privileged or mismatched role
        if value and value != 'nodal_officer':
            raise serializers.ValidationError("Privileged roles cannot be requested during registration.")
        return 'nodal_officer'

    def validate_institutionType(self, value):
        if value and value.strip().upper() != 'UNIVERSITY':
            raise serializers.ValidationError("Institution type must be UNIVERSITY for this registration flow.")
        return 'UNIVERSITY'

    def validate_aisheCode(self, value):
        normalized = normalize_aishe_code(value)
        if not normalized:
            raise serializers.ValidationError("AISHE code is required.")
        # Reject obvious non-university format like college code C-
        if normalized.startswith("C-"):
            raise serializers.ValidationError(
                "The provided code appears to be a College AISHE code. Please use the College registration portal."
            )
        # Check basic valid format: alphanumeric with hyphens
        if not re.match(r'^[A-Z0-9_\-]+$', normalized):
            raise serializers.ValidationError("Invalid AISHE code format. Code must contain only letters, numbers, and hyphens.")
        return normalized

    def validate(self, attrs):
        password = attrs.get('password')
        confirm_password = attrs.get('confirmPassword')
        if confirm_password and password != confirm_password:
            raise serializers.ValidationError({"confirmPassword": "Passwords do not match."})

        # Apply Django's built-in password validation policy
        try:
            validate_password(password)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})

        phone = attrs.get('phoneNumber') or attrs.get('phone_number')
        if phone and phone.strip():
            norm_phone = normalize_phone_number(phone)
            if len(norm_phone) != 10 or not norm_phone.isdigit():
                raise serializers.ValidationError({"phoneNumber": "Enter a valid 10-digit mobile number."})
            if not is_phone_verified(norm_phone):
                raise serializers.ValidationError({"phoneNumber": "Mobile number is not verified. Please verify using OTP."})
            attrs['phone_number'] = norm_phone

        # Authoritative institution lookup
        aishe_code = attrs.get('aisheCode')
        university = University.objects.filter(aishe_code__iexact=aishe_code, is_active=True).first()
        if not university:
            raise serializers.ValidationError({
                "aisheCode": f"No active University found matching AISHE code '{aishe_code}'. Institution must be verified before registration."
            })

        attrs['verified_university'] = university
        return attrs

    def create(self, validated_data):
        university = validated_data['verified_university']
        email = validated_data['email']
        full_name = validated_data['fullName'].strip()
        password = validated_data['password']

        # Enforce approved University applicant role via trusted backend logic
        user = User.objects.create_user(
            email=email,
            full_name=full_name,
            role='nodal_officer',
            password=password,
            university=university,
            college=None,
            phone_number=validated_data.get('phone_number', '')
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)

