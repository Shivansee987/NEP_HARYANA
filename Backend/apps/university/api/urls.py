"""
NEP Excellence Awards 2026 - University API URL Routing
"""
from django.urls import path

from .views import (
    UniversityAssessmentBlockReviewView,
    UniversityAssessmentCertifyView,
    UniversityAssessmentCompleteReviewView,
    UniversityAssessmentCoverageView,
    UniversityAssessmentDetailView,
    UniversityAssessmentEvaluateView,
    UniversityAssessmentListCreateView,
    UniversityAssessmentParameterDetailView,
    UniversityAssessmentParametersListView,
    UniversityAssessmentReadinessView,
    UniversityAssessmentReturnCorrectionView,
    UniversityAssessmentReviewHistoryView,
    UniversityAssessmentStartReviewView,
    UniversityAssessmentSubmitView,
    UniversityDetailView,
    UniversityListCreateView,
    UniversityReviewQueueView,
)

urlpatterns = [
    # University Institution Endpoints
    path('universities/', UniversityListCreateView.as_view(), name='university-list-create'),
    path('universities/<str:pk>/', UniversityDetailView.as_view(), name='university-detail'),

    # Screening Committee Review Queue (Placed BEFORE <str:assessment_id> to avoid collision)
    path('university-assessments/review-queue/', UniversityReviewQueueView.as_view(), name='university-review-queue'),

    # University Assessment Lifecycle Endpoints
    path('universities/<str:pk>/assessments/', UniversityAssessmentListCreateView.as_view(), name='university-assessment-list-create'),
    path('university-assessments/<str:assessment_id>/', UniversityAssessmentDetailView.as_view(), name='university-assessment-detail'),
    path('university-assessments/<str:assessment_id>/submit/', UniversityAssessmentSubmitView.as_view(), name='university-assessment-submit'),

    # Parameter Read/Write Endpoints
    path('university-assessments/<str:assessment_id>/parameters/', UniversityAssessmentParametersListView.as_view(), name='university-assessment-parameters-list'),
    path('university-assessments/<str:assessment_id>/parameters/<str:parameter_code>/', UniversityAssessmentParameterDetailView.as_view(), name='university-assessment-parameter-detail'),

    # Coverage, Readiness & Scoring Endpoints
    path('university-assessments/<str:assessment_id>/coverage/', UniversityAssessmentCoverageView.as_view(), name='university-assessment-coverage'),
    path('university-assessments/<str:assessment_id>/readiness/', UniversityAssessmentReadinessView.as_view(), name='university-assessment-readiness'),
    path('university-assessments/<str:assessment_id>/evaluate/', UniversityAssessmentEvaluateView.as_view(), name='university-assessment-evaluate'),

    # Committee Review Actions & Certification Endpoints (Phase 6C)
    path('university-assessments/<str:assessment_id>/start-review/', UniversityAssessmentStartReviewView.as_view(), name='university-assessment-start-review'),
    path('university-assessments/<str:assessment_id>/complete-review/', UniversityAssessmentCompleteReviewView.as_view(), name='university-assessment-complete-review'),
    path('university-assessments/<str:assessment_id>/return-for-correction/', UniversityAssessmentReturnCorrectionView.as_view(), name='university-assessment-return-correction'),
    path('university-assessments/<str:assessment_id>/block-review/', UniversityAssessmentBlockReviewView.as_view(), name='university-assessment-block-review'),
    path('university-assessments/<str:assessment_id>/review-history/', UniversityAssessmentReviewHistoryView.as_view(), name='university-assessment-review-history'),
    path('university-assessments/<str:assessment_id>/certify/', UniversityAssessmentCertifyView.as_view(), name='university-assessment-certify'),

    # Phase 6C RESTful API Endpoints (as per Section 4 specification)
    path('review/queue/', UniversityReviewQueueView.as_view(), name='api-v1-university-review-queue'),
    path('assessments/<str:assessment_id>/review/start/', UniversityAssessmentStartReviewView.as_view(), name='api-v1-university-review-start'),
    path('assessments/<str:assessment_id>/review/complete/', UniversityAssessmentCompleteReviewView.as_view(), name='api-v1-university-review-complete'),
    path('assessments/<str:assessment_id>/review/return/', UniversityAssessmentReturnCorrectionView.as_view(), name='api-v1-university-review-return'),
    path('assessments/<str:assessment_id>/review/block/', UniversityAssessmentBlockReviewView.as_view(), name='api-v1-university-review-block'),
    path('assessments/<str:assessment_id>/review/history/', UniversityAssessmentReviewHistoryView.as_view(), name='api-v1-university-review-history'),
    path('assessments/<str:assessment_id>/certify/', UniversityAssessmentCertifyView.as_view(), name='api-v1-university-certify'),
]
