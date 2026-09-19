"""
NEP Excellence Awards 2026 - Admin Control Plane API URL Routing (Phase 8)
Mounted at /api/v1/admin/
"""
from django.urls import path

from .api_views import (
    AdminAssessmentAssignReviewerView,
    AdminAssessmentCertifyView,
    AdminAssessmentInspectView,
    AdminReviewQueueView,
    AdminReviewerAuthorizationsView,
)

urlpatterns = [
    # Unified Review Queue
    path('review-queue/', AdminReviewQueueView.as_view(), name='admin-review-queue'),
    path('queue/', AdminReviewQueueView.as_view(), name='admin-queue-alias'),

    # Assessment Inspection & Administration
    path('assessments/<str:assessment_id>/inspect/', AdminAssessmentInspectView.as_view(), name='admin-assessment-inspect'),
    path('assessments/<str:assessment_id>/assign/', AdminAssessmentAssignReviewerView.as_view(), name='admin-assessment-assign'),
    path('assessments/<str:assessment_id>/certify/', AdminAssessmentCertifyView.as_view(), name='admin-assessment-certify'),

    # Reviewer Authorizations Management
    path('authorizations/', AdminReviewerAuthorizationsView.as_view(), name='admin-authorizations'),
]
