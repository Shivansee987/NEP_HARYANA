from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import IsAdminRole
from .services import (
    get_all_applications,
    get_analytics,
    get_dashboard_stats,
    get_institutions_summary,
)


class AdminDashboardStatsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        return Response(get_dashboard_stats(), status=status.HTTP_200_OK)


class AdminApplicationsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        return Response(
            {"applications": get_all_applications()},
            status=status.HTTP_200_OK,
        )


class AdminInstitutionsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        return Response(
            {"institutions": get_institutions_summary()},
            status=status.HTTP_200_OK,
        )


class AdminAnalyticsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        return Response(get_analytics(), status=status.HTTP_200_OK)


from django.utils import timezone
from apps.nominations.models import Nomination
from apps.nominations.scoring import AWARD_THRESHOLDS

class AdminNominationReviewView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request, college_id):
        try:
            nom = Nomination.objects.get(college_id=college_id)
        except Nomination.DoesNotExist:
            return Response({"detail": "Nomination not found for this college."}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get("status")
        remarks = request.data.get("remarks")
        reviewer_scores = request.data.get("scores")

        if new_status:
            nom.status = new_status
            if new_status == "Approved":
                nom.is_submitted = True
            elif new_status == "Sent Back":
                nom.is_submitted = False  # unlock nomination for edits
            elif new_status == "Rejected":
                nom.is_submitted = True   # remains locked

        if remarks is not None:
            nom.remarks = remarks

        if reviewer_scores:
            nom.reviewer_scores = reviewer_scores
            # Sum up scores and update nomination
            total_reviewer_score = sum(int(v) for v in reviewer_scores.values())
            nom.score = total_reviewer_score
            
            category = "No Award"
            for threshold in sorted(AWARD_THRESHOLDS, key=lambda x: x["min_score"], reverse=True):
                if total_reviewer_score >= threshold["min_score"]:
                    category = threshold["level"]
                    break
            nom.award_category = category

        # Add history audit entry
        timestamp = timezone.now().strftime("%d/%m/%Y %H:%M")
        nom.history = nom.history or []
        nom.history.append({
            "date": timestamp,
            "status": new_status or nom.status,
            "user": f"{request.user.full_name or request.user.username} (Admin)"
        })

        nom.save()
        
        # Invalidate dashboard stats cache upon review update
        from .services import invalidate_dashboard_stats_cache
        invalidate_dashboard_stats_cache()
        
        # Get updated institution info
        summary_list = get_institutions_summary()
        updated_item = next((item for item in summary_list if str(item["college_id"]) == str(college_id)), None)

        return Response({
            "message": "Nomination reviewed successfully.",
            "institution": updated_item
        }, status=status.HTTP_200_OK)
