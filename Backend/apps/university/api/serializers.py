"""
NEP Excellence Awards 2026 - University API Serializers
Strictly protects authoritative scoring state, frameworks, and temporal parameters.
All scoring, verification, and lifecycle operations remain server-authoritative.
"""
from datetime import date
from typing import Any, Dict, List, Optional
from rest_framework import serializers

from apps.university.models import University, UniversityAssessment, UniversityReviewRecord
from apps.university.registry import (
    UNIVERSITY_FRAMEWORK_CODE,
    get_university_parameter,
    get_university_parameters,
)
from apps.university.validators import (
    UniversityValidationError,
    validate_count,
    validate_currency_amount,
    validate_framework_code,
    validate_institution_type,
    validate_parameter,
    validate_percentage,
    validate_subcriterion,
    validate_temporal_activity_date,
)


FORBIDDEN_SCORE_FIELDS = {
    "score",
    "earned_score",
    "earned_marks",
    "total",
    "certified_score",
    "certified_total",
    "reviewer_score",
    "marks",
}


class UniversitySerializer(serializers.ModelSerializer):
    """Serializes authoritative University institutions."""
    class Meta:
        model = University
        fields = [
            'id',
            'name',
            'aishe_code',
            'university_type',
            'state',
            'address',
            'contact_email',
            'contact_phone',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_aishe_code(self, value):
        if not value or not str(value).strip():
            raise serializers.ValidationError("AISHE code cannot be blank.")
        return str(value).strip()


class UniversityAssessmentSerializer(serializers.ModelSerializer):
    """
    Serializes UniversityAssessment records.
    Authoritative scores, frameworks, statutory periods, and lifecycle states are strictly read-only.
    """
    university_id = serializers.IntegerField(source='university.id', read_only=True)
    university_name = serializers.CharField(source='university.name', read_only=True)
    aishe_code = serializers.CharField(source='university.aishe_code', read_only=True)

    class Meta:
        model = UniversityAssessment
        fields = [
            'id',
            'assessment_id',
            'university_id',
            'university_name',
            'aishe_code',
            'framework',
            'academic_year',
            'period_start',
            'period_end',
            'status',
            'assigned_reviewer',
            'submitted_at',
            'parameter_data',
            'certified_score',
            'certification_status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'assessment_id',
            'university_id',
            'university_name',
            'aishe_code',
            'framework',
            'academic_year',
            'period_start',
            'period_end',
            'status',
            'assigned_reviewer',
            'submitted_at',
            'certified_score',
            'certification_status',
            'created_at',
            'updated_at',
        ]

    def validate(self, attrs):
        # Prevent client from injecting forbidden score fields
        initial_data = getattr(self, 'initial_data', {})
        for field in FORBIDDEN_SCORE_FIELDS:
            if field in initial_data:
                raise serializers.ValidationError({
                    field: f"Client cannot supply or modify score field '{field}'. Score is server-authoritative."
                })
        return attrs


class UniversityAssessmentCreateSerializer(serializers.Serializer):
    """
    Validates payload for creating a University assessment session.
    Automatically enforces framework UNIVERSITY_2026 and assessment period (2025-07-01 to 2026-06-30).
    """
    academic_year = serializers.CharField(max_length=20, required=False, default="2025-26")
    assessment_id = serializers.CharField(max_length=100, required=False, allow_blank=True, default=None)
    framework = serializers.CharField(required=False, default=UNIVERSITY_FRAMEWORK_CODE)
    period_start = serializers.DateField(required=False, default=date(2025, 7, 1))
    period_end = serializers.DateField(required=False, default=date(2026, 6, 30))

    def validate_framework(self, value):
        if value and value.strip().upper() not in (UNIVERSITY_FRAMEWORK_CODE, "UNIVERSITY"):
            raise serializers.ValidationError(
                f"Invalid framework '{value}'. Client cannot override framework; expected '{UNIVERSITY_FRAMEWORK_CODE}'.",
                code="INVALID_FRAMEWORK"
            )
        return UNIVERSITY_FRAMEWORK_CODE

    def validate_period_start(self, value):
        expected = date(2025, 7, 1)
        if value and value != expected:
            raise serializers.ValidationError(
                f"Invalid assessment period start '{value}'. Statutory period starts {expected}.",
                code="INVALID_ASSESSMENT_PERIOD"
            )
        return expected

    def validate_period_end(self, value):
        expected = date(2026, 6, 30)
        if value and value != expected:
            raise serializers.ValidationError(
                f"Invalid assessment period end '{value}'. Statutory period ends {expected}.",
                code="INVALID_ASSESSMENT_PERIOD"
            )
        return expected

    def validate(self, attrs):
        initial_data = getattr(self, 'initial_data', {})
        for field in FORBIDDEN_SCORE_FIELDS:
            if field in initial_data:
                raise serializers.ValidationError({
                    field: f"Client cannot supply score field '{field}' during assessment creation."
                })
        return attrs


class UniversityParameterInputSerializer(serializers.Serializer):
    """
    Validates parameter inputs for a specific University parameter (U1–U20).
    Rejects any client attempts to set scores, marks, or certification states.
    Validates semantic content using Phase 6A validators.
    """
    raw_inputs = serializers.DictField(required=True)
    entities = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    activity_date = serializers.DateField(required=False, allow_null=True, default=None)

    def validate(self, attrs):
        initial_data = getattr(self, 'initial_data', {})
        for field in FORBIDDEN_SCORE_FIELDS:
            if field in initial_data:
                raise serializers.ValidationError({
                    field: f"Client cannot supply score field '{field}'. Parameter scoring is strictly delegated."
                })
        return attrs

    def validate_with_parameter(self, parameter_code: str):
        """
        Executes domain validation against the authoritative parameter specification.
        Checks percentages, counts, amounts, subcriteria membership, and temporal dates.
        """
        param_clean = validate_parameter(parameter_code)
        param_def = get_university_parameter(param_clean)
        subcriteria_defs = param_def.get("subcriteria", {})
        raw_inputs = self.validated_data.get("raw_inputs", {})
        activity_date = self.validated_data.get("activity_date")

        # Temporal check for date-sensitive parameters
        if activity_date:
            validate_temporal_activity_date(activity_date, param_clean)

        # Inspect raw inputs for semantic constraints
        for key, val in raw_inputs.items():
            # Check if key is a subcriterion format (e.g. U1.1, U1.99, or in subcriteria_defs)
            if "." in key or key.upper().startswith("U") or key in subcriteria_defs:
                validate_subcriterion(param_clean, key)
                # If subcriterion value is a dict, validate its internal keys
                if isinstance(val, dict):
                    for sub_k, sub_v in val.items():
                        self._validate_primitive_field(sub_k, sub_v, param_clean)
            else:
                self._validate_primitive_field(key, val, param_clean)

        return self.validated_data

    def _validate_primitive_field(self, field_name: str, value: Any, param_code: str):
        low_name = field_name.lower()
        if "percent" in low_name or "rate" in low_name:
            validate_percentage(value, field_name=field_name)
        elif "count" in low_name or "programmes" in low_name or "patents" in low_name or "activities" in low_name:
            validate_count(value, field_name=field_name)
        elif "amount" in low_name or "funding" in low_name or "rupees" in low_name:
            validate_currency_amount(value, field_name=field_name)


class UniversityParameterMetadataSerializer(serializers.Serializer):
    """Serializes authoritative parameter metadata merged with submitted input state."""
    code = serializers.CharField()
    title = serializers.CharField()
    max_marks = serializers.FloatField()
    subcriteria = serializers.DictField()
    period_rule = serializers.CharField()
    mandatory_evidence = serializers.ListField(child=serializers.CharField())
    allowed_evidence = serializers.ListField(child=serializers.CharField())
    double_counting_rule = serializers.CharField()
    submitted_input = serializers.DictField(allow_null=True)


class UniversityAssessmentEvaluateSerializer(serializers.Serializer):
    """Validates scoring evaluation request parameters."""
    reviewer_adjustments = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list
    )


