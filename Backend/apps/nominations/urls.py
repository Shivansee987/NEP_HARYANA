from django.urls import path
from .views import (
    NominationConfigView,
    NominationListView,
    NominationDetailView,
    NominationSaveView,
    NominationSubmitView,
    MySubmissionsListView,
    NominationEvidenceUploadView,
)
from .committee_views import (
    CommitteeDashboardStatsView,
    CommitteeAssignedSubmissionsView,
    CommitteeReviewDetailView,
    CommitteeClarificationRequestView,
    PrincipalClarificationView
)

urlpatterns = [
    path('config/', NominationConfigView.as_view(), name='nomination-config'),
    path('upload/', NominationEvidenceUploadView.as_view(), name='nomination-evidence-upload'),
    path('my-submissions/', MySubmissionsListView.as_view(), name='my-submissions-list'),
    path('', NominationListView.as_view(), name='nomination-list'),
    
    # Committee routes
    path('committee/stats/', CommitteeDashboardStatsView.as_view(), name='committee-stats'),
    path('committee/submissions/', CommitteeAssignedSubmissionsView.as_view(), name='committee-submissions'),
    path('committee/submissions/<int:id>/', CommitteeReviewDetailView.as_view(), name='committee-review-detail'),
    path('committee/submissions/<int:id>/clarification/', CommitteeClarificationRequestView.as_view(), name='committee-clarification-request'),
    
    # Principal clarification routes
    path('<str:form_id>/clarification/', PrincipalClarificationView.as_view(), name='principal-clarification'),
    
    path('<str:form_id>/', NominationDetailView.as_view(), name='nomination-detail'),
    path('<str:form_id>/save/', NominationSaveView.as_view(), name='nomination-save'),
    path('<str:form_id>/submit/', NominationSubmitView.as_view(), name='nomination-submit'),
]
