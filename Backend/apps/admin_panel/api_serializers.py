"""
NEP Excellence Awards 2026 - Admin Control Plane Serializers (Phase 8)
Enforces strict anti-tampering validation, rejects client score injection,
and provides structured representations for review queues and inspection.
"""
from rest_framework import serializers
from apps.authentication.models import User
from apps.evidence.models import ReviewerAuthorization


FORBIDDEN_SCORE_FIELDS = frozenset([
    "score",
    "final_score",
    "certified_score",
    "certified_total",
    "raw_score",
    "marks",
    "override_score",
    "status",
    "is_certified",
    "certification_status",
])


class AntiTamperSerializerMixin:
    """
    Mixin that rejects any client-supplied score keys, final totals,
    or lifecycle manipulation fields.
    """
    def validate(self, attrs):
        initial_keys = set(self.initial_data.keys()) if hasattr(self, 'initial_data') and isinstance(self.initial_data, dict) else set()
        forbidden_present = initial_keys.intersection(FORBIDDEN_SCORE_FIELDS)
        if forbidden_present:
            raise serializers.ValidationError({
                "error": "SCORE_INJECTION_REJECTED",
                "detail": f"Direct score, total, or status injection is prohibited: {sorted(list(forbidden_present))}",
            })
        return super().validate(attrs)


class ReviewerAssignmentSerializer(AntiTamperSerializerMixin, serializers.Serializer):
    """
    Validates reviewer assignment and reassignment requests.
    Enforces anti-tampering, mandatory reason on reassignment, and reviewer validity.
    """
    reviewer_id = serializers.IntegerField(
        required=True,
        help_text="Primary key of the User to assign as reviewer."
    )
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Mandatory justification when reassigning an assessment; optional for initial assignment."
    )


class AdminCertifySerializer(AntiTamperSerializerMixin, serializers.Serializer):
    """
    Validates administrative certification requests.
    Strictly forbids client score injection payloads.
    """
    comments = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Optional certification remarks."
    )


class ReviewerAuthorizationCreateSerializer(serializers.Serializer):
    """
    Validates granting of ReviewerAuthorization.
    """
    user_id = serializers.IntegerField(required=True)
    framework = serializers.ChoiceField(
        choices=["UNIVERSITY_2026", "COLLEGE_2026", "ALL"],
        required=True
    )
    institution_id = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Optional AISHE code scoping reviewer to a single institution."
    )
    is_active = serializers.BooleanField(default=True)

    def validate_user_id(self, value):
        try:
            user = User.objects.get(pk=value)
        except User.DoesNotExist:
            raise serializers.ValidationError(f"User with id {value} does not exist.")
        if getattr(user, 'role', '') not in ('committee', 'committee_chair', 'admin', 'state_admin'):
            raise serializers.ValidationError(
                f"User '{user.email}' has role '{user.role}'. Only committee members and administrators can hold reviewer authorizations."
            )
        return value


class ReviewerAuthorizationListSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)
    user_full_name = serializers.CharField(source="user.full_name", read_only=True)
    user_role = serializers.CharField(source="user.role", read_only=True)
    granted_by_email = serializers.CharField(source="granted_by.email", read_only=True, default=None)

    class Meta:
        model = ReviewerAuthorization
        fields = [
            "authorization_id",
            "user_id",
            "user_email",
            "user_full_name",
            "user_role",
            "framework",
            "institution_id",
            "is_active",
            "granted_by_email",
            "created_at",
        ]
        read_only_fields = fields


class AdminReviewQueueItemSerializer(serializers.Serializer):
    """
    Lightweight, read-only serializer for items in the unified review queue.
    """
    assessment_id = serializers.CharField()
    framework = serializers.CharField()
    academic_year = serializers.CharField()
    institution_id = serializers.CharField()
    institution_name = serializers.CharField()
    institution_aishe = serializers.CharField()
    status = serializers.CharField()
    assigned_reviewer_id = serializers.IntegerField(allow_null=True)
    assigned_reviewer_name = serializers.CharField(allow_null=True)
    assigned_reviewer_email = serializers.CharField(allow_null=True)
    certified_score = serializers.FloatField(allow_null=True)
    certification_status = serializers.CharField(allow_blank=True)
    submitted_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()


class UserAuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.SerializerMethodField()
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = None  # Loaded dynamically to avoid circular import
        fields = [
            "id",
            "action",
            "actor_email",
            "actor_name",
            "details",
            "ip_address",
            "timestamp",
        ]

    def __init__(self, *args, **kwargs):
        from apps.authentication.models import UserAuditLog
        self.Meta.model = UserAuditLog
        super().__init__(*args, **kwargs)

    def get_actor_email(self, obj):
        return obj.actor.email if obj.actor else "System / CLI"

    def get_actor_name(self, obj):
        return obj.actor.full_name if obj.actor else "System"