class UniversityReviewStartSerializer(serializers.Serializer):
    """Payload for starting review on an assessment."""
    comments = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        for field in FORBIDDEN_SCORE_FIELDS:
            if field in self.initial_data:
                raise serializers.ValidationError(
                    {"error": f"Field '{field}' cannot be supplied by the client.", "code": "CLIENT_SCORE_FORBIDDEN"}
                )
        return attrs


class UniversityReviewCompleteSerializer(serializers.Serializer):
    """Payload for completing review on an assessment."""
    comments = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        for field in FORBIDDEN_SCORE_FIELDS:
            if field in self.initial_data:
                raise serializers.ValidationError(
                    {"error": f"Field '{field}' cannot be supplied by the client.", "code": "CLIENT_SCORE_FORBIDDEN"}
                )
        return attrs


class UniversityReviewCorrectionSerializer(serializers.Serializer):
    """Payload for returning an assessment for correction."""
    reason = serializers.CharField(required=True, allow_blank=False, min_length=5)
    comments = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        for field in FORBIDDEN_SCORE_FIELDS:
            if field in self.initial_data:
                raise serializers.ValidationError(
                    {"error": f"Field '{field}' cannot be supplied by the client.", "code": "CLIENT_SCORE_FORBIDDEN"}
                )
        if not attrs.get("reason") or not attrs["reason"].strip():
            raise serializers.ValidationError({"reason": "A meaningful reason is mandatory."})
        return attrs


