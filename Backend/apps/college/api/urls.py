"""
NEP Excellence Awards 2026 - College API URL Routing (Phase 7C)
"""
from django.urls import path

from .views import (
    CollegeAssessmentBlockReviewView,
    CollegeAssessmentCertifyView,
    CollegeAssessmentCompleteReviewView,
    CollegeAssessmentCoverageView,
    CollegeAssessmentDetailView,
    CollegeAssessmentEvaluateView,
    CollegeAssessmentListCreateView,
    CollegeAssessmentParameterDetailView,
    CollegeAssessmentParametersListView,
    CollegeAssessmentReadinessView,
    CollegeAssessmentReturnCorrectionView,
    CollegeAssessmentReviewEvaluateView,
    CollegeAssessmentReviewHistoryView,
    CollegeAssessmentStartReviewView,
    CollegeAssessmentSubmitView,
    CollegeDetailView,
    CollegeListCreateView,
    CollegeReviewQueueView,
)

urlpatterns = [
    # College Institution Endpoints
    path('colleges/', CollegeListCreateView.as_view(), name='college-list-create'),
    path('colleges/<str:pk>/', CollegeDetailView.as_view(), name='college-detail'),

    # College Assessment Lifecycle Endpoints (Direct and Nested)
    path('colleges/<str:pk>/assessments/', CollegeAssessmentListCreateView.as_view(), name='college-assessment-nested-list-create'),
    path('college/assessments/', CollegeAssessmentListCreateView.as_view(), name='college-assessment-list-create'),
    path('college-assessments/', CollegeAssessmentListCreateView.as_view(), name='college-assessments-alias'),
    path('assessments/', CollegeAssessmentListCreateView.as_view(), name='college-assessments-v1'),

    path('college/assessments/<str:assessment_id>/', CollegeAssessmentDetailView.as_view(), name='college-assessment-detail'),
    path('college-assessments/<str:assessment_id>/', CollegeAssessmentDetailView.as_view(), name='college-assessment-detail-alias'),
    path('assessments/<str:assessment_id>/', CollegeAssessmentDetailView.as_view(), name='college-assessment-detail-v1'),

    path('college/assessments/<str:assessment_id>/submit/', CollegeAssessmentSubmitView.as_view(), name='college-assessment-submit'),
    path('college-assessments/<str:assessment_id>/submit/', CollegeAssessmentSubmitView.as_view(), name='college-assessment-submit-alias'),
    path('assessments/<str:assessment_id>/submit/', CollegeAssessmentSubmitView.as_view(), name='college-assessment-submit-v1'),

    # Parameter Read/Write Endpoints
    path('college/assessments/<str:assessment_id>/parameters/', CollegeAssessmentParametersListView.as_view(), name='college-assessment-parameters-list'),
    path('college-assessments/<str:assessment_id>/parameters/', CollegeAssessmentParametersListView.as_view(), name='college-assessment-parameters-list-alias'),
    path('assessments/<str:assessment_id>/parameters/', CollegeAssessmentParametersListView.as_view(), name='college-assessment-parameters-list-v1'),

    path('college/assessments/<str:assessment_id>/parameters/<str:parameter_code>/', CollegeAssessmentParameterDetailView.as_view(), name='college-assessment-parameter-detail'),
    path('college-assessments/<str:assessment_id>/parameters/<str:parameter_code>/', CollegeAssessmentParameterDetailView.as_view(), name='college-assessment-parameter-detail-alias'),
    path('assessments/<str:assessment_id>/parameters/<str:parameter_code>/', CollegeAssessmentParameterDetailView.as_view(), name='college-assessment-parameter-detail-v1'),

    # Coverage, Readiness & Scoring Endpoints
    path('college/assessments/<str:assessment_id>/coverage/', CollegeAssessmentCoverageView.as_view(), name='college-assessment-coverage'),
    path('college-assessments/<str:assessment_id>/coverage/', CollegeAssessmentCoverageView.as_view(), name='college-assessment-coverage-alias'),
    path('assessments/<str:assessment_id>/coverage/', CollegeAssessmentCoverageView.as_view(), name='college-assessment-coverage-v1'),

    path('college/assessments/<str:assessment_id>/readiness/', CollegeAssessmentReadinessView.as_view(), name='college-assessment-readiness'),
    path('college-assessments/<str:assessment_id>/readiness/', CollegeAssessmentReadinessView.as_view(), name='college-assessment-readiness-alias'),
    path('assessments/<str:assessment_id>/readiness/', CollegeAssessmentReadinessView.as_view(), name='college-assessment-readiness-v1'),

    path('college/assessments/<str:assessment_id>/evaluate/', CollegeAssessmentEvaluateView.as_view(), name='college-assessment-evaluate'),
    path('college-assessments/<str:assessment_id>/evaluate/', CollegeAssessmentEvaluateView.as_view(), name='college-assessment-evaluate-alias'),
    path('assessments/<str:assessment_id>/evaluate/', CollegeAssessmentEvaluateView.as_view(), name='college-assessment-evaluate-v1'),

    # Phase 7C College Review & Certification Endpoints
    path('college/review/queue/', CollegeReviewQueueView.as_view(), name='college-review-queue'),
    path('college-assessments/review/queue/', CollegeReviewQueueView.as_view(), name='college-review-queue-alias'),
    path('review/queue/', CollegeReviewQueueView.as_view(), name='api-v1-college-review-queue'),

    path('college/assessments/<str:assessment_id>/review/start/', CollegeAssessmentStartReviewView.as_view(), name='college-assessment-review-start'),
    path('college-assessments/<str:assessment_id>/start-review/', CollegeAssessmentStartReviewView.as_view(), name='college-assessment-start-review-alias'),
    path('assessments/<str:assessment_id>/review/start/', CollegeAssessmentStartReviewView.as_view(), name='api-v1-college-review-start'),

    path('college/assessments/<str:assessment_id>/review/evaluate/', CollegeAssessmentReviewEvaluateView.as_view(), name='college-assessment-review-evaluate'),
    path('college-assessments/<str:assessment_id>/review/evaluate/', CollegeAssessmentReviewEvaluateView.as_view(), name='college-assessment-review-evaluate-alias'),
    path('assessments/<str:assessment_id>/review/evaluate/', CollegeAssessmentReviewEvaluateView.as_view(), name='api-v1-college-review-evaluate'),

    path('college/assessments/<str:assessment_id>/review/complete/', CollegeAssessmentCompleteReviewView.as_view(), name='college-assessment-review-complete'),
    path('college-assessments/<str:assessment_id>/complete-review/', CollegeAssessmentCompleteReviewView.as_view(), name='college-assessment-complete-review-alias'),
    path('assessments/<str:assessment_id>/review/complete/', CollegeAssessmentCompleteReviewView.as_view(), name='api-v1-college-review-complete'),

    path('college/assessments/<str:assessment_id>/review/return/', CollegeAssessmentReturnCorrectionView.as_view(), name='college-assessment-review-return'),
    path('college-assessments/<str:assessment_id>/return-for-correction/', CollegeAssessmentReturnCorrectionView.as_view(), name='college-assessment-return-correction-alias'),
    path('assessments/<str:assessment_id>/review/return/', CollegeAssessmentReturnCorrectionView.as_view(), name='api-v1-college-review-return'),

    path('college/assessments/<str:assessment_id>/review/block/', CollegeAssessmentBlockReviewView.as_view(), name='college-assessment-review-block'),
    path('college-assessments/<str:assessment_id>/block-review/', CollegeAssessmentBlockReviewView.as_view(), name='college-assessment-block-review-alias'),
    path('assessments/<str:assessment_id>/review/block/', CollegeAssessmentBlockReviewView.as_view(), name='api-v1-college-review-block'),

    path('college/assessments/<str:assessment_id>/review/history/', CollegeAssessmentReviewHistoryView.as_view(), name='college-assessment-review-history'),
    path('college-assessments/<str:assessment_id>/review-history/', CollegeAssessmentReviewHistoryView.as_view(), name='college-assessment-review-history-alias'),
    path('assessments/<str:assessment_id>/review/history/', CollegeAssessmentReviewHistoryView.as_view(), name='api-v1-college-review-history'),

    path('college/assessments/<str:assessment_id>/certify/', CollegeAssessmentCertifyView.as_view(), name='college-assessment-certify'),
    path('college-assessments/<str:assessment_id>/certify/', CollegeAssessmentCertifyView.as_view(), name='college-assessment-certify-alias'),
    path('assessments/<str:assessment_id>/certify/', CollegeAssessmentCertifyView.as_view(), name='api-v1-college-certify'),
]
