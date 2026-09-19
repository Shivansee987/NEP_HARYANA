"""
NEP Excellence Awards 2026 - University REST API Views
Production-ready API endpoints exposing the complete University assessment workflow.
Business logic is preserved in domain services; views act as clean HTTP adapters.
"""
from functools import wraps
from typing import Any, Dict
from rest_framework import status
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers

from apps.scoring.domain import ReviewerAdjustment
from apps.university.models import University, UniversityAssessment, UniversityReviewRecord
from apps.university.registry import (
    UNIVERSITY_FRAMEWORK_CODE,
    get_university_parameter,
    get_university_parameters,
    validate_university_parameter_code,
)
from apps.university.services import UniversityAssessmentService, UniversityReviewService
from apps.university.validators import (
    AssessmentAlreadyCertifiedError,
    AssessmentLockedError,
    AssessmentNotReadyError,
    CertificationBlockedError,
    CertificationNotAuthorizedError,
    ConcurrentReviewConflictError,
    ConcurrentUpdateError,
    EvidenceNotReadyError,
    FrameworkMismatchError,
    InvalidReviewStateError,
    InvalidStateTransitionError,
    ReviewConflictError,
    ReviewNotAuthorizedError,
    ScoringBlockedError,
    ScoringNotEvaluatedError,
    UniversityNotAuthorizedError,
    UniversityValidationError,
    validate_parameter,
)
from .permissions import (
    AssessmentPermissionDenied,
    IsAuthenticatedUser,
    IsCertificationAuthority,
    IsCommitteeOrAdminForEvaluation,
    IsCommitteeReviewer,
    IsUniversityAdminOrOwner,
    IsUniversityAssessmentOwnerOrReviewer,
    UniversityPermissionDenied,
)
from .serializers import (
    UniversityAssessmentCreateSerializer,
    UniversityAssessmentSerializer,
    UniversityCertifySerializer,
    UniversityParameterInputSerializer,
    UniversityParameterMetadataSerializer,
    UniversityReviewBlockSerializer,
    UniversityReviewCompleteSerializer,
    UniversityReviewCorrectionSerializer,
    UniversityReviewQueueItemSerializer,
    UniversityReviewRecordSerializer,
    UniversityReviewStartSerializer,
    UniversitySerializer,
)


class UniversityPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


def get_university_object(pk_or_aishe: str) -> University:
    try:
        if str(pk_or_aishe).isdigit():
            return University.objects.get(pk=int(pk_or_aishe))
        return University.objects.get(aishe_code=str(pk_or_aishe))
    except University.DoesNotExist:
        raise UniversityValidationError(f"University '{pk_or_aishe}' not found.", code="NOT_FOUND")


def get_university_assessment_object(pk_or_id: str) -> UniversityAssessment:
    try:
        if str(pk_or_id).isdigit():
            return UniversityAssessment.objects.select_related('university').get(pk=int(pk_or_id))
        return UniversityAssessment.objects.select_related('university').get(assessment_id=str(pk_or_id))
    except UniversityAssessment.DoesNotExist:
        raise UniversityValidationError(f"Assessment '{pk_or_id}' not found.", code="NOT_FOUND")


