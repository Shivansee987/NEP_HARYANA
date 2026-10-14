import datetime
import re
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


def resolve_university(aishe_code, institute_code=None):
    """
    Returns (university, error_message). A shared AISHE code must be disambiguated with the DHE institute
    code, mirroring the public lookup endpoint (which answers 409 for ambiguous codes).
    """
    qs = University.objects.filter(aishe_code__iexact=aishe_code, is_active=True)
    if institute_code:
        qs = qs.filter(institute_code=str(institute_code).strip())
    matches = list(qs[:2])
    if not matches:
        return None, f"No active University found matching AISHE code '{aishe_code}'."
    if len(matches) > 1:
        return None, (f"Multiple universities share AISHE code '{aishe_code}'. "
                      f"Provide your DHE Institute Code (instituteCode) to identify your university.")
    return matches[0], None


def validate_verified_phone(attrs):
    """New registrations must present a phone number verified through the OTP backend."""
    from .otp_service import phone_verification_is_valid
    phone = attrs.get('phoneNumber') or attrs.get('phone_number') or ''
    norm_phone = normalize_phone_number(phone)
    if len(norm_phone) != 10 or not norm_phone.isdigit():
        raise serializers.ValidationError({"phoneNumber": "Enter a valid 10-digit mobile number."})
    if not phone_verification_is_valid(norm_phone, attrs.get('phoneVerificationToken') or ''):
        raise serializers.ValidationError({"phoneNumber": "Mobile number is not verified. Please verify it using the OTP sent to it."})
    attrs['phone_number'] = norm_phone
    return attrs


def validate_new_password(attrs):
    try:
        validate_password(attrs.get('password'), User(email=attrs.get('email', ''), full_name=attrs.get('fullName', '')))
    except DjangoValidationError as exc:
        raise serializers.ValidationError({"password": list(exc.messages)})


def create_pending_applicant(validated_data, role, college=None, university=None):
    """
    Creates the applicant account in PENDING state: the institution is only *requested*. Assessment access
    (which checks user.college / user.university) is granted when an administrator approves the request.
    """
    from django.db import transaction
    from .models import UserAuditLog
    from .otp_service import consume_phone_verification

    with transaction.atomic():
        if not consume_phone_verification(validated_data['phone_number'], validated_data.get('phoneVerificationToken')):
            raise serializers.ValidationError({"phoneNumber": "Mobile verification has expired or was already used. Please verify again."})
        user = User.objects.create_user(
            email=validated_data['email'],
            full_name=validated_data['fullName'].strip(),
            role=role,
            password=validated_data['password'],
            college=None,
            university=None,
            phone_number=validated_data['phone_number'],
            institution_status='PENDING',
            requested_college=college,
            requested_university=university,
        )
        institution = college or university
        UserAuditLog.objects.create(
            actor=user, target_user=user, action='INSTITUTION_ACCESS_REQUESTED',
            details={'institution_type': 'COLLEGE' if college else 'UNIVERSITY',
                     'institution_id': institution.pk, 'institution_name': institution.name},
        )
    return user


class CollegeSerializer(serializers.ModelSerializer):
    class Meta:
        model = College
        fields = ['id', 'name', 'aishe_code']


class CollegeDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = College
        fields = [
            'id', 'name', 'institute_code', 'aishe_code', 'department',
            'district', 'institute_type', 'institute_category',
            'affiliation_body_1', 'affiliation_body_2', 'is_verified'
        ]


class UniversityPublicSerializer(serializers.ModelSerializer):
    """Safe public university representation for lookup and registration."""
    class Meta:
        model = University
        fields = [
            'id', 'name', 'institute_code', 'aishe_code', 'university_type',
            'district', 'state', 'address', 'contact_email', 'contact_phone'
        ]


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
            'aishe_code', 'institution_status', 'requested_institution_name'
        ]

    requested_institution_name = serializers.SerializerMethodField()

    def get_requested_institution_name(self, obj):
        inst = obj.requested_college or obj.requested_university
        return inst.name if inst else None

    def get_collegeId(self, obj):
        return obj.college.id if obj.college else None

    def get_college_id(self, obj):
        return obj.college.id if obj.college else None

    def get_college_name(self, obj):
        if obj.college:
            return obj.college.name
        if obj.university:
            return obj.university.name
        if obj.role in ('head_admin', 'sub_admin', 'admin'):
            return "Higher Education Department"
        if 'committee' in obj.role:
            return "Screening Committee"
        return ""

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
        if obj.role in ('head_admin', 'sub_admin', 'admin'):
            return "Higher Education Department"
        if 'committee' in obj.role:
            return "Screening Committee"
        return ""

    def get_aishe_code(self, obj):
        if obj.college:
            return obj.college.aishe_code
        if obj.university:
            return obj.university.aishe_code
        if obj.role in ('head_admin', 'sub_admin', 'admin'):
            return "DHE-HR"
        if 'committee' in obj.role:
            return "SC-HR"
        return ""



