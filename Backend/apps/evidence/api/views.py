"""
NEP Excellence Awards 2026 - Evidence REST API Views
Production-ready API endpoints exposing the complete evidence subsystem.
Business logic is preserved in domain services; views act as clean HTTP adapters.
"""
import uuid
from functools import wraps
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView


from apps.authentication.authentication import JWTAuthentication
from apps.evidence.enums import EvidenceLifecycleState
from apps.evidence.exceptions import (
    ConcurrentVerificationConflictError,
    EvidenceDomainError,
    EvidenceIntegrityError,
    EvidenceTamperingDetectedError,
    FrameworkMismatchError,
    ImmutableRecordError,
    InvalidAssociationError,
    InvalidStateTransitionError,
    MandatoryRejectionReasonError,
    ReviewerAssignmentError,
    ReviewerConflictOfInterestError,
    ReviewerNotAuthorizedError,
    UnauthorizedEvidenceActionError,
)
from apps.evidence.models import EvidenceDocument
from apps.evidence.pipeline import EvidenceUploadPipeline
from apps.evidence.services import EvidenceService
from apps.evidence.validators import (
    FileEmptyError,
    FileTooLargeError,
    FileValidationError,
    MaliciousContentError,
    MimeMismatchError,
    UnsafeFilenameError,
    UnsupportedFileTypeError,
)

from .permissions import (
    IsAuthenticatedUser,
    IsCommitteeRole,
    IsEvidenceOwnerOrAdmin,
    IsStateAdminRole,
)
from .serializers import (
    EvidenceCoverageQuerySerializer,
    EvidenceCreateAssociationSerializer,
    EvidenceDocumentSerializer,
    EvidenceRejectionActionSerializer,
    EvidenceUploadSerializer,
    EvidenceVerificationActionSerializer,
    EvidenceWithdrawalSerializer,
    ReviewerAssignmentSerializer,
    ReviewerQueueFilterSerializer,
    ReviewerUnassignmentSerializer,
)


def get_evidence_document(pk_or_uuid, select_related_fields=None, prefetch_related_fields=None) -> EvidenceDocument:
    """
    Retrieves an EvidenceDocument by either integer pk or UUID document_id.
    Raises EvidenceDocument.DoesNotExist if not found.
    """
    qs = EvidenceDocument.objects
    if select_related_fields:
        qs = qs.select_related(*select_related_fields)
    if prefetch_related_fields:
        qs = qs.prefetch_related(*prefetch_related_fields)

    try:
        val = uuid.UUID(str(pk_or_uuid))
        return qs.get(document_id=val)
    except (ValueError, TypeError):
        try:
            return qs.get(pk=int(pk_or_uuid))
        except (ValueError, TypeError):
            raise EvidenceDocument.DoesNotExist()


class EvidencePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


