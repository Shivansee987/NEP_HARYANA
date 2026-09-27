"""
NEP Excellence Awards 2026 - Evidence API Serializers
Enforces strict read-only protection on internal fields, checksums, and lifecycle states.
All mutations are delegated to server-authoritative domain services.
"""
from rest_framework import serializers

from apps.authentication.models import User
from apps.evidence.enums import (
    EvidenceLifecycleState,
    RejectionReasonCode,
    VerificationDecision,
)
from apps.evidence.models import (
    EvidenceDocument,
    EvidenceSubcriterionAssociation,
    EvidenceVerification,
)
from apps.scoring.enums import FrameworkType


class EvidenceAssociationSerializer(serializers.ModelSerializer):
    """Serializes an association between an evidence document and a subcriterion."""
    id = serializers.IntegerField(read_only=True)
    association_id = serializers.UUIDField(read_only=True)
    evidence_document_id = serializers.UUIDField(source='evidence.document_id', read_only=True)
    original_filename = serializers.CharField(source='evidence.original_filename', read_only=True)
    file_checksum = serializers.CharField(source='evidence.file_checksum', read_only=True)
    mime_type = serializers.CharField(source='evidence.mime_type', read_only=True)
    file_size = serializers.IntegerField(source='evidence.file_size', read_only=True)
    framework = serializers.CharField(source='evidence.framework', read_only=True)
    institution_id = serializers.CharField(source='evidence.institution_id', read_only=True)
    verification_status = serializers.CharField(read_only=True, allow_null=True)
    latest_verification = serializers.SerializerMethodField()

    class Meta:
        model = EvidenceSubcriterionAssociation
        fields = [
            'id',
            'association_id',
            'evidence_document_id',
            'original_filename',
            'file_checksum',
            'mime_type',
            'file_size',
            'framework',
            'institution_id',
            'parameter_id',
            'subcriterion_id',
            'subcriterion_evidence_type',
            'response_id',
            'academic_year',
            'page_start',
            'page_end',
            'section_identifier',
            'claim_description',
            'verification_status',
            'latest_verification',
            'associated_at',
            'is_active',
        ]
        read_only_fields = fields

    def get_latest_verification(self, obj):
        v = obj.latest_verification
        if not v:
            return None
        return {
            "verification_id": str(v.verification_id),
            "decision": v.decision,
            "verifier_id": v.verifier_id,
            "verifier_email": getattr(v.verifier, 'email', str(v.verifier_id)),
            "reason": v.reason,
            "rejection_code": v.rejection_code,
            "inspected_checksum": v.inspected_checksum,
            "timestamp": v.timestamp.isoformat(),
        }


class EvidenceAssociationActionSerializer(serializers.Serializer):
    """Validates action payload for verifying an association."""
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    expected_checksum = serializers.CharField(max_length=64, required=False, allow_blank=True, default=None)
    metadata = serializers.DictField(required=False, default=dict)


class EvidenceAssociationRejectionActionSerializer(serializers.Serializer):
    """Validates action payload for rejecting an association."""
    reason = serializers.CharField(required=True, allow_blank=False)
    rejection_code = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        default=RejectionReasonCode.OTHER
    )
    expected_checksum = serializers.CharField(max_length=64, required=False, allow_blank=True, default=None)
    metadata = serializers.DictField(required=False, default=dict)


class EvidenceCreateAssociationSerializer(serializers.Serializer):
    """Validates payload for associating evidence to a subcriterion."""
    parameter_id = serializers.CharField(max_length=50, required=True)
    subcriterion_id = serializers.CharField(max_length=50, required=True)
    response_id = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    academic_year = serializers.CharField(max_length=20, required=False, allow_blank=True, default="2025-26")
    evidence_type = serializers.CharField(max_length=100, required=False, allow_blank=True, default=None)
    subcriterion_evidence_type = serializers.CharField(max_length=100, required=False, allow_blank=True, default=None)
    page_start = serializers.IntegerField(required=False, allow_null=True, min_value=1, default=None)
    page_end = serializers.IntegerField(required=False, allow_null=True, min_value=1, default=None)
    section_identifier = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    claim_description = serializers.CharField(required=False, allow_blank=True, default="")


class EvidenceDocumentSerializer(serializers.ModelSerializer):
    """
    Serializes evidence document metadata.
    Strictly omits internal storage filesystem paths and binary blobs.
    """
    uploader_email = serializers.EmailField(source='uploader.email', read_only=True)
    assigned_reviewer_email = serializers.EmailField(source='assigned_reviewer.email', read_only=True, default=None)
    associations = EvidenceAssociationSerializer(many=True, read_only=True)

    class Meta:
        model = EvidenceDocument
        fields = [
            'document_id',
            'original_filename',
            'mime_type',
            'file_size',
            'file_checksum',
            'version',
            'framework',
            'institution_type',
            'institution_id',
            'assessment_id',
            'evidence_type',
            'document_date',
            'academic_year',
            'status',
            'is_active',
            'uploader_email',
            'assigned_reviewer_email',
            'assigned_at',
            'upload_timestamp',
            'metadata',
            'associations',
        ]
        read_only_fields = fields


