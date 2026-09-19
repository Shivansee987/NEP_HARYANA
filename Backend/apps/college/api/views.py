"""
NEP Excellence Awards 2026 - College REST API Views (Phase 7B)
Production-ready API endpoints exposing the complete College assessment workflow.
Business logic is preserved in domain services; views act as clean HTTP adapters.
"""
import logging
from functools import wraps
from typing import Any, Dict
from rest_framework import status
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers

logger = logging.getLogger(__name__)

from apps.authentication.models import College
from apps.college.models import CollegeAssessment, CollegeAssessmentAuditLog, CollegeReviewRecord
from apps.college.registry import (
    COLLEGE_FRAMEWORK_CODE,
    COLLEGE_PARAMETER_CODES,
    get_college_parameter,
    get_college_parameters,
    validate_college_parameter_code,
)
from apps.college.services import CollegeAssessmentService, CollegeReviewService
from apps.college.validators import (
    AssessmentAlreadyCertifiedError,
    AssessmentLockedError,
    AssessmentNotReadyError,
    CertificationBlockedError,
    CertificationNotAuthorizedError,
    CollegeNotAuthorizedError,
    CollegeValidationError,
    ConcurrentReviewConflictError,
    ConcurrentUpdateError,
    EvidenceNotReadyError,
    FrameworkMismatchError,
    InvalidFrameworkError,
    InvalidInstitutionTypeError,
    InvalidReviewStateError,
    InvalidStateTransitionError,
    ParameterNotFoundError,
    ReviewConflictError,
    ReviewNotAuthorizedError,
    ScoringBlockedError,
    ScoringNotEvaluatedError,
    SubcriterionNotFoundError,
    TemporalWindowViolationError,
    validate_parameter,
)
from .permissions import (
    AssessmentPermissionDenied,
    CollegePermissionDenied,
    IsAuthenticatedUser,
    IsCertificationAuthority,
    IsCollegeAdminOrOwner,
    IsCollegeAssessmentOwnerOrReviewer,
    IsCommitteeOrAdminForEvaluation,
    IsCommitteeReviewer,
)
from .serializers import (
    CollegeAssessmentCreateSerializer,
    CollegeAssessmentEvaluateSerializer,
    CollegeAssessmentSerializer,
    CollegeCertifySerializer,
    CollegeEvaluationResponseSerializer,
    CollegeParameterInputSerializer,
    CollegeParameterMetadataSerializer,
    CollegeReadSerializer,
    CollegeReviewBlockSerializer,
    CollegeReviewCompleteSerializer,
    CollegeReviewCorrectionSerializer,
    CollegeReviewQueueItemSerializer,
    CollegeReviewRecordSerializer,
    CollegeReviewStartSerializer,
    FORBIDDEN_SCORE_FIELDS,
)


class CollegePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


