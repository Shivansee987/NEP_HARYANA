"""
NEP Excellence Awards 2026 - College API Serializers (Phase 7B)
Strictly protects authoritative scoring state, frameworks, and temporal parameters.
All scoring, verification, and lifecycle operations remain server-authoritative.
"""
from datetime import date
from typing import Any, Dict, List, Optional
from rest_framework import serializers

from apps.authentication.models import College
from apps.college.models import CollegeAssessment, CollegeReviewRecord
from apps.college.registry import (
    COLLEGE_FRAMEWORK_CODE,
    get_college_parameter,
    get_college_parameters,
)
from apps.college.validators import (
    CollegeValidationError,
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


class CollegeReadSerializer(serializers.ModelSerializer):
    """Serializes authoritative College institutions."""
    class Meta:
        model = College
        fields = [
            'id',
            'name',
            'aishe_code',
        ]
        read_only_fields = ['id', 'name', 'aishe_code']

    def validate_aishe_code(self, value):
        if not value or not str(value).strip():
            raise serializers.ValidationError("AISHE code cannot be blank.")
        return str(value).strip()


class CollegeAssessmentSerializer(serializers.ModelSerializer):
    """
    Serializes CollegeAssessment records.
    Authoritative scores, frameworks, statutory periods, and lifecycle states are strictly read-only.
    """
    college_id = serializers.IntegerField(source='college.id', read_only=True)
    college_name = serializers.CharField(source='college.name', read_only=True)
    aishe_code = serializers.CharField(source='college.aishe_code', read_only=True)
    assigned_reviewer = serializers.PrimaryKeyRelatedField(read_only=True)
    evidence_associations = serializers.SerializerMethodField()

    class Meta:
        model = CollegeAssessment
        fields = [
            'id',
            'assessment_id',
            'college_id',
            'college_name',
            'aishe_code',
            'framework',
            'academic_year',
            'period_start',
            'period_end',
            'status',
            'submitted_at',
            'parameter_data',
            'evidence_associations',
            'assigned_reviewer',
            'certified_score',
            'certification_status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'assessment_id',
            'college_id',
            'college_name',
            'aishe_code',
            'framework',
            'academic_year',
            'period_start',
            'period_end',
            'status',
            'submitted_at',
            'evidence_associations',
            'assigned_reviewer',
            'certified_score',
            'certification_status',
            'created_at',
            'updated_at',
        ]

    def get_evidence_associations(self, obj):
        from apps.evidence.models import EvidenceSubcriterionAssociation
        from apps.evidence.api.serializers import EvidenceAssociationSerializer
        assocs = EvidenceSubcriterionAssociation.objects.filter(
            evidence__assessment_id=obj.assessment_id,
            is_active=True,
        ).select_related('evidence', 'associated_by').prefetch_related('verifications__verifier')
        return EvidenceAssociationSerializer(assocs, many=True).data

    def validate(self, attrs):
        # Prevent client from injecting forbidden score fields
        initial_data = getattr(self, 'initial_data', {})
        for field in FORBIDDEN_SCORE_FIELDS:
            if field in initial_data:
                raise serializers.ValidationError({
                    field: f"Client cannot supply or modify score field '{field}'. Score is server-authoritative."
                })
        return attrs


class CollegeAssessmentCreateSerializer(serializers.Serializer):
    """
    Validates payload for creating a College assessment session.
    Automatically enforces framework COLLEGE_2026 and assessment period (2025-07-01 to 2026-06-30).
    """
    college_id = serializers.IntegerField(required=False, default=None)
    academic_year = serializers.CharField(max_length=20, required=False, default="2025-26")
    assessment_id = serializers.CharField(max_length=100, required=False, allow_blank=True, default=None)
    framework = serializers.CharField(required=False, default=COLLEGE_FRAMEWORK_CODE)
    period_start = serializers.DateField(required=False, default=date(2025, 7, 1))
    period_end = serializers.DateField(required=False, default=date(2026, 6, 30))

    def validate_framework(self, value):
        if value and value.strip().upper() not in (COLLEGE_FRAMEWORK_CODE, "COLLEGE"):
            raise serializers.ValidationError(
                f"Invalid framework '{value}'. Client cannot override framework; expected '{COLLEGE_FRAMEWORK_CODE}'.",
                code="INVALID_FRAMEWORK"
            )
        return COLLEGE_FRAMEWORK_CODE

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


class CollegeParameterInputSerializer(serializers.Serializer):
    """
    Validates parameter inputs for a specific College parameter (C1–C22).
    Rejects any client attempts to set scores, marks, or certification states.
    Validates semantic content using Phase 7A validators.
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
        param_def = get_college_parameter(param_clean)
        subcriteria_defs = param_def.get("subcriteria", {})
        raw_inputs = self.validated_data.get("raw_inputs", {})

        # Subcriteria keys validation
        for sub_key, sub_val in raw_inputs.items():
            sub_canonical = validate_subcriterion(sub_key, expected_parameter=param_clean)
            if isinstance(sub_val, dict):
                for k, v in sub_val.items():
                    if k in FORBIDDEN_SCORE_FIELDS:
                        raise serializers.ValidationError({
                            k: f"Client cannot supply score field '{k}' in subcriterion payload."
                        })
                    if "pct" in k.lower() or "percentage" in k.lower() or "ratio" in k.lower():
                        if isinstance(v, (int, float)):
                            validate_percentage(v, label=k)
                    elif "count" in k.lower() or "number" in k.lower() or "students" in k.lower() or "faculty" in k.lower():
                        if isinstance(v, (int, float)):
                            validate_count(v, label=k)
                    elif "amount" in k.lower() or "inr" in k.lower() or "lakhs" in k.lower() or "budget" in k.lower():
                        if isinstance(v, (int, float)):
                            validate_currency_amount(v, label=k)

        # Validate activity date if present
        act_date = self.validated_data.get("activity_date")
        if act_date:
            validate_temporal_activity_date(act_date, param_clean)

        return self.validated_data


class CollegeParameterMetadataSerializer(serializers.Serializer):
    """
    Exposes parameter metadata from authoritative registry along with current submitted inputs.
    """
    parameter_code = serializers.CharField()
    title = serializers.CharField()
    max_marks = serializers.FloatField()
    aggregation_strategy = serializers.CharField()
    period_rule = serializers.CharField()
    double_counting_rule = serializers.CharField()
    resolution_status = serializers.CharField(required=False, default="RESOLVED")
    unresolved_reason = serializers.CharField(required=False, default="")
    subcriteria = serializers.DictField()
    mandatory_evidence = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    submitted_input = serializers.DictField(required=False, default=dict)


class CollegeEvaluationResponseSerializer(serializers.Serializer):
    """
    Serializes scoring evaluation results from the frozen engine in a read-only schema.
    """
    framework = serializers.CharField()
    assessment_id = serializers.CharField()
    institution_id = serializers.CharField()
    calculation_id = serializers.CharField()
    raw_total = serializers.FloatField()
    evidence_gated_total = serializers.FloatField()
    final_certified_total = serializers.FloatField(allow_null=True)
    max_marks = serializers.FloatField()
    certification_status = serializers.CharField()
    blocking_reasons = serializers.ListField(child=serializers.CharField())
    parameter_results = serializers.DictField()
    trace = serializers.DictField()


class CollegeAssessmentEvaluateSerializer(serializers.Serializer):
    """Validates scoring evaluation request parameters."""
    reviewer_adjustments = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list
    )


class CollegeReviewStartSerializer(serializers.Serializer):
    """Payload for starting review on a College assessment."""
    comments = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        for field in FORBIDDEN_SCORE_FIELDS:
            if field in self.initial_data:
                raise serializers.ValidationError(
                    {"error": f"Field '{field}' cannot be supplied by the client.", "code": "CLIENT_SCORE_FORBIDDEN"}
                )
        return attrs


class CollegeReviewCompleteSerializer(serializers.Serializer):
    """Payload for completing review on a College assessment."""
    comments = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        for field in FORBIDDEN_SCORE_FIELDS:
            if field in self.initial_data:
                raise serializers.ValidationError(
                    {"error": f"Field '{field}' cannot be supplied by the client.", "code": "CLIENT_SCORE_FORBIDDEN"}
                )
        return attrs


class CollegeReviewCorrectionSerializer(serializers.Serializer):
    """Payload for returning a College assessment for correction."""
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


class CollegeReviewBlockSerializer(serializers.Serializer):
    """Payload for blocking a College assessment review."""
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


class CollegeCertifySerializer(serializers.Serializer):
    """Payload for certifying a College assessment."""
    remarks = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        for field in FORBIDDEN_SCORE_FIELDS:
            if field in self.initial_data:
                raise serializers.ValidationError(
                    {"error": f"Field '{field}' cannot be supplied by the client.", "code": "CLIENT_SCORE_FORBIDDEN"}
                )
        return attrs


class CollegeReviewRecordSerializer(serializers.ModelSerializer):
    """Serializes append-only review history."""
    reviewer_name = serializers.CharField(source="reviewer.get_full_name", read_only=True)
    reviewer_email = serializers.CharField(source="reviewer.email", read_only=True)

    class Meta:
        model = CollegeReviewRecord
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


class CollegeReviewQueueItemSerializer(serializers.ModelSerializer):
    """Serializes assessment records in the committee review queue."""
    college_name = serializers.CharField(source="college.name", read_only=True)
    aishe_code = serializers.CharField(source="college.aishe_code", read_only=True)
    assigned_reviewer_email = serializers.CharField(source="assigned_reviewer.email", read_only=True, default=None)

    class Meta:
        model = CollegeAssessment
        fields = [
            "assessment_id",
            "college_id",
            "college_name",
            "aishe_code",
            "academic_year",
            "status",
            "submitted_at",
            "certified_score",
            "certification_status",
            "assigned_reviewer_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