def handle_university_exceptions(view_method):
    """
    Standardizes domain exception mapping to clean REST HTTP error responses.
    Prevents leaking internal stack traces or database structures.
    """
    @wraps(view_method)
    def wrapper(self, request, *args, **kwargs):
        try:
            return view_method(self, request, *args, **kwargs)
        except NotAuthenticated as exc:
            return Response(
                {"error": "unauthenticated", "code": "UNAUTHENTICATED", "detail": str(exc)},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except (UniversityPermissionDenied, AssessmentPermissionDenied, PermissionDenied) as exc:
            code = getattr(exc, "code", None)
            if not code and hasattr(exc, "detail") and hasattr(exc.detail, "code"):
                code = str(exc.detail.code).upper()
            code = code or "FORBIDDEN"
            return Response(
                {"error": "forbidden", "code": code, "detail": str(exc.detail if hasattr(exc, 'detail') else exc)},
                status=status.HTTP_403_FORBIDDEN
            )
        except (ReviewNotAuthorizedError, CertificationNotAuthorizedError, ReviewConflictError, AssessmentLockedError) as exc:
            return Response(
                {"error": "forbidden", "code": exc.code, "detail": exc.message},
                status=status.HTTP_403_FORBIDDEN
            )
        except (ConcurrentReviewConflictError, ConcurrentUpdateError, InvalidStateTransitionError) as exc:
            return Response(
                {"error": "conflict", "code": exc.code, "detail": exc.message},
                status=status.HTTP_409_CONFLICT
            )
        except InvalidReviewStateError as exc:
            return Response(
                {"error": "bad_request", "code": exc.code, "detail": exc.message},
                status=status.HTTP_400_BAD_REQUEST
            )
        except (AssessmentAlreadyCertifiedError, CertificationBlockedError, ScoringNotEvaluatedError, ScoringBlockedError, EvidenceNotReadyError, AssessmentNotReadyError, FrameworkMismatchError) as exc:
            return Response(
                {"error": "bad_request", "code": exc.code, "detail": exc.message},
                status=status.HTTP_400_BAD_REQUEST
            )
        except UniversityNotAuthorizedError as exc:
            return Response(
                {"error": "forbidden", "code": exc.code, "detail": exc.message},
                status=status.HTTP_403_FORBIDDEN
            )
        except UniversityValidationError as exc:
            if exc.code == "NOT_FOUND":
                return Response(
                    {"error": "not_found", "code": "NOT_FOUND", "detail": exc.message},
                    status=status.HTTP_404_NOT_FOUND
                )
            return Response(
                {"error": "bad_request", "code": exc.code, "detail": exc.message},
                status=status.HTTP_400_BAD_REQUEST
            )
        except serializers.ValidationError as exc:
            detail = exc.detail
            code = "INVALID_PARAMETER_INPUT"
            # Extract code if present
            if isinstance(detail, dict):
                for k, v in detail.items():
                    if k in ("framework",):
                        code = "INVALID_FRAMEWORK"
                    elif k in ("period_start", "period_end"):
                        code = "INVALID_ASSESSMENT_PERIOD"
                    elif k in ("parameter_code", "parameter"):
                        code = "INVALID_PARAMETER"
                    elif isinstance(v, list) and len(v) > 0 and hasattr(v[0], 'code'):
                        code = str(v[0].code).upper()
            elif isinstance(detail, list) and len(detail) > 0 and hasattr(detail[0], 'code'):
                code = str(detail[0].code).upper()
            return Response(
                {"error": "bad_request", "code": code, "detail": detail},
                status=status.HTTP_400_BAD_REQUEST
            )
        except KeyError as exc:
            return Response(
                {"error": "bad_request", "code": "INVALID_PARAMETER", "detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )
    return wrapper


class UniversityListCreateView(APIView):
    """
    GET: List authorized Universities (supports pagination).
    POST: Register a new University (Administrators only).
    """
    permission_classes = [IsAuthenticatedUser, IsUniversityAdminOrOwner]
    pagination_class = UniversityPagination

    @handle_university_exceptions
    def get(self, request):
        user = request.user
        role = getattr(user, 'role', '')

        qs = University.objects.filter(is_active=True).order_by('name')

        # Institutional scoping
        if not (getattr(user, 'is_superuser', False) or role in ('admin', 'state_admin', 'committee')):
            user_uni = getattr(user, 'university', None)
            if user_uni:
                qs = qs.filter(pk=user_uni.pk)
            else:
                qs = qs.none()

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            serializer = UniversitySerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = UniversitySerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @handle_university_exceptions
    def post(self, request):
        serializer = UniversitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uni = serializer.save()
        return Response(UniversitySerializer(uni).data, status=status.HTTP_201_CREATED)


class UniversityDetailView(APIView):
    """
    GET: Retrieve University metadata by ID or AISHE code.
    """
    permission_classes = [IsAuthenticatedUser, IsUniversityAdminOrOwner]

    @handle_university_exceptions
    def get(self, request, pk):
        uni = get_university_object(pk)
        self.check_object_permissions(request, uni)
        return Response(UniversitySerializer(uni).data, status=status.HTTP_200_OK)


class UniversityAssessmentListCreateView(APIView):
    """
    GET: List assessments for a specific University.
    POST: Create a new assessment session for a specific University.
    """
    permission_classes = [IsAuthenticatedUser, IsUniversityAssessmentOwnerOrReviewer]
    pagination_class = UniversityPagination

    @handle_university_exceptions
    def get(self, request, pk):
        uni = get_university_object(pk)
        # Verify ownership / permissions for this university
        self.check_object_permissions(request, UniversityAssessment(university=uni))

        qs = UniversityAssessment.objects.filter(university=uni).order_by('-created_at')
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            serializer = UniversityAssessmentSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = UniversityAssessmentSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @handle_university_exceptions
    def post(self, request, pk):
        uni = get_university_object(pk)
        # Reviewers cannot create assessments
        if getattr(request.user, 'role', '') == 'committee':
            raise AssessmentPermissionDenied(
                "Reviewers are not permitted to create University assessments.",
                code="ASSESSMENT_NOT_AUTHORIZED"
            )

        # Enforce institutional ownership
        self.check_object_permissions(request, UniversityAssessment(university=uni))

        serializer = UniversityAssessmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        valid_data = serializer.validated_data

        assessment = UniversityAssessmentService.create_assessment(
            university_id=uni,
            assessment_id=valid_data.get('assessment_id'),
            academic_year=valid_data.get('academic_year', '2025-26'),
            created_by=request.user,
        )

        resp_serializer = UniversityAssessmentSerializer(assessment)
        return Response(resp_serializer.data, status=status.HTTP_201_CREATED)


class UniversityAssessmentDetailView(APIView):
    """
    GET: Retrieve UniversityAssessment session details.
    PATCH: Update non-sensitive assessment metadata or transition status.
    """
    permission_classes = [IsAuthenticatedUser, IsUniversityAssessmentOwnerOrReviewer]

    @handle_university_exceptions
    def get(self, request, assessment_id):
        assessment = get_university_assessment_object(assessment_id)
        self.check_object_permissions(request, assessment)
        return Response(UniversityAssessmentSerializer(assessment).data, status=status.HTTP_200_OK)

    @handle_university_exceptions
    def patch(self, request, assessment_id):
        assessment = get_university_assessment_object(assessment_id)
        self.check_object_permissions(request, assessment)

        # Reject client-supplied scores immediately
        for field in ("score", "earned_score", "earned_marks", "total", "certified_score", "reviewer_score"):
            if field in request.data:
                raise UniversityValidationError(
                    f"Client cannot supply or modify score field '{field}'.",
                    code="INVALID_PARAMETER_INPUT"
                )

        # If status transition requested
        if "status" in request.data:
            new_status = request.data["status"]
            assessment = UniversityAssessmentService.transition_status(
                assessment_id=assessment.assessment_id,
                target_status=new_status,
                actor=request.user,
            )

        # Handle other non-sensitive fields
        if "academic_year" in request.data:
            if assessment.status != "DRAFT":
                raise InvalidStateTransitionError(
                    "Cannot modify academic year of a non-draft assessment."
                )
            assessment.academic_year = request.data["academic_year"]
            assessment.save(update_fields=["academic_year", "updated_at"])

        return Response(UniversityAssessmentSerializer(assessment).data, status=status.HTTP_200_OK)


class UniversityAssessmentParametersListView(APIView):
    """
    GET: Authoritative metadata and current submitted state for all U1–U20 parameters.
    """
    permission_classes = [IsAuthenticatedUser, IsUniversityAssessmentOwnerOrReviewer]

    @handle_university_exceptions
    def get(self, request, assessment_id):
        assessment = get_university_assessment_object(assessment_id)
        self.check_object_permissions(request, assessment)

        registered = get_university_parameters()
        param_data = assessment.parameter_data or {}

        results = []
        for code, conf in registered.items():
            results.append({
                "code": code,
                "title": conf.get("title", ""),
                "max_marks": conf.get("max_marks", 0.0),
                "subcriteria": conf.get("subcriteria", {}),
                "period_rule": conf.get("period_rule", ""),
                "mandatory_evidence": conf.get("mandatory_evidence", []),
                "allowed_evidence": conf.get("allowed_evidence", []),
                "double_counting_rule": conf.get("double_counting_rule", ""),
                "submitted_input": param_data.get(code, None),
            })

        serializer = UniversityParameterMetadataSerializer(results, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UniversityAssessmentParameterDetailView(APIView):
    """
    GET: Authoritative metadata and submitted input state for parameter U1–U20.
    PUT/PATCH: Update parameter input data. Strictly passes Phase 6A validators.
    """
    permission_classes = [IsAuthenticatedUser, IsUniversityAssessmentOwnerOrReviewer]

    @handle_university_exceptions
    def get(self, request, assessment_id, parameter_code):
        param_clean = validate_parameter(parameter_code)
        assessment = get_university_assessment_object(assessment_id)
        self.check_object_permissions(request, assessment)

        conf = get_university_parameter(param_clean)
        submitted = (assessment.parameter_data or {}).get(param_clean, None)

        data = {
            "code": param_clean,
            "title": conf.get("title", ""),
            "max_marks": conf.get("max_marks", 0.0),
            "subcriteria": conf.get("subcriteria", {}),
            "period_rule": conf.get("period_rule", ""),
            "mandatory_evidence": conf.get("mandatory_evidence", []),
            "allowed_evidence": conf.get("allowed_evidence", []),
            "double_counting_rule": conf.get("double_counting_rule", ""),
            "submitted_input": submitted,
        }
        serializer = UniversityParameterMetadataSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @handle_university_exceptions
    def put(self, request, assessment_id, parameter_code):
        return self._update_parameter(request, assessment_id, parameter_code)

    @handle_university_exceptions
    def patch(self, request, assessment_id, parameter_code):
        return self._update_parameter(request, assessment_id, parameter_code)

    def _update_parameter(self, request, assessment_id, parameter_code):
        param_clean = validate_parameter(parameter_code)
        assessment = get_university_assessment_object(assessment_id)
        self.check_object_permissions(request, assessment)

        serializer = UniversityParameterInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validate_with_parameter(param_clean)

        updated_assessment = UniversityAssessmentService.update_parameter_inputs(
            assessment_id=assessment.assessment_id,
            parameter_code=param_clean,
            raw_inputs=validated_data.get('raw_inputs', {}),
            entities=validated_data.get('entities', []),
            activity_date=validated_data.get('activity_date'),
        )

        submitted_data = updated_assessment.parameter_data.get(param_clean)
        conf = get_university_parameter(param_clean)
        resp_data = {
            "code": param_clean,
            "title": conf.get("title", ""),
            "max_marks": conf.get("max_marks", 0.0),
            "subcriteria": conf.get("subcriteria", {}),
            "period_rule": conf.get("period_rule", ""),
            "mandatory_evidence": conf.get("mandatory_evidence", []),
            "allowed_evidence": conf.get("allowed_evidence", []),
            "double_counting_rule": conf.get("double_counting_rule", ""),
            "submitted_input": submitted_data,
        }
        return Response(resp_data, status=status.HTTP_200_OK)


class UniversityAssessmentCoverageView(APIView):
    """
    GET: Evaluates evidence coverage across all 44 University subcriteria via Phase 5D.
    Does NOT calculate marks.
    """
    permission_classes = [IsAuthenticatedUser, IsUniversityAssessmentOwnerOrReviewer]

    @handle_university_exceptions
    def get(self, request, assessment_id):
        assessment = get_university_assessment_object(assessment_id)
        self.check_object_permissions(request, assessment)

        report = UniversityAssessmentService.evaluate_assessment_coverage(
            assessment_id=assessment.assessment_id,
            user=request.user,
        )
        return Response(report.to_dict(), status=status.HTTP_200_OK)


class UniversityAssessmentReadinessView(APIView):
    """
    GET: Evaluates evidence readiness via Phase 5D readiness service.
    Clearly distinguishes evidence readiness from scoring results.
    """
    permission_classes = [IsAuthenticatedUser, IsUniversityAssessmentOwnerOrReviewer]

    @handle_university_exceptions
    def get(self, request, assessment_id):
        assessment = get_university_assessment_object(assessment_id)
        self.check_object_permissions(request, assessment)

        is_ready, blocking_reasons, summary = UniversityAssessmentService.check_assessment_readiness(
            assessment_id=assessment.assessment_id,
            user=request.user,
        )

        return Response({
            "assessment_id": assessment.assessment_id,
            "framework": UNIVERSITY_FRAMEWORK_CODE,
            "is_ready": is_ready,
            "blocking_reasons": blocking_reasons,
            "evidence_readiness_summary": summary.to_dict(),
        }, status=status.HTTP_200_OK)


class UniversityAssessmentEvaluateView(APIView):
    """
    POST: Executes scoring exclusively via frozen NEP2026ScoringEngine.
    Protected from direct client score injection.
    Requires committee reviewer or administrator privileges.
    """
    permission_classes = [
        IsAuthenticatedUser,
        IsUniversityAssessmentOwnerOrReviewer,
        IsCommitteeOrAdminForEvaluation,
    ]

    @handle_university_exceptions
    def post(self, request, assessment_id):
        assessment = get_university_assessment_object(assessment_id)
        self.check_object_permissions(request, assessment)

        # Reject any client-supplied score in request body
        for field in ("score", "earned_score", "total", "certified_score", "reviewer_score"):
            if field in request.data:
                raise UniversityValidationError(
                    f"Client cannot supply score field '{field}'. Scoring is server-authoritative.",
                    code="INVALID_PARAMETER_INPUT"
                )

        # Parse optional reviewer adjustments
        raw_adjustments = request.data.get("reviewer_adjustments", [])
        reviewer_adjustments = []
        for adj in raw_adjustments:
            reviewer_adjustments.append(ReviewerAdjustment(
                parameter_code=adj.get("parameter_code", ""),
                subcriterion_code=adj.get("subcriterion_code", ""),
                adjustment_marks=float(adj.get("adjustment_marks", 0.0)),
                reason=adj.get("reason", ""),
                reviewer_id=str(request.user.pk),
            ))

        # Delegate exclusively to frozen scoring engine via service layer
        result = UniversityAssessmentService.evaluate_assessment_scoring(
            assessment_id=assessment.assessment_id,
            reviewer_adjustments=reviewer_adjustments if reviewer_adjustments else None,
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


class UniversityAssessmentSubmitView(APIView):
    """
    POST: Formally submits the assessment for evaluation.
    Verifies institutional ownership, parameter inputs presence, and evidence readiness.
    """
    permission_classes = [IsAuthenticatedUser, IsUniversityAssessmentOwnerOrReviewer]

    @handle_university_exceptions
    def post(self, request, assessment_id):
        assessment = get_university_assessment_object(assessment_id)
        self.check_object_permissions(request, assessment)

        submitted_assessment = UniversityAssessmentService.submit_assessment(
            assessment_id=assessment.assessment_id,
            submitting_user=request.user,
        )

        return Response(
            UniversityAssessmentSerializer(submitted_assessment).data,
            status=status.HTTP_200_OK
        )


class UniversityReviewQueueView(APIView):
    """
    GET: Retrieve screening committee review queue of University assessments.
    Excludes assessments with reviewer institutional conflict of interest.
    """
    permission_classes = [IsAuthenticatedUser, IsCommitteeReviewer]

    @handle_university_exceptions
    def get(self, request):
        qs = UniversityReviewService.get_review_queue(
            user=request.user,
            filters=request.query_params
        )
        paginator = UniversityPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            serializer = UniversityReviewQueueItemSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = UniversityReviewQueueItemSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UniversityAssessmentStartReviewView(APIView):
    """
    POST: Begins committee review on a submitted assessment.
    Transitions lifecycle status: SUBMITTED/RETURNED -> UNDER_REVIEW.
    """
    permission_classes = [IsAuthenticatedUser, IsCommitteeReviewer]

    @handle_university_exceptions
    def post(self, request, assessment_id):
        assessment = get_university_assessment_object(assessment_id)
        self.check_object_permissions(request, assessment)

        serializer = UniversityReviewStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_assessment, review_rec = UniversityReviewService.start_review(
            assessment_id=assessment.assessment_id,
            reviewer=request.user,
            comments=serializer.validated_data.get("comments", "")
        )

        return Response({
            "assessment": UniversityAssessmentSerializer(updated_assessment).data,
            "review": UniversityReviewRecordSerializer(review_rec).data,
            "message": "Review started successfully."
        }, status=status.HTTP_200_OK)


class UniversityAssessmentCompleteReviewView(APIView):
    """
    POST: Completes committee review after validating evidence readiness and scoring.
    Transitions lifecycle status: UNDER_REVIEW/EVALUATED -> CERTIFICATION_PENDING.
    """
    permission_classes = [IsAuthenticatedUser, IsCommitteeReviewer]

    @handle_university_exceptions
    def post(self, request, assessment_id):
        assessment = get_university_assessment_object(assessment_id)
        self.check_object_permissions(request, assessment)

        serializer = UniversityReviewCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_assessment, review_rec = UniversityReviewService.complete_review(
            assessment_id=assessment.assessment_id,
            reviewer=request.user,
            comments=serializer.validated_data.get("comments", "")
        )

        return Response({
            "assessment": UniversityAssessmentSerializer(updated_assessment).data,
            "review": UniversityReviewRecordSerializer(review_rec).data,
            "message": "Committee review completed successfully."
        }, status=status.HTTP_200_OK)


class UniversityAssessmentReturnCorrectionView(APIView):
    """
    POST: Returns assessment to institution for correction with mandatory reason.
    Transitions lifecycle status to RETURNED.
    """
    permission_classes = [IsAuthenticatedUser, IsCommitteeReviewer]

    @handle_university_exceptions
    def post(self, request, assessment_id):
        assessment = get_university_assessment_object(assessment_id)
        self.check_object_permissions(request, assessment)

        serializer = UniversityReviewCorrectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_assessment, review_rec = UniversityReviewService.return_for_correction(
            assessment_id=assessment.assessment_id,
            reviewer=request.user,
            reason=serializer.validated_data["reason"],
            comments=serializer.validated_data.get("comments", "")
        )

        return Response({
            "assessment": UniversityAssessmentSerializer(updated_assessment).data,
            "review": UniversityReviewRecordSerializer(review_rec).data,
            "message": "Assessment returned for correction."
        }, status=status.HTTP_200_OK)


class UniversityAssessmentBlockReviewView(APIView):
    """
    POST: Blocks assessment review due to irremediable policy or statutory deficiencies.
    Transitions lifecycle status to BLOCKED.
    """
    permission_classes = [IsAuthenticatedUser, IsCommitteeReviewer]

    @handle_university_exceptions
    def post(self, request, assessment_id):
        assessment = get_university_assessment_object(assessment_id)
        self.check_object_permissions(request, assessment)

        serializer = UniversityReviewBlockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_assessment, review_rec = UniversityReviewService.block_review(
            assessment_id=assessment.assessment_id,
            reviewer=request.user,
            reason=serializer.validated_data["reason"],
            comments=serializer.validated_data.get("comments", "")
        )

        return Response({
            "assessment": UniversityAssessmentSerializer(updated_assessment).data,
            "review": UniversityReviewRecordSerializer(review_rec).data,
            "message": "Assessment review blocked."
        }, status=status.HTTP_200_OK)


class UniversityAssessmentReviewHistoryView(APIView):
    """
    GET: Retrieve append-only history of review actions and committee evaluations.
    """
    permission_classes = [IsAuthenticatedUser, IsUniversityAssessmentOwnerOrReviewer]

    @handle_university_exceptions
    def get(self, request, assessment_id):
        assessment = get_university_assessment_object(assessment_id)
        self.check_object_permissions(request, assessment)

        reviews = UniversityReviewRecord.objects.filter(
            assessment=assessment
        ).select_related("reviewer").order_by("-created_at")

        serializer = UniversityReviewRecordSerializer(reviews, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UniversityAssessmentCertifyView(APIView):
    """
    POST: Formally certifies a University assessment.
    Verifies all 11 Statutory Gates and permanently locks the assessment.
    Restricted strictly to DHE Administrators, Superusers, and Screening Committee Chairs.
    """
    permission_classes = [IsAuthenticatedUser, IsCertificationAuthority]

    @handle_university_exceptions
    def post(self, request, assessment_id):
        assessment = get_university_assessment_object(assessment_id)
        self.check_object_permissions(request, assessment)

        serializer = UniversityCertifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        certified_assessment, review_rec = UniversityReviewService.certify_assessment(
            assessment_id=assessment.assessment_id,
            actor=request.user,
            remarks=serializer.validated_data.get("remarks", "")
        )

        return Response({
            "assessment": UniversityAssessmentSerializer(certified_assessment).data,
            "review": UniversityReviewRecordSerializer(review_rec).data,
            "message": "University assessment certified successfully and locked."
        }, status=status.HTTP_200_OK)

