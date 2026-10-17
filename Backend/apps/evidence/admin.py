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


class ViewOnlyAdmin(admin.ModelAdmin):
    """
    Evidence, associations and verification decisions change only through the committee workflow API, which
    enforces reviewer scope, assessment state and audit logging. The Django admin is a read-only inspection
    tool: nobody (superusers included) can add, edit or delete these records here (FIN-01).
    """
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EvidenceDocument)
class EvidenceDocumentAdmin(ViewOnlyAdmin):
    list_display = ('document_id', 'original_filename', 'framework', 'institution_id', 'status', 'upload_timestamp')
    list_filter = ('framework', 'institution_type', 'status', 'is_active')
    search_fields = ('document_id', 'original_filename', 'institution_id', 'file_checksum')
    readonly_fields = ('document_id', 'file_checksum', 'upload_timestamp')


@admin.register(EvidenceSubcriterionAssociation)
class EvidenceSubcriterionAssociationAdmin(ViewOnlyAdmin):
    list_display = ('association_id', 'evidence', 'parameter_id', 'subcriterion_id', 'subcriterion_evidence_type', 'is_active')
    list_filter = ('parameter_id', 'is_active')
    search_fields = ('parameter_id', 'subcriterion_id', 'subcriterion_evidence_type')
    readonly_fields = ('association_id', 'associated_at')


@admin.register(EvidenceVerification)
class EvidenceVerificationAdmin(ViewOnlyAdmin):
    list_display = ('verification_id', 'evidence', 'verifier', 'decision', 'timestamp')
    list_filter = ('decision',)
    search_fields = ('verification_id', 'verifier__email')
    readonly_fields = ('verification_id', 'timestamp', 'inspected_checksum')


@admin.register(EvidenceAssociationVerification)
class EvidenceAssociationVerificationAdmin(ViewOnlyAdmin):
    list_display = ('verification_id', 'association', 'verifier', 'decision', 'timestamp')
    list_filter = ('decision',)
    search_fields = ('verification_id', 'verifier__email')
    readonly_fields = ('verification_id', 'timestamp', 'inspected_checksum')
