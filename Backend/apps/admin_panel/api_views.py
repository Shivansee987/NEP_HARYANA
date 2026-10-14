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
    IsHeadAdminOnly,
    IsAnyAdminUserManagement,
    IsControlPlaneCertificationAuthority,
)
from .api_serializers import (
    AdminCertifySerializer,
    AdminReviewQueueItemSerializer,
    ReviewerAssignmentSerializer,
    ReviewerAuthorizationCreateSerializer,
    ReviewerAuthorizationListSerializer,
    AdminUserListSerializer,
    AdminUserDetailSerializer,
    AdminUserCreateSerializer,
    AdminUserUpdateSerializer,
    UserAuditLogSerializer,
)
from .services import (
    AdminControlPlaneService,
    AdminUserManagementService,
    AdminValidationError,
    HeadAdminControlCentreService,
    StateOverviewService,
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


class AdminStateInstitutionsView(APIView):
    """
    GET /api/v1/admin/institutions/
    State Admin overview: every University and College with its latest assessment stage, score and reviewer,
    state totals, committee workload and recent audit activity. Read-only, so the Council Admin Overseer
    may view it as well.
    """
    permission_classes = [IsAuthenticatedUser, IsAnyAdminUserManagement]

    def get(self, request):
        return Response(StateOverviewService.build(), status=status.HTTP_200_OK)


class AdminUserListCreateView(APIView):
    """
    GET  /api/v1/admin/users/ - List, search, filter users across the platform.
    POST /api/v1/admin/users/ - Create or invite authorized users.
    Only Head Admin can create privileged accounts (head_admin, sub_admin, committee, etc.).
    """
    permission_classes = [IsAuthenticatedUser, IsAnyAdminUserManagement]

    def get(self, request):
        filters = {
            "q": request.query_params.get("q") or request.query_params.get("search"),
            "role": request.query_params.get("role"),
            "is_active": request.query_params.get("is_active") or request.query_params.get("status"),
            "institution_type": request.query_params.get("institution_type") or request.query_params.get("type"),
            "institution_id": request.query_params.get("institution_id") or request.query_params.get("aishe_code"),
            "ordering": request.query_params.get("ordering", "-id"),
            "institution_status": request.query_params.get("institution_status"),
        }
        filters = {k: v for k, v in filters.items() if v is not None}
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))

        result = AdminUserManagementService.list_users(
            actor=request.user,
            filters=filters,
            page=page,
            page_size=page_size,
        )
        serializer = AdminUserListSerializer(result["users"], many=True)
        return Response({
            "count": result["count"],
            "page": result["page"],
            "page_size": result["page_size"],
            "total_pages": result["total_pages"],
            "results": serializer.data,
        }, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = AdminUserCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        ip = request.META.get("HTTP_X_FORWARDED_FOR") or request.META.get("REMOTE_ADDR")
        if ip and "," in ip:
            ip = ip.split(",")[0].strip()

        try:
            new_user = AdminUserManagementService.create_user(
                actor=request.user,
                validated_data=serializer.validated_data,
                ip_address=ip,
            )
            response_data = AdminUserDetailSerializer(new_user).data
            # The activation link is only ever delivered by e-mail; report whether that actually happened.
            email_sent = bool(getattr(new_user, "_invitation_email_sent", False))
            response_data["invitation_email_sent"] = email_sent
            response_data["credential_status"] = "INVITATION_SENT" if email_sent else "INVITATION_PENDING_DISPATCH"
            return Response(response_data, status=status.HTTP_201_CREATED)
        except AdminPermissionDenied as e:
            return Response({"error": getattr(e, "code", "PERMISSION_DENIED"), "detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except AdminValidationError as e:
            return Response({"error": getattr(e, "code", "VALIDATION_ERROR"), "detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminUserDetailView(APIView):
    """
    GET   /api/v1/admin/users/<user_id>/ - View user details, institution, and recent audit trail.
    PATCH /api/v1/admin/users/<user_id>/ - Update user role, status, or details with Head Admin checks.
    """
    permission_classes = [IsAuthenticatedUser, IsAnyAdminUserManagement]

    def get(self, request, user_id):
        try:
            target_user, audit_logs = AdminUserManagementService.get_user_detail(
                actor=request.user,
                user_id=user_id,
            )
            data = AdminUserDetailSerializer(target_user).data
            return Response(data, status=status.HTTP_200_OK)
        except AdminPermissionDenied as e:
            return Response({"error": getattr(e, "code", "PERMISSION_DENIED"), "detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except AdminValidationError as e:
            code = getattr(e, "code", "VALIDATION_ERROR")
            http_status = status.HTTP_404_NOT_FOUND if code == "USER_NOT_FOUND" else status.HTTP_400_BAD_REQUEST
            return Response({"error": code, "detail": str(e)}, status=http_status)

    def patch(self, request, user_id):
        serializer = AdminUserUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        ip = request.META.get("HTTP_X_FORWARDED_FOR") or request.META.get("REMOTE_ADDR")
        if ip and "," in ip:
            ip = ip.split(",")[0].strip()

        try:
            updated_user = AdminUserManagementService.update_user(
                actor=request.user,
                user_id=user_id,
                validated_data=serializer.validated_data,
                ip_address=ip,
            )
            return Response(AdminUserDetailSerializer(updated_user).data, status=status.HTTP_200_OK)
        except AdminPermissionDenied as e:
            return Response({"error": getattr(e, "code", "PERMISSION_DENIED"), "detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except AdminValidationError as e:
            code = getattr(e, "code", "VALIDATION_ERROR")
            http_status = status.HTTP_404_NOT_FOUND if code == "USER_NOT_FOUND" else status.HTTP_400_BAD_REQUEST
            return Response({"error": code, "detail": str(e)}, status=http_status)

    def delete(self, request, user_id):
        ip = request.META.get("HTTP_X_FORWARDED_FOR") or request.META.get("REMOTE_ADDR")
        if ip and "," in ip:
            ip = ip.split(",")[0].strip()

        try:
            target_info = AdminUserManagementService.delete_user(
                actor=request.user,
                user_id=user_id,
                ip_address=ip,
            )
            return Response(
                {
                    "message": f"User '{target_info['email']}' removed successfully.",
                    "deleted_user": target_info,
                },
                status=status.HTTP_200_OK,
            )
        except AdminPermissionDenied as e:
            return Response({"error": getattr(e, "code", "PERMISSION_DENIED"), "detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except AdminValidationError as e:
            code = getattr(e, "code", "VALIDATION_ERROR")
            http_status = {"USER_NOT_FOUND": status.HTTP_404_NOT_FOUND,
                           "USER_HAS_PROTECTED_RECORDS": status.HTTP_409_CONFLICT}.get(code, status.HTTP_400_BAD_REQUEST)
            return Response({"error": code, "detail": str(e)}, status=http_status)


class AdminUserAuditLogsView(APIView):
    """
    GET /api/v1/admin/users/<user_id>/audit/ - Retrieve append-only audit trail for a specific user.
    """
    permission_classes = [IsAuthenticatedUser, IsAnyAdminUserManagement]

    def get(self, request, user_id):
        from apps.authentication.models import UserAuditLog
        try:
            target_user, _ = AdminUserManagementService.get_user_detail(actor=request.user, user_id=user_id)
        except AdminValidationError as e:
            return Response({"error": getattr(e, "code", "VALIDATION_ERROR"), "detail": str(e)}, status=status.HTTP_404_NOT_FOUND)

        logs = UserAuditLog.objects.filter(target_user=target_user).select_related("actor").order_by("-timestamp")
        serializer = UserAuditLogSerializer(logs, many=True)
        return Response({
            "user_id": target_user.pk,
            "email": target_user.email,
            "count": logs.count(),
            "results": serializer.data,
        }, status=status.HTTP_200_OK)


class AdminControlCentreSummaryView(APIView):
    """
    GET /api/v1/admin/control-centre/summary/
    Dedicated summary endpoint for the Head Admin Control Centre.
    Permits Head Admin access to the full governance summary, and applies
    least-privilege restrictions to other administrative roles.
    """
    permission_classes = [IsAuthenticatedUser, IsAnyAdminUserManagement]

    def get(self, request):
        summary = HeadAdminControlCentreService.build_summary(actor=request.user)
        return Response(summary, status=status.HTTP_200_OK)


class AdminGlobalUserAuditLogsView(APIView):
    """
    GET /api/v1/admin/users/audit-trail/
    Global audit trail of all privileged actions across all users.
    Restricted strictly to the Head Administrator or superuser.
    Read-only with sanitization against sensitive credential leakage.
    """
    permission_classes = [IsAuthenticatedUser, IsHeadAdminOnly]

    def get(self, request):
        filters = {
            "action": request.query_params.get("action"),
            "target_role": request.query_params.get("target_role") or request.query_params.get("role"),
            "search": request.query_params.get("search") or request.query_params.get("q"),
        }
        filters = {k: v for k, v in filters.items() if v is not None}
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 25))

        try:
            result = HeadAdminControlCentreService.list_audit_trail(
                actor=request.user,
                filters=filters,
                page=page,
                page_size=page_size,
            )
            return Response(result, status=status.HTTP_200_OK)
        except AdminPermissionDenied as e:
            return Response({"error": getattr(e, "code", "PERMISSION_DENIED"), "detail": str(e)}, status=status.HTTP_403_FORBIDDEN)


class AdminUserResetPasswordView(APIView):
    """
    POST /api/v1/admin/users/<int:user_id>/reset-password/
    Head Admin only. E-mails the user a single-use, expiring password-reset link; the administrator never
    sets or sees the password. The response states whether the e-mail was actually accepted for delivery.
    """
    permission_classes = [IsAuthenticatedUser, IsHeadAdminOnly]

    def post(self, request, user_id):
        ip = request.META.get("HTTP_X_FORWARDED_FOR") or request.META.get("REMOTE_ADDR")
        if ip and "," in ip:
            ip = ip.split(",")[0].strip()

        try:
            _, email_sent = AdminUserManagementService.reset_password(
                actor=request.user,
                user_id=user_id,
                new_password=request.data.get("password") or request.data.get("new_password"),
                ip_address=ip,
            )
        except AdminPermissionDenied as e:
            return Response({"error": getattr(e, "code", "PERMISSION_DENIED"), "detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except AdminValidationError as e:
            code = getattr(e, "code", "VALIDATION_ERROR")
            http_status = status.HTTP_404_NOT_FOUND if code == "USER_NOT_FOUND" else status.HTTP_400_BAD_REQUEST
            return Response({"error": code, "detail": str(e)}, status=http_status)
        if not email_sent:
            return Response({
                "error": "EMAIL_DELIVERY_FAILED",
                "detail": "The password reset e-mail could not be sent. Check the e-mail configuration and try again.",
                "email_sent": False,
            }, status=status.HTTP_502_BAD_GATEWAY)
        return Response({
            "message": "A password reset link has been e-mailed to the user.",
            "user_id": user_id,
            "email_sent": True,
        }, status=status.HTTP_200_OK)


class AdminUserCommitteeView(APIView):
    """
    POST /api/v1/admin/users/<int:user_id>/committee/
    Assign or remove committee framework authorization for a user.
    Restricted to Platform Administrators (Head Admin, State Admin).
    Council Admin Overseer is strictly forbidden.
    """
    permission_classes = [IsAuthenticatedUser, IsAdminOnly]

    def post(self, request, user_id):
        framework = request.data.get("framework")
        action = request.data.get("action", "assign")  # "assign" or "remove"
        institution_id = request.data.get("institution_id", "")

        if not framework:
            return Response({"error": "VALIDATION_ERROR", "detail": "Framework is required."}, status=status.HTTP_400_BAD_REQUEST)

        valid_frameworks = ("UNIVERSITY_2026", "COLLEGE_2026", "ALL")
        if framework not in valid_frameworks:
            return Response(
                {"error": "VALIDATION_ERROR", "detail": f"Invalid framework. Must be one of {valid_frameworks}."},
                status=status.HTTP_400_BAD_REQUEST
            )

        ip = request.META.get("HTTP_X_FORWARDED_FOR") or request.META.get("REMOTE_ADDR")
        if ip and "," in ip:
            ip = ip.split(",")[0].strip()

        try:
            auth = AdminUserManagementService.manage_committee_assignment(
                actor=request.user,
                user_id=user_id,
                framework=framework,
                action=action,
                institution_id=institution_id,
                ip_address=ip,
            )
            return Response({
                "message": f"Committee authorization {action}ed successfully.",
                "user_id": user_id,
                "framework": framework,
                "action": action,
            }, status=status.HTTP_200_OK)
        except AdminPermissionDenied as e:
            return Response({"error": getattr(e, "code", "PERMISSION_DENIED"), "detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except AdminValidationError as e:
            code = getattr(e, "code", "VALIDATION_ERROR")
            http_status = status.HTTP_404_NOT_FOUND if code == "USER_NOT_FOUND" else status.HTTP_400_BAD_REQUEST
            return Response({"error": code, "detail": str(e)}, status=http_status)


class AdminUserResendInvitationView(APIView):
    """
    POST /api/v1/admin/users/<int:user_id>/resend-invitation/
    Head Admin only. Re-sends the activation invitation for an account that has never been activated. The
    token is delivered by e-mail only and is never included in the response.
    """
    permission_classes = [IsAuthenticatedUser, IsHeadAdminOnly]

    def post(self, request, user_id):
        from apps.authentication.models import User, UserAuditLog
        from apps.authentication.activation_service import AccountActivationService, InvitationNotAllowedError
        try:
            target_user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"error": "USER_NOT_FOUND", "detail": f"User with ID {user_id} does not exist."}, status=status.HTTP_404_NOT_FOUND)

        try:
            email_sent = AccountActivationService.resend_invitation(target_user, actor=request.user)
        except InvitationNotAllowedError as e:
            return Response({"error": "ALREADY_ACTIVATED", "detail": str(e)}, status=status.HTTP_409_CONFLICT)
        if not email_sent:
            UserAuditLog.objects.create(actor=request.user, target_user=target_user, action="NOTIFICATION_FAILED",
                                        details={"notification": "ACTIVATION_INVITATION"})
            return Response({
                "error": "EMAIL_DELIVERY_FAILED",
                "detail": "The invitation e-mail could not be sent. Check the e-mail configuration and try again.",
                "email_sent": False,
                "credential_status": "INVITATION_PENDING_DISPATCH",
            }, status=status.HTTP_502_BAD_GATEWAY)
        return Response({
            "message": "Activation invitation e-mailed to the user.",
            "email_sent": True,
            "credential_status": "INVITATION_SENT",
        }, status=status.HTTP_200_OK)


class AdminUserInstitutionDecisionView(APIView):
    """
    POST /api/v1/admin/users/<int:user_id>/institution-access/  {"decision": "approve"|"reject", "reason": "..."}
    Approves or rejects a self-registered applicant's request to act for an institution. Until approved the
    account has no institution binding and therefore no access to any assessment.
    Head Admin, State Admin, Sub-Admin and legacy Admin; the Council Admin Overseer is read-only.
    """
    permission_classes = [IsAuthenticatedUser, IsAdminOnly]

    def post(self, request, user_id):
        decision = str(request.data.get("decision", "")).lower()
        if decision not in ("approve", "reject"):
            return Response({"error": "VALIDATION_ERROR", "detail": "decision must be 'approve' or 'reject'."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            user = AdminUserManagementService.decide_institution_access(
                actor=request.user, user_id=user_id, approve=decision == "approve",
                reason=request.data.get("reason", ""), ip_address=request.META.get("REMOTE_ADDR"))
        except AdminPermissionDenied as e:
            return Response({"error": getattr(e, "code", "PERMISSION_DENIED"), "detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except AdminValidationError as e:
            code = getattr(e, "code", "VALIDATION_ERROR")
            http_status = status.HTTP_404_NOT_FOUND if code == "USER_NOT_FOUND" else status.HTTP_400_BAD_REQUEST
            return Response({"error": code, "detail": str(e)}, status=http_status)
        return Response(AdminUserDetailSerializer(user).data, status=status.HTTP_200_OK)


class AdminUserRevokeInvitationView(APIView):
    """
    POST /api/v1/admin/users/<int:user_id>/revoke-invitation/
    Revokes any outstanding activation invitation tokens for a user.
    """
    permission_classes = [IsAuthenticatedUser, IsHeadAdminOnly]

    def post(self, request, user_id):
        from apps.authentication.models import User
        from apps.authentication.activation_service import AccountActivationService
        try:
            target_user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"error": "USER_NOT_FOUND", "detail": f"User with ID {user_id} does not exist."}, status=status.HTTP_404_NOT_FOUND)

        AccountActivationService.revoke_invitation(target_user, actor=request.user)
        return Response({
            "message": "Activation invitation revoked successfully."
        }, status=status.HTTP_200_OK)


class AdminCommitteeListCreateView(APIView):
    """
    GET  /api/v1/admin/committees/ - List all committees (Any Admin)
    POST /api/v1/admin/committees/ - Create new committee (Admin Only)
    """
    permission_classes = [IsAuthenticatedUser, IsAnyAdminUserManagement]

    def get(self, request):
        from .services import CommitteeService
        from .api_serializers import CommitteeListSerializer
        filters = {
            "framework": request.query_params.get("framework"),
            "committee_type": request.query_params.get("committee_type"),
            "is_active": request.query_params.get("is_active"),
            "search": request.query_params.get("q") or request.query_params.get("search"),
        }
        committees = CommitteeService.list_committees(filters)
        serializer = CommitteeListSerializer(committees, many=True)
        return Response({
            "count": len(serializer.data),
            "results": serializer.data,
        }, status=status.HTTP_200_OK)

    def post(self, request):
        from .api_permissions import IsAdminOnly
        perm = IsAdminOnly()
        if not perm.has_permission(request, self):
            raise AdminPermissionDenied("Platform administration authority required. Council Admin Overseer is restricted.", code="ADMIN_REQUIRED")

        from .services import CommitteeService
        from .api_serializers import CommitteeCreateSerializer, CommitteeDetailSerializer
        serializer = CommitteeCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            committee = CommitteeService.create_committee(
                actor=request.user,
                data=serializer.validated_data,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return Response(CommitteeDetailSerializer(committee).data, status=status.HTTP_201_CREATED)
        except AdminValidationError as e:
            return Response({"error": getattr(e, "code", "VALIDATION_ERROR"), "detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminCommitteeDetailView(APIView):
    """
    GET   /api/v1/admin/committees/<int:committee_id>/ - Committee detail (Any Admin)
    PATCH /api/v1/admin/committees/<int:committee_id>/ - Update committee (Admin Only)
    """
    permission_classes = [IsAuthenticatedUser, IsAnyAdminUserManagement]

    def get(self, request, committee_id):
        from .services import CommitteeService
        from .api_serializers import CommitteeDetailSerializer
        try:
            committee = CommitteeService.get_committee_detail(committee_id)
            return Response(CommitteeDetailSerializer(committee).data, status=status.HTTP_200_OK)
        except AdminValidationError as e:
            return Response({"error": getattr(e, "code", "NOT_FOUND"), "detail": str(e)}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, committee_id):
        from .api_permissions import IsAdminOnly
        perm = IsAdminOnly()
        if not perm.has_permission(request, self):
            raise AdminPermissionDenied("Platform administration authority required. Council Admin Overseer is restricted.", code="ADMIN_REQUIRED")

        from .services import CommitteeService
        from .api_serializers import CommitteeUpdateSerializer, CommitteeDetailSerializer
        serializer = CommitteeUpdateSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            committee = CommitteeService.update_committee(
                actor=request.user,
                committee_id=committee_id,
                data=serializer.validated_data,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return Response(CommitteeDetailSerializer(committee).data, status=status.HTTP_200_OK)
        except AdminValidationError as e:
            return Response({"error": getattr(e, "code", "VALIDATION_ERROR"), "detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminCommitteeAssignChairView(APIView):
    """
    POST /api/v1/admin/committees/<int:committee_id>/chair/
    Assigns or replaces the chair of a committee.
    """
    permission_classes = [IsAuthenticatedUser, IsAdminOnly]

    def post(self, request, committee_id):
        from .services import CommitteeService
        from .api_serializers import CommitteeAssignChairSerializer, CommitteeDetailSerializer
        serializer = CommitteeAssignChairSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            committee = CommitteeService.assign_chair(
                actor=request.user,
                committee_id=committee_id,
                chair_id=serializer.validated_data['chair_id'],
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return Response(CommitteeDetailSerializer(committee).data, status=status.HTTP_200_OK)
        except AdminValidationError as e:
            code = getattr(e, "code", "VALIDATION_ERROR")
            http_status = status.HTTP_404_NOT_FOUND if code in ("COMMITTEE_NOT_FOUND", "USER_NOT_FOUND") else status.HTTP_400_BAD_REQUEST
            return Response({"error": code, "detail": str(e)}, status=http_status)


class AdminCommitteeMembersView(APIView):
    """
    POST   /api/v1/admin/committees/<int:committee_id>/members/ - Add member
    DELETE /api/v1/admin/committees/<int:committee_id>/members/<int:user_id>/ - Remove member
    """
    permission_classes = [IsAuthenticatedUser, IsAdminOnly]

    def post(self, request, committee_id):
        from .services import CommitteeService
        from .api_serializers import CommitteeAddMemberSerializer, CommitteeMemberSerializer
        serializer = CommitteeAddMemberSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            membership = CommitteeService.add_member(
                actor=request.user,
                committee_id=committee_id,
                user_id=serializer.validated_data['user_id'],
                role_in_committee=serializer.validated_data.get('role_in_committee', 'member'),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return Response(CommitteeMemberSerializer(membership).data, status=status.HTTP_201_CREATED)
        except AdminValidationError as e:
            code = getattr(e, "code", "VALIDATION_ERROR")
            http_status = status.HTTP_404_NOT_FOUND if code in ("COMMITTEE_NOT_FOUND", "USER_NOT_FOUND") else status.HTTP_400_BAD_REQUEST
            return Response({"error": code, "detail": str(e)}, status=http_status)

    def delete(self, request, committee_id, user_id=None):
        from .services import CommitteeService
        if not user_id:
            user_id = request.data.get('user_id')
        if not user_id:
            return Response({"detail": "User ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            CommitteeService.remove_member(
                actor=request.user,
                committee_id=committee_id,
                user_id=user_id,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return Response({"message": "Member removed from committee successfully."}, status=status.HTTP_200_OK)
        except AdminValidationError as e:
            code = getattr(e, "code", "VALIDATION_ERROR")
            http_status = status.HTTP_404_NOT_FOUND if code in ("COMMITTEE_NOT_FOUND", "MEMBERSHIP_NOT_FOUND") else status.HTTP_400_BAD_REQUEST
            return Response({"error": code, "detail": str(e)}, status=http_status)