def handle_evidence_exceptions(view_method):
    """
    Standardizes domain exception mapping to clean REST HTTP error responses.
    Prevents leaking internal stack traces or database structures.
    """
    @wraps(view_method)
    def wrapper(*args, **kwargs):
        try:
            return view_method(*args, **kwargs)
        except (
            UnauthorizedEvidenceActionError,
            ReviewerNotAuthorizedError,
            ReviewerConflictOfInterestError,
        ) as exc:
            return Response(
                {"error": "forbidden", "detail": str(exc)},
                status=status.HTTP_403_FORBIDDEN
            )
        except (
            ConcurrentVerificationConflictError,
            InvalidStateTransitionError,
        ) as exc:
            return Response(
                {"error": "conflict", "detail": str(exc)},
                status=status.HTTP_409_CONFLICT
            )
        except FileTooLargeError as exc:
            return Response(
                {"error": "file_too_large", "detail": str(exc)},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            )
        except (
            MandatoryRejectionReasonError,
            InvalidAssociationError,
            FrameworkMismatchError,
            EvidenceTamperingDetectedError,
            EvidenceIntegrityError,
            ImmutableRecordError,
            ReviewerAssignmentError,
            FileEmptyError,
            UnsafeFilenameError,
            UnsupportedFileTypeError,
            MaliciousContentError,
            MimeMismatchError,
            FileValidationError,
        ) as exc:
            return Response(
                {"error": "bad_request", "detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except EvidenceDocument.DoesNotExist:
            return Response(
                {"error": "not_found", "detail": "Evidence document not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        except EvidenceDomainError as exc:
            return Response(
                {"error": "domain_error", "detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )
    return wrapper


class EvidenceListCreateView(APIView):
    """
    GET: List accessible evidence documents for the requesting user's scope.
    POST: Upload new evidence document through Phase 5B pipeline.
    """
    permission_classes = [IsAuthenticatedUser]
    pagination_class = EvidencePagination

    @handle_evidence_exceptions
    def get(self, request):
        user = request.user
        role = getattr(user, 'role', '')

        # Base queryset: active evidence
        qs = EvidenceDocument.objects.filter(is_active=True).select_related(
            'uploader', 'assigned_reviewer'
        ).prefetch_related('associations')

        # Scope restriction by role
        if not (getattr(user, 'is_superuser', False) or role in ('admin', 'state_admin')):
            if role in ('principal', 'nodal_officer', 'faculty'):
                user_college = getattr(user, 'college', None)
                college_code = getattr(user_college, 'aishe_code', None) or str(getattr(user_college, 'pk', ''))
                qs = qs.filter(institution_id=college_code)
            elif role == 'committee':
                # Reviewers see documents assigned to them or in their authorized framework
                qs = qs.exclude(institution_id=getattr(user.college, 'aishe_code', ''))

        # Filtering parameters
        assessment_id = request.query_params.get('assessment_id')
        if assessment_id:
            qs = qs.filter(assessment_id=assessment_id)

        framework = request.query_params.get('framework')
        if framework:
            qs = qs.filter(framework=framework)

        status_param = request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        parameter_id = request.query_params.get('parameter_id')
        if parameter_id:
            qs = qs.filter(associations__parameter_id=parameter_id)

        subcriterion_id = request.query_params.get('subcriterion_id')
        if subcriterion_id:
            qs = qs.filter(associations__subcriterion_id=subcriterion_id)

        qs = qs.order_by('-upload_timestamp').distinct()

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            serializer = EvidenceDocumentSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = EvidenceDocumentSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @handle_evidence_exceptions
    def post(self, request):
        serializer = EvidenceUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = request.user
        user_college = getattr(user, 'college', None)
        inst_id = data.get('institution_id') or (getattr(user_college, 'aishe_code', None) or str(getattr(user_college, 'pk', '')))

        # Delegate intake to Phase 5B upload pipeline
        doc = EvidenceUploadPipeline.process_upload(
            uploader=user,
            assessment_id=data['assessment_id'],
            framework=data['framework'],
            institution_type=data.get('institution_type') or "COLLEGE",
            institution_id=inst_id,
            file_data=data['file'],
            filename=data['file'].name,
            evidence_type=data.get('evidence_type', 'EVID_GENERAL'),
            document_date=data.get('document_date'),
            academic_year=data.get('academic_year', '2025-26'),
            parameter_id=data.get('parameter_id'),
            subcriterion_id=data.get('subcriterion_id'),
            response_id=data.get('response_id', ''),
            auto_submit=data.get('auto_submit', False),
        )

        resp_serializer = EvidenceDocumentSerializer(doc)
        return Response(resp_serializer.data, status=status.HTTP_201_CREATED)


class EvidenceDetailView(APIView):
    """
    GET: Retrieve metadata for a specific evidence document.
    """
    permission_classes = [IsAuthenticatedUser, IsEvidenceOwnerOrAdmin]

    @handle_evidence_exceptions
    def get(self, request, pk):
        doc = get_evidence_document(
            pk,
            select_related_fields=['uploader', 'assigned_reviewer'],
            prefetch_related_fields=['associations'],
        )
        self.check_object_permissions(request, doc)
        serializer = EvidenceDocumentSerializer(doc)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EvidenceSubmitView(APIView):
    """
    POST: Submit an evidence document for committee review.
    """
    permission_classes = [IsAuthenticatedUser, IsEvidenceOwnerOrAdmin]

    @handle_evidence_exceptions
    def post(self, request, pk):
        doc = get_evidence_document(pk)
        self.check_object_permissions(request, doc)
        updated_doc = EvidenceService.submit_for_verification(doc.pk, request.user)
        serializer = EvidenceDocumentSerializer(updated_doc)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EvidenceWithdrawView(APIView):
    """
    POST: Withdraw an evidence document.
    """
    permission_classes = [IsAuthenticatedUser, IsEvidenceOwnerOrAdmin]

    @handle_evidence_exceptions
    def post(self, request, pk):
        doc = get_evidence_document(pk)
        self.check_object_permissions(request, doc)
        serializer = EvidenceWithdrawalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get('reason', 'Withdrawn by institution')

        updated_doc = EvidenceService.withdraw_evidence(doc.pk, request.user, reason=reason)
        resp_serializer = EvidenceDocumentSerializer(updated_doc)
        return Response(resp_serializer.data, status=status.HTTP_200_OK)


class EvidenceAssociateView(APIView):
    """
    POST: Associate an evidence document with a framework parameter and subcriterion.
    """
    permission_classes = [IsAuthenticatedUser, IsEvidenceOwnerOrAdmin]

    @handle_evidence_exceptions
    def post(self, request, pk):
        doc = get_evidence_document(pk)
        self.check_object_permissions(request, doc)
        serializer = EvidenceCreateAssociationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        EvidenceService.associate_subcriterion(
            evidence_id=doc.pk,
            parameter_id=data['parameter_id'],
            subcriterion_id=data['subcriterion_id'],
            actor=request.user,
            response_id=data.get('response_id', ''),
            academic_year=data.get('academic_year', '2025-26'),
        )

        doc.refresh_from_db()
        resp_serializer = EvidenceDocumentSerializer(doc)
        return Response(resp_serializer.data, status=status.HTTP_200_OK)


class ReviewerQueueView(APIView):
    """
    GET: Retrieve screening committee review queue with automatic conflict-of-interest exclusion.
    """
    permission_classes = [IsAuthenticatedUser, IsCommitteeRole]
    pagination_class = EvidencePagination

    @handle_evidence_exceptions
    def get(self, request):
        serializer = ReviewerQueueFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        queue_items = EvidenceService.get_reviewer_queue(
            reviewer=request.user,
            framework=data.get('framework'),
            institution_id=data.get('institution_id'),
            parameter_id=data.get('parameter_id'),
            subcriterion_id=data.get('subcriterion_id'),
            status=data.get('status'),
            assigned_to=data.get('assigned_to'),
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queue_items, request)
        if page is not None:
            return paginator.get_paginated_response(page)

        return Response(queue_items, status=status.HTTP_200_OK)


class ReviewerAssignView(APIView):
    """
    POST: Administrative assignment of evidence to a committee reviewer.
    """
    permission_classes = [IsAuthenticatedUser, IsStateAdminRole]

    @handle_evidence_exceptions
    def post(self, request, pk):
        doc = get_evidence_document(pk)
        serializer = ReviewerAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reviewer_user = serializer.validated_data['reviewer_id']
        notes = serializer.validated_data.get('notes', '')

        EvidenceService.assign_reviewer(
            evidence_id=doc.pk,
            reviewer=reviewer_user,
            assigned_by=request.user,
            notes=notes,
        )

        return Response({
            "message": "Reviewer assigned successfully",
            "evidence_id": str(doc.document_id),
            "assigned_reviewer": reviewer_user.email,
        }, status=status.HTTP_200_OK)


class ReviewerUnassignView(APIView):
    """
    POST: Administrative revocation of reviewer assignment.
    """
    permission_classes = [IsAuthenticatedUser, IsStateAdminRole]

    @handle_evidence_exceptions
    def post(self, request, pk):
        doc = get_evidence_document(pk)
        serializer = ReviewerUnassignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get('reason', '')

        EvidenceService.unassign_reviewer(
            evidence_id=doc.pk,
            unassigned_by=request.user,
            reason=reason,
        )

        return Response({
            "message": "Reviewer unassigned successfully",
            "evidence_id": str(doc.document_id),
        }, status=status.HTTP_200_OK)


class EvidenceVerifyView(APIView):
    """
    POST: Approve evidence verification with optional cryptographic hash/version binding.
    """
    permission_classes = [IsAuthenticatedUser, IsCommitteeRole]

    @handle_evidence_exceptions
    def post(self, request, pk):
        doc = get_evidence_document(pk)
        serializer = EvidenceVerificationActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        verification = EvidenceService.verify_evidence(
            evidence_id=doc.pk,
            verifier=request.user,
            reason=data.get('reason', 'Verified by screening committee'),
            expected_checksum=data.get('expected_checksum'),
            expected_version=data.get('expected_version'),
        )

        return Response({
            "verification_id": str(verification.verification_id),
            "decision": verification.decision,
            "resulting_state": verification.resulting_state,
            "inspected_checksum": verification.inspected_checksum,
            "inspected_version": verification.inspected_version,
            "timestamp": verification.timestamp.isoformat(),
        }, status=status.HTTP_200_OK)


class EvidenceRejectView(APIView):
    """
    POST: Reject evidence verification with mandatory reason and structured code.
    """
    permission_classes = [IsAuthenticatedUser, IsCommitteeRole]

    @handle_evidence_exceptions
    def post(self, request, pk):
        doc = get_evidence_document(pk)
        serializer = EvidenceRejectionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        verification = EvidenceService.reject_evidence(
            evidence_id=doc.pk,
            verifier=request.user,
            reason=data['reason'],
            rejection_code=data.get('rejection_code', ''),
            expected_checksum=data.get('expected_checksum'),
            expected_version=data.get('expected_version'),
        )

        return Response({
            "verification_id": str(verification.verification_id),
            "decision": verification.decision,
            "resulting_state": verification.resulting_state,
            "rejection_code": verification.rejection_code,
            "reason": verification.reason,
            "timestamp": verification.timestamp.isoformat(),
        }, status=status.HTTP_200_OK)


class EvidenceVerificationHistoryView(APIView):
    """
    GET: Retrieve immutable chronological verification history for an evidence document.
    """
    permission_classes = [IsAuthenticatedUser, IsEvidenceOwnerOrAdmin]

    @handle_evidence_exceptions
    def get(self, request, pk):
        doc = get_evidence_document(pk)
        self.check_object_permissions(request, doc)
        history = EvidenceService.get_verification_history(doc.pk, user=request.user)
        return Response(history, status=status.HTTP_200_OK)


class EvidenceCoverageView(APIView):
    """
    GET: Retrieve structured evidence coverage report (Phase 5D).
    """
    permission_classes = [IsAuthenticatedUser]

    @handle_evidence_exceptions
    def get(self, request):
        serializer = EvidenceCoverageQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        sub_codes = None
        if data.get('subcriterion_codes'):
            sub_codes = [c.strip() for c in data['subcriterion_codes'].split(',') if c.strip()]

        report = EvidenceService.evaluate_evidence_coverage(
            assessment_id=data.get('assessment_id'),
            institution_id=data.get('institution_id'),
            framework=data.get('framework'),
            requesting_user=request.user,
            subcriterion_codes=sub_codes,
        )

        return Response(report.to_dict(), status=status.HTTP_200_OK)


class EvidenceReadinessView(APIView):
    """
    GET: Determine whether an assessment's evidence is ready for scoring review.
    Does NOT calculate scores.
    """
    permission_classes = [IsAuthenticatedUser]

    @handle_evidence_exceptions
    def get(self, request):
        serializer = EvidenceCoverageQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        sub_codes = None
        if data.get('subcriterion_codes'):
            sub_codes = [c.strip() for c in data['subcriterion_codes'].split(',') if c.strip()]

        is_ready, blocking_reasons, summary = EvidenceService.is_assessment_evidence_ready(
            assessment_id=data.get('assessment_id'),
            institution_id=data.get('institution_id'),
            framework=data.get('framework'),
            requesting_user=request.user,
            subcriterion_codes=sub_codes,
        )

        return Response({
            "is_ready_for_scoring": is_ready,
            "blocking_reasons": blocking_reasons,
            "summary": summary.to_dict(),
        }, status=status.HTTP_200_OK)