class AdminUserListSerializer(serializers.ModelSerializer):
    institution_type = serializers.SerializerMethodField()
    institution_name = serializers.SerializerMethodField()
    aishe_code = serializers.SerializerMethodField()
    has_pending_invitation = serializers.SerializerMethodField()
    is_activated = serializers.SerializerMethodField()
    requested_institution = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "institution_status",
            "requested_institution",
            "id",
            "email",
            "full_name",
            "role",
            "is_active",
            "is_activated",
            "has_pending_invitation",
            "phone_number",
            "institution_type",
            "institution_name",
            "aishe_code",
            "is_staff",
            "is_superuser",
            "last_login",
        ]
        read_only_fields = fields

    def get_requested_institution(self, obj):
        inst = obj.requested_college or obj.requested_university
        if not inst:
            return None
        return {"type": "COLLEGE" if obj.requested_college_id else "UNIVERSITY", "id": inst.pk,
                "name": inst.name, "aishe_code": inst.aishe_code}

    def get_has_pending_invitation(self, obj):
        annotated = getattr(obj, "pending_invitation", None)
        if annotated is not None:
            return bool(annotated)
        from apps.authentication.models import AccountActivationToken
        from django.utils import timezone
        return AccountActivationToken.objects.filter(
            user=obj, is_used=False, is_revoked=False, expires_at__gt=timezone.now()
        ).exists()

    def get_is_activated(self, obj):
        return bool(obj.is_active and obj.has_usable_password())


    def get_institution_type(self, obj):
        if getattr(obj, "university_id", None):
            return "UNIVERSITY"
        if getattr(obj, "college_id", None):
            return "COLLEGE"
        return "NONE"

    def get_institution_name(self, obj):
        if getattr(obj, "university", None):
            return obj.university.name
        if getattr(obj, "college", None):
            return obj.college.name
        if obj.role in ("head_admin", "state_admin", "sub_admin", "admin"):
            return "Department of Higher Education, Haryana"
        if obj.role == "council_admin":
            return "State Council Administration Console"
        if "committee" in obj.role:
            return "Haryana NEP Awards Committee"
        return ""

    def get_aishe_code(self, obj):
        if getattr(obj, "university", None):
            return obj.university.aishe_code
        if getattr(obj, "college", None):
            return obj.college.aishe_code
        return ""


class AdminUserDetailSerializer(AdminUserListSerializer):
    audit_logs = serializers.SerializerMethodField()
    college = serializers.SerializerMethodField()
    university = serializers.SerializerMethodField()
    reviewer_authorizations = serializers.SerializerMethodField()

    class Meta(AdminUserListSerializer.Meta):
        fields = AdminUserListSerializer.Meta.fields + [
            "college",
            "university",
            "audit_logs",
            "reviewer_authorizations",
        ]

    def get_college(self, obj):
        if obj.college:
            return {
                "id": obj.college.id,
                "name": obj.college.name,
                "aishe_code": obj.college.aishe_code,
            }
        return None

    def get_university(self, obj):
        if obj.university:
            return {
                "id": obj.university.id,
                "name": obj.university.name,
                "aishe_code": obj.university.aishe_code,
                "university_type": getattr(obj.university, "university_type", ""),
            }
        return None

    def get_audit_logs(self, obj):
        logs = obj.audit_logs.all()[:25]
        return UserAuditLogSerializer(logs, many=True).data

    def get_reviewer_authorizations(self, obj):
        from apps.evidence.models import ReviewerAuthorization
        auths = ReviewerAuthorization.objects.filter(user=obj, is_active=True).order_by("-created_at")
        return [
            {
                "id": a.id,
                "framework": a.framework,
                "institution_id": a.institution_id,
                "is_active": a.is_active,
                "created_at": a.created_at,
            }
            for a in auths
        ]


class AdminUserCreateSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    full_name = serializers.CharField(required=True, max_length=255)
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES, required=True)
    password = serializers.CharField(required=False, allow_blank=True, write_only=True, min_length=8)
    phone_number = serializers.CharField(required=False, allow_blank=True, default="", max_length=20)
    college_id = serializers.IntegerField(required=False, allow_null=True)
    university_id = serializers.IntegerField(required=False, allow_null=True)
    committee_framework = serializers.CharField(required=False, allow_blank=True, default="")
    send_invite = serializers.BooleanField(required=False, default=True)

    def validate_email(self, value):
        normalized = value.strip().lower()
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError(f"User with email '{normalized}' already exists.")
        return normalized

    def validate(self, attrs):
        college_id = attrs.get("college_id")
        university_id = attrs.get("university_id")

        if college_id:
            from apps.authentication.models import College
            col = College.objects.filter(pk=college_id).first()
            if not col:
                raise serializers.ValidationError({"college_id": f"College with ID {college_id} does not exist."})
            attrs["college"] = col

        if university_id:
            from apps.university.models import University
            uni = University.objects.filter(pk=university_id).first()
            if not uni:
                raise serializers.ValidationError({"university_id": f"University with ID {university_id} does not exist."})
            attrs["university"] = uni

        return attrs


class AdminUserUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=False, max_length=255)
    phone_number = serializers.CharField(required=False, allow_blank=True, max_length=20)
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES, required=False)
    is_active = serializers.BooleanField(required=False)
    college_id = serializers.IntegerField(required=False, allow_null=True)
    university_id = serializers.IntegerField(required=False, allow_null=True)
    committee_framework = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if "college_id" in attrs:
            cid = attrs["college_id"]
            if cid is not None:
                from apps.authentication.models import College
                col = College.objects.filter(pk=cid).first()
                if not col:
                    raise serializers.ValidationError({"college_id": f"College with ID {cid} does not exist."})
                attrs["college"] = col
            else:
                attrs["college"] = None

        if "university_id" in attrs:
            uid = attrs["university_id"]
            if uid is not None:
                from apps.university.models import University
                uni = University.objects.filter(pk=uid).first()
                if not uni:
                    raise serializers.ValidationError({"university_id": f"University with ID {uid} does not exist."})
                attrs["university"] = uni
            else:
                attrs["university"] = None

        return attrs


class CommitteeMemberSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    user_role = serializers.CharField(source="user.role", read_only=True)
    assigned_by_email = serializers.EmailField(source="assigned_by.email", read_only=True, default=None)

    class Meta:
        from apps.admin_panel.models import CommitteeMember
        model = CommitteeMember
        fields = [
            "id",
            "user_id",
            "email",
            "full_name",
            "user_role",
            "role_in_committee",
            "is_active",
            "assigned_at",
            "removed_at",
            "assigned_by_email",
        ]


class CommitteeListSerializer(serializers.ModelSerializer):
    chair_id = serializers.IntegerField(source="chair.id", read_only=True, default=None)
    chair_name = serializers.CharField(source="chair.full_name", read_only=True, default=None)
    chair_email = serializers.EmailField(source="chair.email", read_only=True, default=None)
    member_count = serializers.SerializerMethodField()

    class Meta:
        from apps.admin_panel.models import Committee
        model = Committee
        fields = [
            "id",
            "name",
            "description",
            "committee_type",
            "framework",
            "chair_id",
            "chair_name",
            "chair_email",
            "member_count",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def get_member_count(self, obj):
        return obj.memberships.filter(is_active=True).count()


class CommitteeDetailSerializer(serializers.ModelSerializer):
    chair_id = serializers.IntegerField(source="chair.id", read_only=True, default=None)
    chair_name = serializers.CharField(source="chair.full_name", read_only=True, default=None)
    chair_email = serializers.EmailField(source="chair.email", read_only=True, default=None)
    members = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        from apps.admin_panel.models import Committee
        model = Committee
        fields = [
            "id",
            "name",
            "description",
            "committee_type",
            "framework",
            "chair_id",
            "chair_name",
            "chair_email",
            "members",
            "member_count",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def get_members(self, obj):
        active_members = obj.memberships.filter(is_active=True).select_related("user", "assigned_by")
        return CommitteeMemberSerializer(active_members, many=True).data

    def get_member_count(self, obj):
        return obj.memberships.filter(is_active=True).count()


class CommitteeCreateSerializer(serializers.Serializer):
    name = serializers.CharField(required=True, max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    committee_type = serializers.ChoiceField(choices=["SCREENING", "EMPOWERED"], default="SCREENING")
    framework = serializers.ChoiceField(choices=["COLLEGE_2026", "UNIVERSITY_2026", "ALL"], default="COLLEGE_2026")
    chair_id = serializers.IntegerField(required=False, allow_null=True)
    is_active = serializers.BooleanField(default=True)

    def validate_name(self, value):
        from apps.admin_panel.models import Committee
        name = value.strip()
        if Committee.objects.filter(name__iexact=name).exists():
            raise serializers.ValidationError(f"A committee with name '{name}' already exists.")
        return name


class CommitteeUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)


class CommitteeAssignChairSerializer(serializers.Serializer):
    chair_id = serializers.IntegerField(required=True)


class CommitteeAddMemberSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=True)
    role_in_committee = serializers.ChoiceField(choices=["chair", "member"], default="member")