class UniversityReviewBlockSerializer(serializers.Serializer):
    """Payload for blocking an assessment review."""
    reason = serializers.CharField(required=True, allow_blank=False, min_length=5)
    comments = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        for field in FORBIDDEN_SCORE_FIELDS:
            if field in self.initial_data:
                raise serializers.ValidationError(
                    {"error": f"Field '{field}' cannot be supplied by the client.", "code": "CLIENT_SCORE_FORBIDDEN"}
                )
        if not attrs.get("reason") or not attrs["reason"].strip():
            raise serializers.ValidationError({"reason": "A meaningful reason is mandatory."})
        return attrs


class UniversityCertifySerializer(serializers.Serializer):
    """Payload for certifying an assessment."""
    remarks = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        for field in FORBIDDEN_SCORE_FIELDS:
            if field in self.initial_data:
                raise serializers.ValidationError(
                    {"error": f"Field '{field}' cannot be supplied by the client.", "code": "CLIENT_SCORE_FORBIDDEN"}
                )
        return attrs


class UniversityReviewRecordSerializer(serializers.ModelSerializer):
    """Serializes append-only review history."""
    reviewer_name = serializers.CharField(source="reviewer.full_name", read_only=True)
    reviewer_email = serializers.CharField(source="reviewer.email", read_only=True)

    class Meta:
        model = UniversityReviewRecord
        fields = [
            "review_id",
            "action",
            "status_before",
            "status_after",
            "reviewer_name",
            "reviewer_email",
            "reason",
            "comments",
            "scoring_snapshot",
            "evidence_readiness_snapshot",
            "created_at",
        ]
        read_only_fields = fields


class UniversityReviewQueueItemSerializer(serializers.ModelSerializer):
    """Serializes assessment records in the committee review queue."""
    university_name = serializers.CharField(source="university.name", read_only=True)
    aishe_code = serializers.CharField(source="university.aishe_code", read_only=True)
    assigned_reviewer_email = serializers.CharField(source="assigned_reviewer.email", read_only=True, default=None)
    assigned_reviewer_name = serializers.CharField(source="assigned_reviewer.full_name", read_only=True, default=None)

    class Meta:
        model = UniversityAssessment
        fields = [
            "assessment_id",
            "university_id",
            "university_name",
            "aishe_code",
            "framework",
            "academic_year",
            "status",
            "submitted_at",
            "assigned_reviewer_email",
            "assigned_reviewer_name",
            "certified_score",
            "certification_status",
            "created_at",
        ]
        read_only_fields = fields

