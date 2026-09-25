"""
NEP Excellence Awards 2026 - Evidence API URL Routing
"""
from django.urls import path

from .views import (
    EvidenceAssociateView,
    EvidenceAssociationDetailView,
    EvidenceAssociationDocumentDownloadView,
    EvidenceAssociationHistoryView,
    EvidenceAssociationListView,
    EvidenceAssociationRejectView,
    EvidenceAssociationVerifyView,
    EvidenceCoverageView,
    EvidenceDetailView,
    EvidenceDocumentDownloadView,
    EvidenceListCreateView,
    EvidenceReadinessView,
    EvidenceRejectView,
    EvidenceSubmitView,
    EvidenceVerificationHistoryView,
    EvidenceVerifyView,
    EvidenceWithdrawView,
    ReviewerAssignView,
    ReviewerQueueView,
    ReviewerUnassignView,
)

urlpatterns = [
    # Top-level collection & global endpoints
    path('', EvidenceListCreateView.as_view(), name='evidence-list-create'),
    path('review-queue/', ReviewerQueueView.as_view(), name='evidence-review-queue'),
    path('coverage/', EvidenceCoverageView.as_view(), name='evidence-coverage'),
    path('readiness/', EvidenceReadinessView.as_view(), name='evidence-readiness'),

    # Association-level endpoints (Placed BEFORE <str:pk>/ to prevent pattern conflict)
    path('associations/', EvidenceAssociationListView.as_view(), name='evidence-association-list'),
    path('associations/<str:pk>/', EvidenceAssociationDetailView.as_view(), name='evidence-association-detail'),
    path('associations/<str:pk>/verify/', EvidenceAssociationVerifyView.as_view(), name='evidence-association-verify'),
    path('associations/<str:pk>/reject/', EvidenceAssociationRejectView.as_view(), name='evidence-association-reject'),
    path('associations/<str:pk>/history/', EvidenceAssociationHistoryView.as_view(), name='evidence-association-history'),
    path('associations/<str:pk>/document/', EvidenceAssociationDocumentDownloadView.as_view(), name='evidence-association-document'),

    # Document-specific endpoints (supports document_id UUID or pk)
    path('<str:pk>/', EvidenceDetailView.as_view(), name='evidence-detail'),
    path('<str:pk>/document/', EvidenceDocumentDownloadView.as_view(), name='evidence-document-download'),
    path('<str:pk>/download/', EvidenceDocumentDownloadView.as_view(), name='evidence-document-download-alias'),
    path('<str:pk>/submit/', EvidenceSubmitView.as_view(), name='evidence-submit'),
    path('<str:pk>/withdraw/', EvidenceWithdrawView.as_view(), name='evidence-withdraw'),
    path('<str:pk>/associate/', EvidenceAssociateView.as_view(), name='evidence-associate'),
    path('<str:pk>/assign/', ReviewerAssignView.as_view(), name='evidence-assign'),
    path('<str:pk>/unassign/', ReviewerUnassignView.as_view(), name='evidence-unassign'),
    path('<str:pk>/verify/', EvidenceVerifyView.as_view(), name='evidence-verify'),
    path('<str:pk>/reject/', EvidenceRejectView.as_view(), name='evidence-reject'),
    path('<str:pk>/history/', EvidenceVerificationHistoryView.as_view(), name='evidence-history'),
]
