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


def resolve_university(aishe_code=None, institute_code=None, university_id=None, university_name=None):
    """
    Returns (university, error_message).
    Resolves university by ID, AISHE code (with DHE institute code disambiguation),
    or University Name (for universities without AISHE codes).
    """
    if university_id:
        uni = University.objects.filter(id=university_id, is_active=True).first()
        if uni:
            return uni, None
        return None, f"No active University found with ID '{university_id}'."

    aishe_code = normalize_aishe_code(aishe_code) if aishe_code else ""
    if aishe_code:
        qs = University.objects.filter(aishe_code__iexact=aishe_code, is_active=True)
        if institute_code:
            qs = qs.filter(institute_code=str(institute_code).strip())
        matches = list(qs[:2])
        if not matches:
            if university_name:
                uni = University.objects.filter(name__iexact=str(university_name).strip(), is_active=True).first()
                if not uni:
                    uni = University.objects.filter(name__icontains=str(university_name).strip(), is_active=True).first()
                if uni:
                    return uni, None
            return None, f"No active University found matching AISHE code '{aishe_code}'."
        if len(matches) > 1:
            return None, (f"Multiple universities share AISHE code '{aishe_code}'. "
                          f"Provide your DHE Institute Code (instituteCode) to identify your university.")
        return matches[0], None

    if university_name:
        name_str = str(university_name).strip()
        qs = University.objects.filter(name__iexact=name_str, is_active=True)
        if not qs.exists():
            qs = University.objects.filter(name__icontains=name_str, is_active=True)
        matches = list(qs[:2])
        if not matches:
            return None, f"No active University found matching name '{name_str}'."
        if len(matches) > 1:
            return None, f"Multiple universities match '{name_str}'. Please select the exact university name."
        return matches[0], None

    return None, "Either University AISHE Code or University Name is required."


def validate_phone_number(attrs):
    """
    Phone number is optional contact info. If provided, normalize and validate 10-digit format.
    Phone/SMS OTP verification is completely removed from the signup dependency chain.
    """
    phone = attrs.get('phoneNumber') or attrs.get('phone_number') or ''
    if not phone:
        attrs['phone_number'] = ''
        return attrs
    norm_phone = normalize_phone_number(phone)
    if norm_phone and (len(norm_phone) != 10 or not norm_phone.isdigit()):
        raise serializers.ValidationError({"phoneNumber": "Enter a valid 10-digit mobile number."})
    attrs['phone_number'] = norm_phone
    return attrs


# Backwards compatibility alias
validate_verified_phone = validate_phone_number


_NAME_FORBIDDEN_CHARS = re.compile(r'[<>"{}\[\]\\/=;`|@\x00-\x1f\x7f]')
_NAME_LINK = re.compile(r'://|www\.', re.IGNORECASE)


def validate_person_name(value):
    """
    A person's name appears in the portal's own e-mails. Markup characters, links and control characters are refused,
    so a name can never be used to plant content in an official message (S-02). Letters in any script are allowed.
    """
    value = (value or '').strip()
    if _NAME_FORBIDDEN_CHARS.search(value) or _NAME_LINK.search(value) or not any(ch.isalpha() for ch in value):
        raise serializers.ValidationError(
            "Enter a valid name: letters, spaces and the characters . ' - only, without links."
        )
    return value


def validate_new_password(attrs):
    try:
        validate_password(attrs.get('password'), User(email=attrs.get('email', ''), full_name=attrs.get('fullName', '')))
    except DjangoValidationError as exc:
        raise serializers.ValidationError({"password": list(exc.messages)})


def create_pending_applicant(validated_data, role, college=None, university=None):
    """
    Creates the applicant account in PENDING/UNVERIFIED state:
    1. Email verification is required before login is permitted.
    2. Once email is verified, institutional access remains PENDING until an administrator approves it.
    """
    from django.db import transaction
    from .models import UserAuditLog

    with transaction.atomic():
        user = User.objects.create_user(
            email=validated_data['email'],
            full_name=validated_data['fullName'].strip(),
            role=role,
            password=validated_data['password'],
            college=None,
            university=None,
            phone_number=validated_data.get('phone_number', ''),
            institution_status='PENDING',
            requested_college=college,
            requested_university=university,
            is_email_verified=False,
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
    is_email_verified = serializers.BooleanField(read_only=True)
    email_verified = serializers.BooleanField(source='is_email_verified', read_only=True)
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
            'is_email_verified', 'email_verified',
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
    fullName = serializers.CharField(required=True, min_length=2, max_length=255, validators=[validate_person_name])
    email = serializers.EmailField(required=True)
    phoneNumber = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    phoneVerificationToken = serializers.CharField(required=False, allow_blank=True, write_only=True)
    collegeId = serializers.IntegerField(required=False, allow_null=True)
    aisheCode = serializers.CharField(required=False, allow_blank=True, max_length=50)
    instituteCode = serializers.CharField(required=False, allow_blank=True, max_length=50)
    universityName = serializers.CharField(required=False, allow_blank=True, max_length=255)
    universityId = serializers.IntegerField(required=False, allow_null=True)
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
            uni_name = attrs.get('universityName')
            uni_id = attrs.get('universityId')
            if not aishe and not uni_name and not uni_id:
                raise serializers.ValidationError({"aisheCode": "AISHE code or University Name is required for University registration."})
            university, error = resolve_university(
                aishe_code=normalize_aishe_code(aishe) if aishe else "",
                institute_code=attrs.get('instituteCode'),
                university_id=uni_id,
                university_name=uni_name,
            )
            if error:
                error_field = 'universityName' if (uni_name and not aishe) else 'aisheCode'
                raise serializers.ValidationError({error_field: error})
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
    - The AISHE code or University Name must resolve to an active University.
    """
    fullName = serializers.CharField(required=True, min_length=2, max_length=255, validators=[validate_person_name])
    email = serializers.EmailField(required=True)
    phoneNumber = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    phoneVerificationToken = serializers.CharField(required=False, allow_blank=True, write_only=True)
    aisheCode = serializers.CharField(required=False, allow_blank=True, max_length=50)
    instituteCode = serializers.CharField(required=False, allow_blank=True, max_length=50)
    universityName = serializers.CharField(required=False, allow_blank=True, max_length=255)
    universityId = serializers.IntegerField(required=False, allow_null=True)
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
        if not value:
            return ""
        normalized = normalize_aishe_code(value)
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

        aishe = attrs.get('aisheCode')
        uni_name = attrs.get('universityName')
        uni_id = attrs.get('universityId')

        if not aishe and not uni_name and not uni_id:
            raise serializers.ValidationError({"aisheCode": "University AISHE code or University Name is required."})

        university, error = resolve_university(
            aishe_code=aishe,
            institute_code=attrs.get('instituteCode'),
            university_id=uni_id,
            university_name=uni_name,
        )
        if error:
            error_field = 'universityName' if (uni_name and not aishe) else 'aisheCode'
            raise serializers.ValidationError({error_field: f"{error} Institution must be verified before registration."})
        attrs['verified_university'] = university

        validate_new_password(attrs)
        validate_verified_phone(attrs)
        return attrs

    def create(self, validated_data):
        return create_pending_applicant(validated_data, 'nodal_officer', university=validated_data['verified_university'])


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)

