"""
NEP Excellence Awards 2026 - Reports & Analytics URL Configuration (Phase 9)
Mounted at /api/v1/reports/
"""
from django.urls import path

from apps.reports.views import (
    AdminReportingSummaryView,
    AssessmentEvidenceReportView,
    AssessmentParameterReportView,
    AssessmentReportExportView,
    AssessmentReportView,
    AssessmentReviewReportView,
    AssessmentScoringReportView,
    AssessmentSubcriteriaReportView,
    InstitutionReportingSummaryView,
)

urlpatterns = [
    # Cross-Framework Admin Analytics Summary
    path("admin/summary/", AdminReportingSummaryView.as_view(), name="reports-admin-summary"),

    # Institutional Summary (own institution)
    path("institution/summary/", InstitutionReportingSummaryView.as_view(), name="reports-institution-summary"),

    # Per-Assessment Reports
    path("assessments/<str:assessment_id>/", AssessmentReportView.as_view(), name="reports-assessment-detail"),
    path("assessments/<str:assessment_id>/parameters/", AssessmentParameterReportView.as_view(), name="reports-assessment-parameters"),
    path("assessments/<str:assessment_id>/subcriteria/", AssessmentSubcriteriaReportView.as_view(), name="reports-assessment-subcriteria"),
    path("assessments/<str:assessment_id>/evidence-readiness/", AssessmentEvidenceReportView.as_view(), name="reports-assessment-evidence"),
    path("assessments/<str:assessment_id>/scoring/", AssessmentScoringReportView.as_view(), name="reports-assessment-scoring"),
    path("assessments/<str:assessment_id>/review/", AssessmentReviewReportView.as_view(), name="reports-assessment-review"),
    path("assessments/<str:assessment_id>/export/", AssessmentReportExportView.as_view(), name="reports-assessment-export"),
]
