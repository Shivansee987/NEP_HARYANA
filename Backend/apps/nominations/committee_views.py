from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, IsAuthenticated
from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator

from .models import Nomination, ClarificationRequest
from .serializers import NominationSerializer, ClarificationRequestSerializer
from .scoring import calculate_nomination_score, AWARD_THRESHOLDS
from .views import HasApprovedCollege

class IsCommitteeRole(BasePermission):
    message = "Committee access required."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "role", None) == "committee"
        )

class CommitteeDashboardStatsView(APIView):
    permission_classes = [IsAuthenticated, IsCommitteeRole]

    def get(self, request):
        # All submitted nominations
        submitted_qs = Nomination.objects.filter(is_submitted=True)
        
        total_assigned = submitted_qs.count()
        pending_reviews = submitted_qs.filter(status__in=['Pending Review', 'Under Review', 'Clarification Requested', 'Responded']).count()
        reviewed = submitted_qs.filter(status__in=['Recommended', 'Not Recommended', 'Approved', 'Rejected']).count()
        clarification_requests = submitted_qs.filter(status='Clarification Requested').count()
        completed = submitted_qs.filter(status__in=['Recommended', 'Not Recommended', 'Approved', 'Rejected']).count()

        # Build recent activity from nomination histories
        all_activities = []
        for nom in submitted_qs:
            history = nom.history or []
            for h in history:
                all_activities.append({
                    "id": nom.id,
                    "college_name": nom.college.name,
                    "status": h.get("status"),
                    "date": h.get("date"),
                    "user": h.get("user")
                })
        
        # Sort activities by date descending
        # Convert date string "dd/mm/yyyy hh:mm" to comparable format if possible, otherwise list recent
        try:
            all_activities.sort(key=lambda x: timezone.datetime.strptime(x["date"], "%d/%m/%Y %H:%M"), reverse=True)
        except Exception:
            pass
            
        recent_activity = all_activities[:10]

        return Response({
            "total_assigned": total_assigned,
            "pending_reviews": pending_reviews,
            "reviewed_submissions": reviewed,
            "clarification_requests": clarification_requests,
            "completed_reviews": completed,
            "recent_activity": recent_activity
        }, status=status.HTTP_200_OK)

class CommitteeAssignedSubmissionsView(APIView):
    permission_classes = [IsAuthenticated, IsCommitteeRole]

    def get(self, request):
        # All submitted nominations
        qs = Nomination.objects.filter(is_submitted=True).order_by("-updated_at")

        # Search
        search = request.query_params.get("search", "")
        if search:
            qs = qs.filter(
                Q(college__name__icontains=search) |
                Q(college__aishe_code__icontains=search) |
                Q(head_name__icontains=search)
            )

        # Filters
        status_filter = request.query_params.get("status", "")
        if status_filter:
            qs = qs.filter(status=status_filter)

        # Sorting
        sort_by = request.query_params.get("sort_by", "")
        if sort_by == "score":
            qs = qs.order_by("-score")
        elif sort_by == "submitted_at":
            qs = qs.order_by("-submitted_at")
        elif sort_by == "updated_at":
            qs = qs.order_by("-updated_at")

        # Pagination
        page_num = request.query_params.get("page", 1)
        page_size = request.query_params.get("page_size", 10)
        paginator = Paginator(qs, page_size)
        page_obj = paginator.get_page(page_num)

        serializer = NominationSerializer(page_obj.object_list, many=True)

        return Response({
            "results": serializer.data,
            "total_count": paginator.count,
            "total_pages": paginator.num_pages,
            "current_page": page_obj.number
        }, status=status.HTTP_200_OK)

