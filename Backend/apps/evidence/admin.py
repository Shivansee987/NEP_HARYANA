"""
NEP Excellence Awards 2026 - Evidence Domain Admin Registration
"""
from django.contrib import admin
from .models import (
    EvidenceDocument,
    EvidenceSubcriterionAssociation,
    EvidenceVerification,
    EvidenceAssociationVerification,
    EvidenceAuditLog,
    ReviewerAuthorization,
    EvidenceReviewAssignment,
)


@admin.register(EvidenceDocument)
class EvidenceDocumentAdmin(admin.ModelAdmin):
    list_display = ('document_id', 'original_filename', 'framework', 'institution_id', 'status', 'upload_timestamp')
    list_filter = ('framework', 'institution_type', 'status', 'is_active')
    search_fields = ('document_id', 'original_filename', 'institution_id', 'file_checksum')
    readonly_fields = ('document_id', 'file_checksum', 'upload_timestamp')


@admin.register(EvidenceSubcriterionAssociation)
class EvidenceSubcriterionAssociationAdmin(admin.ModelAdmin):
    list_display = ('association_id', 'evidence', 'parameter_id', 'subcriterion_id', 'subcriterion_evidence_type', 'is_active')
    list_filter = ('parameter_id', 'is_active')
    search_fields = ('parameter_id', 'subcriterion_id', 'subcriterion_evidence_type')
    readonly_fields = ('association_id', 'associated_at')


@admin.register(EvidenceVerification)
class EvidenceVerificationAdmin(admin.ModelAdmin):
    list_display = ('verification_id', 'evidence', 'verifier', 'decision', 'timestamp')
    list_filter = ('decision',)
    search_fields = ('verification_id', 'verifier__email')
    readonly_fields = ('verification_id', 'timestamp', 'inspected_checksum')


@admin.register(EvidenceAssociationVerification)
class EvidenceAssociationVerificationAdmin(admin.ModelAdmin):
    list_display = ('verification_id', 'association', 'verifier', 'decision', 'timestamp')
    list_filter = ('decision',)
    search_fields = ('verification_id', 'verifier__email')
    readonly_fields = ('verification_id', 'timestamp', 'inspected_checksum')
