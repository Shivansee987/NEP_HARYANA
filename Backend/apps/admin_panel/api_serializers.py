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