class CommitteeReviewDetailView(APIView):
    permission_classes = [IsAuthenticated, IsCommitteeRole]

    def get(self, request, id):
        try:
            nom = Nomination.objects.get(id=id)
        except Nomination.DoesNotExist:
            return Response({"detail": "Nomination not found."}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = NominationSerializer(nom)
        
        # Include clarifications
        clarifications = ClarificationRequest.objects.filter(nomination=nom).order_by("-created_at")
        clar_serializer = ClarificationRequestSerializer(clarifications, many=True)

        return Response({
            "nomination": serializer.data,
            "clarifications": clar_serializer.data
        }, status=status.HTTP_200_OK)

    # Save remarks, observations and scores
    def post(self, request, id):
        try:
            nom = Nomination.objects.get(id=id)
        except Nomination.DoesNotExist:
            return Response({"detail": "Nomination not found."}, status=status.HTTP_404_NOT_FOUND)

        remarks = request.data.get("remarks")
        reviewer_scores = request.data.get("reviewer_scores")
        new_status = request.data.get("status", nom.status)

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

        nom.status = new_status
        nom.save()

        # Add history entry
        timestamp = timezone.now().strftime("%d/%m/%Y %H:%M")
        nom.history = nom.history or []
        nom.history.append({
            "date": timestamp,
            "status": new_status,
            "user": f"{request.user.full_name or request.user.email} (Committee)"
        })
        nom.save()

        return Response({"message": "Review details saved successfully.", "nomination": NominationSerializer(nom).data}, status=status.HTTP_200_OK)

    # Recommend Approval / Rejection / Revision
    def put(self, request, id):
        try:
            nom = Nomination.objects.get(id=id)
        except Nomination.DoesNotExist:
            return Response({"detail": "Nomination not found."}, status=status.HTTP_404_NOT_FOUND)

        recommendation = request.data.get("recommendation") # Approved, Rejected, Sent Back (Under Revision)
        remarks = request.data.get("remarks", "")

        if recommendation not in ["Approved", "Rejected", "Sent Back"]:
            return Response({"detail": "Invalid recommendation type."}, status=status.HTTP_400_BAD_REQUEST)

        status_mapping = {
            "Approved": "Recommended",
            "Rejected": "Not Recommended",
            "Sent Back": "Sent Back"
        }
        mapped_status = status_mapping[recommendation]
        nom.status = mapped_status
        if mapped_status == "Sent Back":
            nom.is_submitted = False  # Allow principal to edit

        if remarks:
            nom.remarks = remarks

        # Add history entry
        timestamp = timezone.now().strftime("%d/%m/%Y %H:%M")
        nom.history = nom.history or []
        nom.history.append({
            "date": timestamp,
            "status": mapped_status,
            "user": f"{request.user.full_name or request.user.email} (Committee Recommendation)"
        })
        nom.save()

        return Response({"message": f"Successfully recommended {recommendation}.", "nomination": NominationSerializer(nom).data}, status=status.HTTP_200_OK)

class CommitteeClarificationRequestView(APIView):
    permission_classes = [IsAuthenticated, IsCommitteeRole]

    def post(self, request, id):
        try:
            nom = Nomination.objects.get(id=id)
        except Nomination.DoesNotExist:
            return Response({"detail": "Nomination not found."}, status=status.HTTP_404_NOT_FOUND)

        query = request.data.get("query")
        fields_to_edit = request.data.get("fields_to_edit", [])

        if not query:
            return Response({"detail": "Query field is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Create clarification request
        clar = ClarificationRequest.objects.create(
            nomination=nom,
            requested_by=request.user,
            query=query,
            fields_to_edit=fields_to_edit,
            status="Pending"
        )

        # Update nomination status
        nom.status = "Clarification Requested"
        
        # Add history entry
        timestamp = timezone.now().strftime("%d/%m/%Y %H:%M")
        nom.history = nom.history or []
        nom.history.append({
            "date": timestamp,
            "status": "Clarification Requested",
            "user": f"{request.user.full_name or request.user.email} (Committee)"
        })
        nom.save()

        return Response({
            "message": "Clarification requested successfully.",
            "clarification": ClarificationRequestSerializer(clar).data
        }, status=status.HTTP_201_CREATED)

# Endpoint for Principal to view and reply to active clarification
class PrincipalClarificationView(APIView):
    permission_classes = [IsAuthenticated, HasApprovedCollege]

    def get(self, request, form_id):
        # Get active clarification
        try:
            nom = Nomination.objects.get(form_id=form_id, college=request.user.college)
        except Nomination.DoesNotExist:
            return Response({"detail": "Nomination not found."}, status=status.HTTP_404_NOT_FOUND)

        clarifications = ClarificationRequest.objects.filter(nomination=nom).order_by("-created_at")
        serializer = ClarificationRequestSerializer(clarifications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, form_id):
        try:
            nom = Nomination.objects.get(form_id=form_id, college=request.user.college)
        except Nomination.DoesNotExist:
            return Response({"detail": "Nomination not found."}, status=status.HTTP_404_NOT_FOUND)

        active_clar = ClarificationRequest.objects.filter(nomination=nom, status="Pending").first()
        if not active_clar:
            return Response({"detail": "No pending clarification request found."}, status=status.HTTP_400_BAD_REQUEST)

        response_text = request.data.get("response")
        if not response_text:
            return Response({"detail": "Response text is required."}, status=status.HTTP_400_BAD_REQUEST)

        active_clar.response = response_text
        active_clar.responded_at = timezone.now()
        active_clar.status = "Responded"
        active_clar.save()

        # Re-lock nomination or change status
        nom.status = "Responded"
        
        # Add history entry
        timestamp = timezone.now().strftime("%d/%m/%Y %H:%M")
        nom.history = nom.history or []
        nom.history.append({
            "date": timestamp,
            "status": "Responded",
            "user": f"{request.user.full_name or request.user.email} (Principal)"
        })
        nom.save()

        return Response({
            "message": "Clarification response submitted successfully.",
            "clarification": ClarificationRequestSerializer(active_clar).data
        }, status=status.HTTP_200_OK)
