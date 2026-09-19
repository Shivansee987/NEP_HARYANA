"""
NEP Excellence Awards 2026 - Admin Control Plane API Views (Phase 8)
Exposes administrative inspection, unified review queues, explicit reviewer assignment,
and domain certification delegation with strict anti-tampering and error handling.
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied

from apps.evidence.models import ReviewerAuthorization
from .api_permissions import (
    AdminPermissionDenied,
    FrameworkMismatchError,
    ReviewConflictError,
    IsAuthenticatedUser,
    IsControlPlaneAuthorized,
    IsAdminOrCommitteeChair,
    IsAdminOnly,
    IsControlPlaneCertificationAuthority,
)
from .api_serializers import (
    AdminCertifySerializer,
    AdminReviewQueueItemSerializer,
    ReviewerAssignmentSerializer,
    ReviewerAuthorizationCreateSerializer,
    ReviewerAuthorizationListSerializer,
)
from .services import (
    AdminControlPlaneService,
    AdminValidationError,
)


class AdminReviewQueueView(APIView):
    """
    GET /api/v1/admin/review-queue/
    GET /api/v1/admin/queue/
    Consolidated review queue across NEP 2026 frameworks (University & College).
    Strictly restricted to screening committee reviewers and administrators.
    Institutional users are denied with HTTP 403.
    """
    permission_classes = [IsAuthenticatedUser, IsControlPlaneAuthorized]

    def get(self, request):
        filters = {
            "framework": request.query_params.get("framework"),
            "status": request.query_params.get("status"),
            "institution": request.query_params.get("institution"),
            "academic_year": request.query_params.get("academic_year"),
            "assigned_reviewer": request.query_params.get("assigned_reviewer"),
            "readiness": request.query_params.get("readiness"),
            "specification_blocked": request.query_params.get("specification_blocked"),
        }
        # Clean out None values
        filters = {k: v for k, v in filters.items() if v is not None}

        try:
            items = AdminControlPlaneService.get_unified_queue(request.user, filters=filters)
            serializer = AdminReviewQueueItemSerializer(items, many=True)
            return Response(
                {
                    "count": len(items),
                    "results": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except FrameworkMismatchError as e:
            return Response(
                {"error": "FRAMEWORK_MISMATCH", "detail": str(e)},
                status=status.HTTP_403_FORBIDDEN,
            )
        except AdminPermissionDenied as e:
            return Response(
                {"error": getattr(e, "code", "PERMISSION_DENIED"), "detail": str(e)},
                status=status.HTTP_403_FORBIDDEN,
            )


class AdminAssessmentInspectView(APIView):
    """
    GET /api/v1/admin/assessments/<assessment_id>/inspect/
    Safe, read-only administrative inspection of an assessment across frameworks.
    Enforces tenancy and framework access boundaries. Zero state mutation.
    """
    permission_classes = [IsAuthenticatedUser]

    def get(self, request, assessment_id):
        try:
            inspection_data = AdminControlPlaneService.inspect_assessment(
                assessment_id=assessment_id, user=request.user
            )
            return Response(inspection_data, status=status.HTTP_200_OK)
        except AdminValidationError as e:
            code = getattr(e, "code", "VALIDATION_ERROR")
            http_status = status.HTTP_404_NOT_FOUND if code == "ASSESSMENT_NOT_FOUND" else status.HTTP_400_BAD_REQUEST
            return Response({"error": code, "detail": str(e)}, status=http_status)
        except (AdminPermissionDenied, FrameworkMismatchError, ReviewConflictError) as e:
            code = getattr(e, "code", "PERMISSION_DENIED")
            return Response({"error": code, "detail": str(e)}, status=status.HTTP_403_FORBIDDEN)


class AdminAssessmentAssignReviewerView(APIView):
    """
    POST /api/v1/admin/assessments/<assessment_id>/assign/
    Explicit, auditable assignment or reassignment of a reviewer to an assessment.
    Restricted to Committee Chairs and Administrators.
    Reassignment requires a mandatory non-empty reason.
    Strictly rejects any client-supplied score keys.
    """
    permission_classes = [IsAuthenticatedUser, IsAdminOrCommitteeChair]

    def post(self, request, assessment_id):
        serializer = ReviewerAssignmentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        reviewer_id = serializer.validated_data["reviewer_id"]
        reason = serializer.validated_data.get("reason", "")

        try:
            assessment, assigned_user = AdminControlPlaneService.assign_reviewer(
                assessment_id=assessment_id,
                reviewer_id=reviewer_id,
                actor=request.user,
                reason=reason,
            )
            return Response(
                {
                    "message": "Reviewer assigned successfully.",
                    "assessment_id": assessment.assessment_id,
                    "framework": assessment.framework,
                    "assigned_reviewer": {
                        "id": assigned_user.pk,
                        "email": assigned_user.email,
                        "full_name": assigned_user.full_name,
                        "role": getattr(assigned_user, "role", ""),
                    },
                },
                status=status.HTTP_200_OK,
            )
        except AdminValidationError as e:
            code = getattr(e, "code", "VALIDATION_ERROR")
            http_status = status.HTTP_404_NOT_FOUND if code == "ASSESSMENT_NOT_FOUND" else status.HTTP_400_BAD_REQUEST
            return Response({"error": code, "detail": str(e)}, status=http_status)
        except (AdminPermissionDenied, ReviewConflictError, FrameworkMismatchError) as e:
            code = getattr(e, "code", "PERMISSION_DENIED")
            return Response({"error": code, "detail": str(e)}, status=status.HTTP_403_FORBIDDEN)


class AdminAssessmentCertifyView(APIView):
    """
    POST /api/v1/admin/assessments/<assessment_id>/certify/
    Delegates assessment certification to the respective domain service.
    Restricted to Committee Chairs, DHE Admins, and Superusers.
    Strictly rejects score injection payloads and evaluates all 11 certification gates.
    """
    permission_classes = [IsAuthenticatedUser, IsControlPlaneCertificationAuthority]

    def post(self, request, assessment_id):
        serializer = AdminCertifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        comments = serializer.validated_data.get("comments", "")

        try:
            assessment, review_rec = AdminControlPlaneService.certify_assessment(
                assessment_id=assessment_id,
                actor=request.user,
                comments=comments,
            )
            return Response(
                {
                    "message": "Assessment certified successfully.",
                    "assessment_id": assessment.assessment_id,
                    "framework": assessment.framework,
                    "status": assessment.status,
                    "certified_score": assessment.certified_score,
                    "certification_status": getattr(assessment, "certification_status", "FINALIZABLE"),
                    "certified_at": getattr(review_rec, "created_at", None),
                },
                status=status.HTTP_200_OK,
            )
        except AdminValidationError as e:
            code = getattr(e, "code", "VALIDATION_ERROR")
            http_status = status.HTTP_404_NOT_FOUND if code == "ASSESSMENT_NOT_FOUND" else status.HTTP_400_BAD_REQUEST
            return Response({"error": code, "detail": str(e)}, status=http_status)
        except (AdminPermissionDenied, ReviewConflictError, FrameworkMismatchError) as e:
            code = getattr(e, "code", "PERMISSION_DENIED")
            return Response({"error": code, "detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            # Domain certification errors (e.g. EvidenceNotReadyError, CertificationBlockedByEngineError)
            err_cls = e.__class__.__name__
            if "NotAuthorized" in err_cls or "Conflict" in err_cls:
                return Response({"error": err_cls, "detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
            return Response({"error": err_cls, "detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminReviewerAuthorizationsView(APIView):
    """
    GET /api/v1/admin/authorizations/
    POST /api/v1/admin/authorizations/
    Lists and grants ReviewerAuthorization bindings.
    Restricted strictly to Platform Administrators.
    """
    permission_classes = [IsAuthenticatedUser, IsAdminOnly]

    def get(self, request):
        auths = ReviewerAuthorization.objects.select_related("user", "granted_by").order_by("-created_at")
        serializer = ReviewerAuthorizationListSerializer(auths, many=True)
        return Response({"count": auths.count(), "results": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ReviewerAuthorizationCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        from apps.authentication.models import User
        target_user = User.objects.get(pk=serializer.validated_data["user_id"])
        framework = serializer.validated_data["framework"]
        institution_id = serializer.validated_data.get("institution_id", "")
        is_active = serializer.validated_data.get("is_active", True)

        auth_record = ReviewerAuthorization.objects.create(
            user=target_user,
            framework=framework,
            institution_id=institution_id,
            is_active=is_active,
            granted_by=request.user,
        )

        return Response(
            ReviewerAuthorizationListSerializer(auth_record).data,
            status=status.HTTP_201_CREATED,
        )