def handle_college_exceptions(view_func):
    """
    Decorator for standardized exception translation.
    Prevents leaking internal stack traces and maps domain errors to RFC-compliant HTTP status codes.
    """
    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        try:
            return view_func(self, request, *args, **kwargs)
        except NotAuthenticated:
            return Response(
                {"error": "Authentication credentials were not provided.", "code": "NOT_AUTHENTICATED"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except (CollegePermissionDenied, AssessmentPermissionDenied) as exc:
            return Response(
                {"error": str(exc.detail) if hasattr(exc, 'detail') else str(exc), "code": getattr(exc, 'code', 'FORBIDDEN')},
                status=status.HTTP_403_FORBIDDEN
            )
        except PermissionDenied as exc:
            return Response(
                {"error": str(exc.detail) if hasattr(exc, 'detail') else str(exc), "code": "FORBIDDEN"},
                status=status.HTTP_403_FORBIDDEN
            )
        except (ReviewNotAuthorizedError, CertificationNotAuthorizedError, ReviewConflictError, AssessmentLockedError) as exc:
            return Response(
                {"error": exc.message, "code": exc.code, "detail": exc.message},
                status=status.HTTP_403_FORBIDDEN
            )
        except (College.DoesNotExist, CollegeAssessment.DoesNotExist):
            return Response(
                {"error": "Requested resource was not found.", "code": "NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND
            )
        except (ConcurrentReviewConflictError, ConcurrentUpdateError, InvalidStateTransitionError) as exc:
            return Response(
                {"error": getattr(exc, 'message', str(exc)), "code": getattr(exc, 'code', 'CONFLICT'), "detail": getattr(exc, 'message', str(exc))},
                status=status.HTTP_409_CONFLICT
            )
        except (
            InvalidReviewStateError,
            AssessmentAlreadyCertifiedError,
            CertificationBlockedError,
            ScoringNotEvaluatedError,
            ScoringBlockedError,
            EvidenceNotReadyError,
            AssessmentNotReadyError,
            FrameworkMismatchError,
        ) as exc:
            return Response(
                {"error": getattr(exc, 'message', str(exc)), "code": getattr(exc, 'code', 'BAD_REQUEST'), "detail": getattr(exc, 'message', str(exc))},
                status=status.HTTP_400_BAD_REQUEST
            )
        except CollegeNotAuthorizedError as exc:
            return Response(
                {"error": str(exc), "code": "ASSESSMENT_NOT_AUTHORIZED"},
                status=status.HTTP_403_FORBIDDEN
            )
        except (
            CollegeValidationError,
            ParameterNotFoundError,
            SubcriterionNotFoundError,
            InvalidFrameworkError,
            InvalidInstitutionTypeError,
            TemporalWindowViolationError,
        ) as exc:
            return Response(
                {"error": str(exc), "code": getattr(exc, 'code', 'VALIDATION_ERROR')},
                status=status.HTTP_400_BAD_REQUEST
            )
        except serializers.ValidationError as exc:
            return Response(
                {"error": exc.detail, "code": "INVALID_INPUT"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as exc:
            logger.error(f"Unexpected error in college API: {exc}", exc_info=True)
            return Response(
                {"error": f"An unexpected error occurred during processing: {exc}", "code": "INTERNAL_SERVER_ERROR"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    return wrapper


def get_college_object(pk: Any) -> College:
    """Retrieves College by numeric ID or AISHE code."""
    if str(pk).isdigit():
        return College.objects.get(pk=int(pk))
    return College.objects.get(aishe_code=str(pk))


def get_college_assessment_object(assessment_id: str) -> CollegeAssessment:
    """Retrieves CollegeAssessment by assessment_id with college relation."""
    return CollegeAssessment.objects.select_related("college").get(assessment_id=assessment_id)


# ==============================================================================
# 1. COLLEGE INSTITUTION ENDPOINTS
# ==============================================================================

class CollegeListCreateView(APIView):
    """
    GET: List College institutions.
    POST: Register a new College institution (Admin only).
    """
    permission_classes = [IsAuthenticatedUser, IsCollegeAdminOrOwner]
    pagination_class = CollegePagination

    @handle_college_exceptions
    def get(self, request):
        user = request.user
        if getattr(user, 'is_superuser', False) or getattr(user, 'role', '') in ('admin', 'state_admin', 'committee', 'committee_chair'):
            qs = College.objects.all().order_by('name')
        else:
            user_col = getattr(user, 'college', None)
            if user_col:
                qs = College.objects.filter(pk=user_col.pk)
            else:
                qs = College.objects.none()

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            serializer = CollegeReadSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = CollegeReadSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @handle_college_exceptions
    def post(self, request):
        user = request.user
        if not (getattr(user, 'is_superuser', False) or getattr(user, 'role', '') in ('admin', 'state_admin')):
            raise CollegePermissionDenied(
                "Only administrators can register new Colleges.",
                code="COLLEGE_NOT_AUTHORIZED"
            )

        name = request.data.get("name")
        aishe_code = request.data.get("aishe_code")
        if not name or not aishe_code:
            raise CollegeValidationError("Both 'name' and 'aishe_code' are required.")

        college = College.objects.create(name=name.strip(), aishe_code=aishe_code.strip())
        return Response(CollegeReadSerializer(college).data, status=status.HTTP_201_CREATED)


class CollegeDetailView(APIView):
    """
    GET: Retrieve College metadata by ID or AISHE code.
    """
    permission_classes = [IsAuthenticatedUser, IsCollegeAdminOrOwner]

    @handle_college_exceptions
    def get(self, request, pk):
        college = get_college_object(pk)
        self.check_object_permissions(request, college)
        return Response(CollegeReadSerializer(college).data, status=status.HTTP_200_OK)


# ==============================================================================
# 2. COLLEGE ASSESSMENT LIFECYCLE ENDPOINTS
# ==============================================================================

class CollegeAssessmentListCreateView(APIView):
    """
    GET: List assessments for a College or authorized user.
    POST: Create a new assessment session for a College.
    """
    permission_classes = [IsAuthenticatedUser, IsCollegeAssessmentOwnerOrReviewer]
    pagination_class = CollegePagination

    @handle_college_exceptions
    def get(self, request, pk=None):
        user = request.user
        qs = CollegeAssessment.objects.select_related("college").order_by('-created_at')

        if pk:
            college = get_college_object(pk)
            self.check_object_permissions(request, CollegeAssessment(college=college))
            qs = qs.filter(college=college)
        else:
            if not (getattr(user, 'is_superuser', False) or getattr(user, 'role', '') in ('admin', 'state_admin', 'committee', 'committee_chair')):
                user_col = getattr(user, 'college', None)
                if user_col:
                    qs = qs.filter(college=user_col)
                else:
                    qs = CollegeAssessment.objects.none()

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            serializer = CollegeAssessmentSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = CollegeAssessmentSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @handle_college_exceptions
    def post(self, request, pk=None):
        user = request.user
        if getattr(user, 'role', '') in ('committee', 'committee_chair'):
            raise AssessmentPermissionDenied(
                "Reviewers are not permitted to create College assessments.",
                code="ASSESSMENT_NOT_AUTHORIZED"
            )

        serializer = CollegeAssessmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        valid_data = serializer.validated_data

        target_college = None
        if pk:
            target_college = get_college_object(pk)
        elif valid_data.get('college_id'):
            target_college = get_college_object(valid_data['college_id'])
        else:
            target_college = getattr(user, 'college', None)

        if not target_college:
            raise CollegeValidationError("Target College must be specified or associated with user.")

        # Tenancy check
        self.check_object_permissions(request, CollegeAssessment(college=target_college))

        assessment = CollegeAssessmentService.create_assessment(
            college_id=target_college,
            assessment_id=valid_data.get('assessment_id'),
            academic_year=valid_data.get('academic_year', '2025-26'),
            created_by=user,
        )

        resp_serializer = CollegeAssessmentSerializer(assessment)
        return Response(resp_serializer.data, status=status.HTTP_201_CREATED)


class CollegeAssessmentDetailView(APIView):
    """
    GET: Retrieve CollegeAssessment details.
    PATCH: Update non-protected metadata. Score injection and status reverts are blocked.
    """
    permission_classes = [IsAuthenticatedUser, IsCollegeAssessmentOwnerOrReviewer]

    @handle_college_exceptions
    def get(self, request, assessment_id):
        assessment = get_college_assessment_object(assessment_id)
        self.check_object_permissions(request, assessment)
        return Response(CollegeAssessmentSerializer(assessment).data, status=status.HTTP_200_OK)

    @handle_college_exceptions
    def patch(self, request, assessment_id):
        assessment = get_college_assessment_object(assessment_id)
        self.check_object_permissions(request, assessment)

        if assessment.status != "DRAFT":
            raise InvalidStateTransitionError(
                f"Assessment '{assessment_id}' is in status '{assessment.status}' and cannot be modified."
            )

        # Reject score injection attempts
        for field in FORBIDDEN_SCORE_FIELDS:
            if field in request.data:
                raise CollegeValidationError(
                    f"Client cannot supply or modify score field '{field}'.",
                    code="INVALID_PARAMETER_INPUT"
                )

        # Reject protected field modifications
        protected = {"framework", "academic_year", "period_start", "period_end", "college_id", "status"}
        for p_field in protected:
            if p_field in request.data:
                raise CollegeValidationError(
                    f"Client cannot modify protected assessment field '{p_field}'.",
                    code="PROTECTED_FIELD_MODIFICATION"
                )

        if "notes" in request.data:
            p_data = dict(assessment.parameter_data or {})
            p_data["_notes"] = request.data["notes"]
            assessment.parameter_data = p_data
            assessment.save(update_fields=["parameter_data", "updated_at"])

        return Response(CollegeAssessmentSerializer(assessment).data, status=status.HTTP_200_OK)


# ==============================================================================
# 3. PARAMETER INPUT ENDPOINTS (C1–C22)
# ==============================================================================

class CollegeAssessmentParametersListView(APIView):
    """
    GET: Lists all 22 College parameters (C1–C22) with metadata and current submitted inputs.
    """
    permission_classes = [IsAuthenticatedUser, IsCollegeAssessmentOwnerOrReviewer]

    @handle_college_exceptions
    def get(self, request, assessment_id):
        assessment = get_college_assessment_object(assessment_id)
        self.check_object_permissions(request, assessment)

        registered_params = get_college_parameters()
        param_data = assessment.parameter_data or {}

        results = []
        for p_code in COLLEGE_PARAMETER_CODES:
            p_conf = registered_params[p_code]
            submitted_data = param_data.get(p_code, {})
            results.append({
                "parameter_code": p_code,
                "title": p_conf.get("title", ""),
                "max_marks": p_conf.get("max_marks", 0.0),
                "aggregation_strategy": p_conf.get("aggregation_strategy", "SUM").value if hasattr(p_conf.get("aggregation_strategy"), "value") else str(p_conf.get("aggregation_strategy")),
                "period_rule": p_conf.get("period_rule", "ACADEMIC_YEAR").value if hasattr(p_conf.get("period_rule"), "value") else str(p_conf.get("period_rule")),
                "double_counting_rule": p_conf.get("double_counting_rule", "FORBIDDEN_REUSE").value if hasattr(p_conf.get("double_counting_rule"), "value") else str(p_conf.get("double_counting_rule")),
                "resolution_status": p_conf.get("resolution_status", "RESOLVED").value if hasattr(p_conf.get("resolution_status"), "value") else str(p_conf.get("resolution_status", "RESOLVED")),
                "unresolved_reason": p_conf.get("unresolved_reason", ""),
                "subcriteria": p_conf.get("subcriteria", {}),
                "mandatory_evidence": p_conf.get("mandatory_evidence", []),
                "submitted_input": submitted_data,
            })

        return Response(results, status=status.HTTP_200_OK)


class CollegeAssessmentParameterDetailView(APIView):
    """
    GET: Retrieve specific parameter metadata and submitted inputs.
    PUT/PATCH: Update raw parameter inputs and entities for C1–C22.
    """
    permission_classes = [IsAuthenticatedUser, IsCollegeAssessmentOwnerOrReviewer]

    @handle_college_exceptions
    def get(self, request, assessment_id, parameter_code):
        assessment = get_college_assessment_object(assessment_id)
        self.check_object_permissions(request, assessment)

        param_clean = validate_parameter(parameter_code)
        param_conf = get_college_parameter(param_clean)
        param_data = assessment.parameter_data or {}
        submitted_data = param_data.get(param_clean, {})

        resp_data = {
            "parameter_code": param_clean,
            "title": param_conf.get("title", ""),
            "max_marks": param_conf.get("max_marks", 0.0),
            "aggregation_strategy": param_conf.get("aggregation_strategy", "SUM").value if hasattr(param_conf.get("aggregation_strategy"), "value") else str(param_conf.get("aggregation_strategy")),
            "period_rule": param_conf.get("period_rule", "ACADEMIC_YEAR").value if hasattr(param_conf.get("period_rule"), "value") else str(param_conf.get("period_rule")),
            "double_counting_rule": param_conf.get("double_counting_rule", "FORBIDDEN_REUSE").value if hasattr(param_conf.get("double_counting_rule"), "value") else str(param_conf.get("double_counting_rule")),
            "resolution_status": param_conf.get("resolution_status", "RESOLVED").value if hasattr(param_conf.get("resolution_status"), "value") else str(param_conf.get("resolution_status", "RESOLVED")),
            "unresolved_reason": param_conf.get("unresolved_reason", ""),
            "subcriteria": param_conf.get("subcriteria", {}),
            "mandatory_evidence": param_conf.get("mandatory_evidence", []),
            "submitted_input": submitted_data,
        }
        return Response(resp_data, status=status.HTTP_200_OK)

    @handle_college_exceptions
    def put(self, request, assessment_id, parameter_code):
        return self._update_parameter(request, assessment_id, parameter_code)

    @handle_college_exceptions
    def patch(self, request, assessment_id, parameter_code):
        return self._update_parameter(request, assessment_id, parameter_code)

    def _update_parameter(self, request, assessment_id, parameter_code):
        assessment = get_college_assessment_object(assessment_id)
        self.check_object_permissions(request, assessment)

        if assessment.status != "DRAFT":
            raise InvalidStateTransitionError(
                f"Assessment '{assessment_id}' is in status '{assessment.status}' and cannot be modified."
            )

        param_clean = validate_parameter(parameter_code)
        serializer = CollegeParameterInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        valid_data = serializer.validate_with_parameter(param_clean)

        updated_assessment = CollegeAssessmentService.update_parameter_inputs(
            assessment_id=assessment.assessment_id,
            parameter_code=param_clean,
            raw_inputs=valid_data.get("raw_inputs", {}),
            entities=valid_data.get("entities", []),
            activity_date=valid_data.get("activity_date"),
        )

        resp_param_data = updated_assessment.parameter_data.get(param_clean, {})
        return Response({
            "parameter_code": param_clean,
            "status": "SAVED",
            "submitted_input": resp_param_data,
        }, status=status.HTTP_200_OK)


# ==============================================================================
# 4. EVIDENCE COVERAGE & READINESS ENDPOINTS
# ==============================================================================

class CollegeAssessmentCoverageView(APIView):
    """
    GET: Evaluates evidence coverage across College subcriteria via Phase 5D.
    Does NOT calculate marks.
    """
    permission_classes = [IsAuthenticatedUser, IsCollegeAssessmentOwnerOrReviewer]

    @handle_college_exceptions
    def get(self, request, assessment_id):
        assessment = get_college_assessment_object(assessment_id)
        self.check_object_permissions(request, assessment)

        report = CollegeAssessmentService.evaluate_assessment_coverage(
            assessment_id=assessment.assessment_id,
            user=request.user,
        )
        return Response(report.to_dict(), status=status.HTTP_200_OK)


class CollegeAssessmentReadinessView(APIView):
    """
    GET: Evaluates evidence readiness via Phase 5D readiness service.
    Clearly distinguishes evidence readiness from scoring results.
    """
    permission_classes = [IsAuthenticatedUser, IsCollegeAssessmentOwnerOrReviewer]

    @handle_college_exceptions
    def get(self, request, assessment_id):
        assessment = get_college_assessment_object(assessment_id)
        self.check_object_permissions(request, assessment)

        is_ready, blocking_reasons, summary = CollegeAssessmentService.check_assessment_readiness(
            assessment_id=assessment.assessment_id,
            user=request.user,
        )

        return Response({
            "assessment_id": assessment.assessment_id,
            "framework": COLLEGE_FRAMEWORK_CODE,
            "is_ready": is_ready,
            "blocking_reasons": blocking_reasons,
            "evidence_readiness_summary": summary.to_dict(),
        }, status=status.HTTP_200_OK)


# ==============================================================================
# 5. SCORING EVALUATION ENDPOINT (FROZEN ENGINE)
# ==============================================================================

class CollegeAssessmentEvaluateView(APIView):
    """
    POST: Executes scoring exclusively via frozen NEP2026ScoringEngine.
    Protected from direct client score injection.
    """
    permission_classes = [IsAuthenticatedUser, IsCollegeAssessmentOwnerOrReviewer]

    @handle_college_exceptions
    def post(self, request, assessment_id):
        assessment = get_college_assessment_object(assessment_id)
        self.check_object_permissions(request, assessment)

        # Reject any client-supplied score in request body
        for field in FORBIDDEN_SCORE_FIELDS:
            if field in request.data:
                raise CollegeValidationError(
                    f"Client cannot supply score field '{field}'. Scoring is server-authoritative.",
                    code="INVALID_PARAMETER_INPUT"
                )

        # Delegate exclusively to frozen scoring engine via service layer
        result = CollegeAssessmentService.evaluate_assessment_scoring(
            assessment_id=assessment.assessment_id
        )

        # Format structured response
        param_results_dict = {}
        for p_code, p_res in result.parameter_results.items():
            sub_dict = {}
            for s_code, s_res in p_res.subcriteria_results.items():
                sub_dict[s_code] = {
                    "subcriterion_code": s_res.subcriterion_code,
                    "raw_score": s_res.raw_score,
                    "evidence_gated_score": s_res.evidence_gated_score,
                    "final_score": s_res.final_score,
                    "max_score": s_res.max_score,
                    "resolution_status": s_res.resolution_status.value,
                    "gating_status": s_res.gating_status.value,
                    "trace": s_res.trace,
                }
            param_results_dict[p_code] = {
                "parameter_code": p_res.parameter_code,
                "max_marks": p_res.max_marks,
                "raw_score": p_res.raw_score,
                "evidence_gated_score": p_res.evidence_gated_score,
                "final_score": p_res.final_score,
                "resolution_status": p_res.resolution_status.value,
                "subcriteria_results": sub_dict,
                "trace": p_res.trace,
            }

        response_data = {
            "framework": result.framework.value,
            "assessment_id": result.assessment_id,
            "institution_id": result.institution_id,
            "calculation_id": result.calculation_id,
            "raw_total": result.raw_total,
            "evidence_gated_total": result.evidence_gated_total,
            "final_certified_total": result.final_certified_total,
            "max_marks": result.max_marks,
            "certification_status": result.certification_status.value,
            "blocking_reasons": result.blocking_reasons,
            "parameter_results": param_results_dict,
            "trace": result.trace,
        }

        return Response(response_data, status=status.HTTP_200_OK)


# ==============================================================================
# 6. FORMAL ASSESSMENT SUBMISSION ENDPOINT
# ==============================================================================

class CollegeAssessmentSubmitView(APIView):
    """
    POST: Formally submits the assessment for evaluation.
    Verifies institutional ownership, parameter inputs presence, and locks assessment.
    """
    permission_classes = [IsAuthenticatedUser, IsCollegeAssessmentOwnerOrReviewer]

    @handle_college_exceptions
    def post(self, request, assessment_id):
        assessment = get_college_assessment_object(assessment_id)
        self.check_object_permissions(request, assessment)

        submitted_assessment = CollegeAssessmentService.submit_assessment(
            assessment_id=assessment.assessment_id,
            submitting_user=request.user,
        )

        return Response(CollegeAssessmentSerializer(submitted_assessment).data, status=status.HTTP_200_OK)


# ==============================================================================
# 7. COLLEGE REVIEW & CERTIFICATION WORKFLOW ENDPOINTS (PHASE 7C)
# ==============================================================================

class CollegeReviewQueueView(APIView):
    """
    GET: Retrieve screening committee review queue of College assessments.
    Excludes assessments with reviewer institutional conflict of interest.
    """
    permission_classes = [IsAuthenticatedUser, IsCommitteeReviewer]

    @handle_college_exceptions
    def get(self, request):
        qs = CollegeReviewService.get_review_queue(
            user=request.user,
            filters=request.query_params
        )
        paginator = CollegePagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            serializer = CollegeReviewQueueItemSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = CollegeReviewQueueItemSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CollegeAssessmentStartReviewView(APIView):
    """
    POST: Begins committee review on a submitted College assessment.
    Transitions lifecycle status: SUBMITTED -> UNDER_REVIEW.
    """
    permission_classes = [IsAuthenticatedUser, IsCommitteeReviewer]

    @handle_college_exceptions
    def post(self, request, assessment_id):
        assessment = get_college_assessment_object(assessment_id)
        self.check_object_permissions(request, assessment)

        serializer = CollegeReviewStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_assessment, review_rec = CollegeReviewService.start_review(
            assessment_id=assessment.assessment_id,
            reviewer=request.user,
            comments=serializer.validated_data.get("comments", "")
        )

        return Response({
            "assessment": CollegeAssessmentSerializer(updated_assessment).data,
            "review": CollegeReviewRecordSerializer(review_rec).data,
            "message": "Review started successfully."
        }, status=status.HTTP_200_OK)


class CollegeAssessmentReviewEvaluateView(APIView):
    """
    POST: Executes committee scoring evaluation via the frozen NEP2026ScoringEngine.
    Status remains UNDER_REVIEW; evaluation is captured in CollegeReviewRecord.
    Protected from direct client score injection.
    """
    permission_classes = [IsAuthenticatedUser, IsCommitteeReviewer]

    @handle_college_exceptions
    def post(self, request, assessment_id):
        assessment = get_college_assessment_object(assessment_id)
        self.check_object_permissions(request, assessment)

        # Anti-tampering: Reject client-supplied score in request body
        for field in FORBIDDEN_SCORE_FIELDS:
            if field in request.data:
                raise CollegeValidationError(
                    f"Client cannot supply score field '{field}'. Scoring is server-authoritative.",
                    code="INVALID_PARAMETER_INPUT"
                )

        updated_assessment, result, review_rec = CollegeReviewService.evaluate_assessment(
            assessment_id=assessment.assessment_id,
            actor=request.user,
        )

        return Response({
            "assessment": CollegeAssessmentSerializer(updated_assessment).data,
            "review": CollegeReviewRecordSerializer(review_rec).data,
            "scoring": {
                "calculation_id": result.calculation_id,
                "raw_total": result.raw_total,
                "evidence_gated_total": result.evidence_gated_total,
                "final_certified_total": result.final_certified_total,
                "max_marks": result.max_marks,
                "certification_status": result.certification_status.value if hasattr(result.certification_status, "value") else str(result.certification_status),
                "blocking_reasons": result.blocking_reasons,
            },
            "message": "Assessment scoring evaluated successfully by reviewer."
        }, status=status.HTTP_200_OK)


class CollegeAssessmentCompleteReviewView(APIView):
    """
    POST: Completes committee review after validating evidence readiness and scoring.
    Status remains UNDER_REVIEW; review completion is captured in CollegeReviewRecord.
    """
    permission_classes = [IsAuthenticatedUser, IsCommitteeReviewer]

    @handle_college_exceptions
    def post(self, request, assessment_id):
        assessment = get_college_assessment_object(assessment_id)
        self.check_object_permissions(request, assessment)

        serializer = CollegeReviewCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_assessment, review_rec = CollegeReviewService.complete_review(
            assessment_id=assessment.assessment_id,
            reviewer=request.user,
            comments=serializer.validated_data.get("comments", "")
        )

        return Response({
            "assessment": CollegeAssessmentSerializer(updated_assessment).data,
            "review": CollegeReviewRecordSerializer(review_rec).data,
            "message": "Committee review completed successfully."
        }, status=status.HTTP_200_OK)


class CollegeAssessmentReturnCorrectionView(APIView):
    """
    POST: Returns assessment to institution for correction with mandatory reason.
    Transitions lifecycle status to DRAFT (Phase 7A correction state).
    """
    permission_classes = [IsAuthenticatedUser, IsCommitteeReviewer]

    @handle_college_exceptions
    def post(self, request, assessment_id):
        assessment = get_college_assessment_object(assessment_id)
        self.check_object_permissions(request, assessment)

        serializer = CollegeReviewCorrectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_assessment, review_rec = CollegeReviewService.return_for_correction(
            assessment_id=assessment.assessment_id,
            reviewer=request.user,
            reason=serializer.validated_data["reason"],
            comments=serializer.validated_data.get("comments", "")
        )

        return Response({
            "assessment": CollegeAssessmentSerializer(updated_assessment).data,
            "review": CollegeReviewRecordSerializer(review_rec).data,
            "message": "Assessment returned for correction."
        }, status=status.HTTP_200_OK)


class CollegeAssessmentBlockReviewView(APIView):
    """
    POST: Blocks assessment review due to irremediable policy or statutory deficiencies.
    Transitions lifecycle status to REJECTED.
    """
    permission_classes = [IsAuthenticatedUser, IsCommitteeReviewer]

    @handle_college_exceptions
    def post(self, request, assessment_id):
        assessment = get_college_assessment_object(assessment_id)
        self.check_object_permissions(request, assessment)

        serializer = CollegeReviewBlockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_assessment, review_rec = CollegeReviewService.block_review(
            assessment_id=assessment.assessment_id,
            reviewer=request.user,
            reason=serializer.validated_data["reason"],
            comments=serializer.validated_data.get("comments", "")
        )

        return Response({
            "assessment": CollegeAssessmentSerializer(updated_assessment).data,
            "review": CollegeReviewRecordSerializer(review_rec).data,
            "message": "Assessment review blocked."
        }, status=status.HTTP_200_OK)


class CollegeAssessmentReviewHistoryView(APIView):
    """
    GET: Retrieve append-only history of review actions and committee evaluations.
    """
    permission_classes = [IsAuthenticatedUser, IsCollegeAssessmentOwnerOrReviewer]

    @handle_college_exceptions
    def get(self, request, assessment_id):
        assessment = get_college_assessment_object(assessment_id)
        self.check_object_permissions(request, assessment)

        reviews = CollegeReviewRecord.objects.filter(
            assessment=assessment
        ).select_related("reviewer").order_by("-created_at")

        serializer = CollegeReviewRecordSerializer(reviews, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CollegeAssessmentCertifyView(APIView):
    """
    POST: Formally certifies a College assessment.
    Verifies all 11 Statutory Gates and permanently locks the assessment.
    Restricted strictly to DHE Administrators, Superusers, and Screening Committee Chairs.
    """
    permission_classes = [IsAuthenticatedUser, IsCertificationAuthority]

    @handle_college_exceptions
    def post(self, request, assessment_id):
        assessment = get_college_assessment_object(assessment_id)
        self.check_object_permissions(request, assessment)

        serializer = CollegeCertifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        certified_assessment, review_rec = CollegeReviewService.certify_assessment(
            assessment_id=assessment.assessment_id,
            actor=request.user,
            remarks=serializer.validated_data.get("remarks", "")
        )

        return Response({
            "assessment": CollegeAssessmentSerializer(certified_assessment).data,
            "review": CollegeReviewRecordSerializer(review_rec).data,
            "message": "College assessment certified successfully and locked."
        }, status=status.HTTP_200_OK)
