"""
NEP Excellence Awards 2026 - Reports & Analytics REST API Views (Phase 9)
Exclusively read-only projection endpoints. Writable methods strictly prohibited.
"""
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.reports.permissions import (
    IsReportAuthorized,
    IsAdminOrChairForAnalytics,
    ReportPermissionDenied,
)
from apps.reports.services import ReportingService, AssessmentNotFoundError


class AssessmentReportView(APIView):
    """
    GET /api/v1/reports/assessments/<assessment_id>/
    Returns the comprehensive, authoritative read-only report projection.
    """
    permission_classes = [IsAuthenticated, IsReportAuthorized]

    def get(self, request, assessment_id):
        try:
            report_data = ReportingService.get_assessment_report(assessment_id, request.user)
            return Response(report_data, status=status.HTTP_200_OK)
        except AssessmentNotFoundError as e:
            return Response({"error": "ASSESSMENT_NOT_FOUND", "detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ReportPermissionDenied as e:
            return Response({"error": "PERMISSION_DENIED", "detail": str(e)}, status=status.HTTP_403_FORBIDDEN)


class AssessmentParameterReportView(APIView):
    """
    GET /api/v1/reports/assessments/<assessment_id>/parameters/
    Returns parameter-level audit rows (U1–U20 or C1–C22) consuming frozen engine output.
    """
    permission_classes = [IsAuthenticated, IsReportAuthorized]

    def get(self, request, assessment_id):
        try:
            report_data = ReportingService.get_parameter_report(assessment_id, request.user)
            return Response(report_data, status=status.HTTP_200_OK)
        except AssessmentNotFoundError as e:
            return Response({"error": "ASSESSMENT_NOT_FOUND", "detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ReportPermissionDenied as e:
            return Response({"error": "PERMISSION_DENIED", "detail": str(e)}, status=status.HTTP_403_FORBIDDEN)


class AssessmentSubcriteriaReportView(APIView):
    """
    GET /api/v1/reports/assessments/<assessment_id>/subcriteria/
    Returns granular subcriterion traces from the frozen scoring engine and evidence evaluator.
    """
    permission_classes = [IsAuthenticated, IsReportAuthorized]

    def get(self, request, assessment_id):
        try:
            report_data = ReportingService.get_subcriteria_report(assessment_id, request.user)
            return Response(report_data, status=status.HTTP_200_OK)
        except AssessmentNotFoundError as e:
            return Response({"error": "ASSESSMENT_NOT_FOUND", "detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ReportPermissionDenied as e:
            return Response({"error": "PERMISSION_DENIED", "detail": str(e)}, status=status.HTTP_403_FORBIDDEN)


class AssessmentEvidenceReportView(APIView):
    """
    GET /api/v1/reports/assessments/<assessment_id>/evidence-readiness/
    Returns structured evidence coverage, verification status, and readiness blockers.
    """
    permission_classes = [IsAuthenticated, IsReportAuthorized]

    def get(self, request, assessment_id):
        try:
            report_data = ReportingService.get_evidence_report(assessment_id, request.user)
            return Response(report_data, status=status.HTTP_200_OK)
        except AssessmentNotFoundError as e:
            return Response({"error": "ASSESSMENT_NOT_FOUND", "detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ReportPermissionDenied as e:
            return Response({"error": "PERMISSION_DENIED", "detail": str(e)}, status=status.HTTP_403_FORBIDDEN)


class AssessmentScoringReportView(APIView):
    """
    GET /api/v1/reports/assessments/<assessment_id>/scoring/
    Returns authoritative scoring evaluation summary from frozen engine.
    """
    permission_classes = [IsAuthenticated, IsReportAuthorized]

    def get(self, request, assessment_id):
        try:
            report_data = ReportingService.get_scoring_report(assessment_id, request.user)
            return Response(report_data, status=status.HTTP_200_OK)
        except AssessmentNotFoundError as e:
            return Response({"error": "ASSESSMENT_NOT_FOUND", "detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ReportPermissionDenied as e:
            return Response({"error": "PERMISSION_DENIED", "detail": str(e)}, status=status.HTTP_403_FORBIDDEN)


class AssessmentReviewReportView(APIView):
    """
    GET /api/v1/reports/assessments/<assessment_id>/review/
    Returns append-only review records, lifecycle state, and certification eligibility gates.
    """
    permission_classes = [IsAuthenticated, IsReportAuthorized]

    def get(self, request, assessment_id):
        try:
            report_data = ReportingService.get_review_report(assessment_id, request.user)
            return Response(report_data, status=status.HTTP_200_OK)
        except AssessmentNotFoundError as e:
            return Response({"error": "ASSESSMENT_NOT_FOUND", "detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ReportPermissionDenied as e:
            return Response({"error": "PERMISSION_DENIED", "detail": str(e)}, status=status.HTTP_403_FORBIDDEN)


class AdminReportingSummaryView(APIView):
    """
    GET /api/v1/reports/admin/summary/
    Cross-framework analytics summary for DHE Admins and Committee Chairs.
    Does NOT calculate institutional rankings or Top 10 lists.
    """
    permission_classes = [IsAuthenticated, IsAdminOrChairForAnalytics]

    def get(self, request):
        data = ReportingService.get_admin_summary(request.user)
        return Response(data, status=status.HTTP_200_OK)


class InstitutionReportingSummaryView(APIView):
    """
    GET /api/v1/reports/institution/summary/
    Returns report summary for the logged-in institutional user's institution.
    """
    permission_classes = [IsAuthenticated, IsReportAuthorized]

    def get(self, request):
        data = ReportingService.get_institution_summary(request.user)
        return Response(data, status=status.HTTP_200_OK)


class AssessmentReportExportView(APIView):
    """
    GET /api/v1/reports/assessments/<assessment_id>/export/
    Exports authoritative CSV report matching on-screen audit ledger.
    """
    permission_classes = [IsAuthenticated, IsReportAuthorized]

    def get(self, request, assessment_id):
        try:
            csv_data = ReportingService.export_csv(assessment_id, request.user)
            response = HttpResponse(csv_data, content_type="text/csv")
            filename = f"NEP_2026_Report_{assessment_id}.csv"
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response
        except AssessmentNotFoundError as e:
            return Response({"error": "ASSESSMENT_NOT_FOUND", "detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ReportPermissionDenied as e:
            return Response({"error": "PERMISSION_DENIED", "detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