class EvidenceUploadSerializer(serializers.Serializer):
    """Validates incoming multipart file upload and metadata."""
    file = serializers.FileField(required=True)
    filename = serializers.CharField(max_length=255, required=False, allow_blank=True, default=None)
    assessment_id = serializers.CharField(max_length=100, required=True)
    framework = serializers.ChoiceField(
        choices=[FrameworkType.COLLEGE_2026.value, FrameworkType.UNIVERSITY_2026.value],
        required=True
    )
    institution_id = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    institution_type = serializers.CharField(max_length=50, required=False, allow_blank=True, default="COLLEGE")
    evidence_type = serializers.CharField(max_length=100, required=False, allow_blank=True, default=None)
    document_date = serializers.DateField(required=False, allow_null=True, default=None)
    academic_year = serializers.CharField(max_length=20, required=False, allow_blank=True, default="2025-26")
    parameter_id = serializers.CharField(max_length=50, required=False, allow_blank=True, default=None)
    subcriterion_id = serializers.CharField(max_length=50, required=False, allow_blank=True, default=None)
    response_id = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    auto_submit = serializers.BooleanField(required=False, default=False)

    def validate_filename(self, value):
        if value:
            from apps.evidence.validators import FilenameValidator
            try:
                FilenameValidator.validate_and_sanitize(value)
            except Exception as e:
                raise serializers.ValidationError(str(e))
        return value

    def validate(self, attrs):
        # Security: strictly reject any attempt to inject score fields via evidence upload
        from apps.college.api.serializers import FORBIDDEN_SCORE_FIELDS
        for field in FORBIDDEN_SCORE_FIELDS:
            if field in self.initial_data:
                raise serializers.ValidationError({field: f"Score field '{field}' cannot be injected via evidence upload."})

        # Taxonomy derivation and validation (DEF-01)
        from apps.evidence.taxonomy import (
            derive_or_validate_evidence_type,
            EvidenceTaxonomyError,
        )

        framework = attrs.get('framework')
        evidence_type = attrs.get('evidence_type')
        parameter_id = attrs.get('parameter_id')
        subcriterion_id = attrs.get('subcriterion_id')

        try:
            resolved_evidence_type = derive_or_validate_evidence_type(
                framework=framework,
                evidence_type=evidence_type,
                parameter_id=parameter_id,
                subcriterion_id=subcriterion_id,
            )
            attrs['evidence_type'] = resolved_evidence_type
        except EvidenceTaxonomyError as e:
            raise serializers.ValidationError({"evidence_type": str(e)})

        return attrs


class EvidenceWithdrawalSerializer(serializers.Serializer):
    """Validates payload for evidence withdrawal."""
    reason = serializers.CharField(required=False, allow_blank=True, default="Withdrawn by institution")


class ReviewerAssignmentSerializer(serializers.Serializer):
    """Validates administrative reviewer assignment."""
    reviewer_id = serializers.CharField(required=True, help_text="Reviewer user ID or email")
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_reviewer_id(self, value):
        try:
            # Check if UUID or PK or email
            if '@' in value:
                user = User.objects.filter(email=value).first()
            else:
                user = User.objects.filter(id=value).first()
            if not user:
                raise serializers.ValidationError(f"Reviewer user '{value}' does not exist.")
            return user
        except Exception as e:
            raise serializers.ValidationError(str(e))


class ReviewerUnassignmentSerializer(serializers.Serializer):
    """Validates administrative reviewer unassignment."""
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class EvidenceVerificationActionSerializer(serializers.Serializer):
    """Validates reviewer verify action with optional cryptographic hash/version binding."""
    reason = serializers.CharField(required=False, allow_blank=True, default="Verified by screening committee")
    expected_checksum = serializers.CharField(max_length=64, required=False, allow_blank=True, default=None)
    expected_version = serializers.IntegerField(required=False, allow_null=True, default=None)


class EvidenceRejectionActionSerializer(serializers.Serializer):
    """Validates reviewer reject action with mandatory reason and structured code."""
    reason = serializers.CharField(required=True, allow_blank=False)
    rejection_code = serializers.ChoiceField(
        choices=RejectionReasonCode.choices,
        required=False,
        allow_blank=True,
        default=RejectionReasonCode.OTHER
    )
    expected_checksum = serializers.CharField(max_length=64, required=False, allow_blank=True, default=None)
    expected_version = serializers.IntegerField(required=False, allow_null=True, default=None)


class EvidenceVerificationHistorySerializer(serializers.ModelSerializer):
    """Serializes immutable append-only verification events."""
    verifier_email = serializers.EmailField(source='verifier.email', read_only=True)

    class Meta:
        model = EvidenceVerification
        fields = [
            'verification_id',
            'decision',
            'verifier_email',
            'reason',
            'rejection_code',
            'inspected_checksum',
            'inspected_version',
            'resulting_state',
            'timestamp',
            'metadata',
        ]
        read_only_fields = fields


class ReviewerQueueFilterSerializer(serializers.Serializer):
    """Validates query parameters for reviewer queue retrieval."""
    framework = serializers.CharField(required=False)
    institution_id = serializers.CharField(required=False)
    parameter_id = serializers.CharField(required=False)
    subcriterion_id = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    assigned_to = serializers.CharField(required=False)


class EvidenceCoverageQuerySerializer(serializers.Serializer):
    """Validates query parameters for coverage and readiness evaluations."""
    assessment_id = serializers.CharField(required=False)
    institution_id = serializers.CharField(required=False)
    framework = serializers.CharField(required=False)
    subcriterion_codes = serializers.CharField(required=False, help_text="Comma-separated subcriterion codes")