class RegisterSerializer(serializers.Serializer):
    """
    Public applicant registration (College principal, or University nodal officer via institutionType).
    Privileged roles are refused. The account is created PENDING: the institution is requested, not granted,
    until an administrator approves it.
    """
    fullName = serializers.CharField(required=True, min_length=2, max_length=255)
    email = serializers.EmailField(required=True)
    phoneNumber = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    phoneVerificationToken = serializers.CharField(required=False, allow_blank=True, write_only=True)
    collegeId = serializers.IntegerField(required=False, allow_null=True)
    aisheCode = serializers.CharField(required=False, allow_blank=True, max_length=50)
    instituteCode = serializers.CharField(required=False, allow_blank=True, max_length=50)
    institutionType = serializers.CharField(required=False, default="COLLEGE")
    role = serializers.CharField(required=False, default="principal")
    password = serializers.CharField(write_only=True, required=True)

    def validate_email(self, value):
        normalized = value.strip().lower()
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return normalized

    def validate_role(self, value):
        if value not in ('principal', 'nodal_officer'):
            raise serializers.ValidationError("Privileged roles cannot be requested during public registration.")
        return value

    def validate_collegeId(self, value):
        if value is not None and not College.objects.filter(id=value).exists():
            raise serializers.ValidationError("Selected institution does not exist.")
        return value

    def validate(self, attrs):
        role = attrs.get('role', 'principal')
        institution_type = (attrs.get('institutionType') or 'COLLEGE').upper()

        if institution_type == 'UNIVERSITY' or role == 'nodal_officer':
            aishe = attrs.get('aisheCode')
            if not aishe:
                raise serializers.ValidationError({"aisheCode": "AISHE code is required for University registration."})
            university, error = resolve_university(normalize_aishe_code(aishe), attrs.get('instituteCode'))
            if error:
                raise serializers.ValidationError({"aisheCode": error})
            attrs['verified_university'] = university
            attrs['role'] = 'nodal_officer'
        else:
            if attrs.get('collegeId') is None:
                raise serializers.ValidationError({"collegeId": "Institution is required for College Principal role."})
            attrs['role'] = 'principal'

        validate_new_password(attrs)
        validate_verified_phone(attrs)
        return attrs

    def create(self, validated_data):
        university = validated_data.get('verified_university')
        if university:
            return create_pending_applicant(validated_data, 'nodal_officer', university=university)
        college = College.objects.get(id=validated_data['collegeId'])
        return create_pending_applicant(validated_data, 'principal', college=college)


class UniversityRegisterSerializer(serializers.Serializer):
    """
    Dedicated University Applicant Registration.
    - Fixed institution type UNIVERSITY and role nodal_officer; privileged roles are refused.
    - Verified mobile number and password policy are required.
    - The AISHE code (plus DHE institute code when the AISHE code is shared) must resolve to exactly one
      active University. The account is created PENDING until an administrator approves the request.
    """
    fullName = serializers.CharField(required=True, min_length=2, max_length=255)
    email = serializers.EmailField(required=True)
    phoneNumber = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    phoneVerificationToken = serializers.CharField(required=False, allow_blank=True, write_only=True)
    aisheCode = serializers.CharField(required=True, max_length=50)
    instituteCode = serializers.CharField(required=False, allow_blank=True, max_length=50)
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
        if normalized.startswith("C-"):
            raise serializers.ValidationError(
                "The provided code appears to be a College AISHE code. Please use the College registration portal."
            )
        if not re.match(r'^[A-Z0-9_\-]+$', normalized):
            raise serializers.ValidationError("Invalid AISHE code format. Code must contain only letters, numbers, and hyphens.")
        return normalized

    def validate(self, attrs):
        confirm_password = attrs.get('confirmPassword')
        if confirm_password and attrs.get('password') != confirm_password:
            raise serializers.ValidationError({"confirmPassword": "Passwords do not match."})
        university, error = resolve_university(attrs.get('aisheCode'), attrs.get('instituteCode'))
        if error:
            raise serializers.ValidationError({"aisheCode": f"{error} Institution must be verified before registration."})
        attrs['verified_university'] = university

        validate_new_password(attrs)
        validate_verified_phone(attrs)
        return attrs

    def create(self, validated_data):
        return create_pending_applicant(validated_data, 'nodal_officer', university=validated_data['verified_university'])


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)

