from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, IsAuthenticated
from django.utils import timezone
import os
import io

from apps.evidence.validators import (
    ContentValidator,
    FilenameValidator,
    FileTooLargeError,
    FileValidationError,
)

from .models import Nomination, ClarificationRequest
from .serializers import NominationSerializer
from .scoring import calculate_nomination_score

from .scoring import AWARD_THRESHOLDS

class NominationConfigView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'award_thresholds': AWARD_THRESHOLDS
        }, status=status.HTTP_200_OK)


class HasApprovedCollege(BasePermission):
    """
    Nominations belong to one college: only a user whose binding to that college has been approved may read or edit
    them. Pending, rejected and unbound accounts (university users, administrators, committee members) are refused;
    there is no fallback college (S-01).
    """
    message = "Your account is not linked to an approved college."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated
            and getattr(user, 'college_id', None)
            and getattr(user, 'institution_status', None) == 'VERIFIED'
        )


class NominationEvidenceUploadView(APIView):
    """Validate nomination evidence before forwarding it to Cloudinary."""
    # Only an approved college principal may upload nomination evidence (S-01).
    permission_classes = [IsAuthenticated, HasApprovedCollege]

    def post(self, request):
        uploaded_file = request.FILES.get('file')
        if uploaded_file is None:
            return Response(
                {'error': 'bad_request', 'detail': 'A file is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            safe_name, extension = FilenameValidator.validate_and_sanitize(uploaded_file.name)
            limit = (
                ContentValidator.get_max_pdf_size()
                if extension == 'pdf' else ContentValidator.get_max_file_size()
            )
            declared_size = getattr(uploaded_file, 'size', None)
            if declared_size is not None and declared_size > limit:
                raise FileTooLargeError(
                    'The PDF file must not exceed 5 MB. Please choose a smaller file.'
                    if extension == 'pdf'
                    else f'Uploaded file exceeds the maximum limit of {limit} bytes.'
                )

            chunks = []
            total_size = 0
            for chunk in uploaded_file.chunks():
                total_size += len(chunk)
                if total_size > limit:
                    raise FileTooLargeError(
                        'The PDF file must not exceed 5 MB. Please choose a smaller file.'
                        if extension == 'pdf'
                        else f'Uploaded file exceeds the maximum limit of {limit} bytes.'
                    )
                chunks.append(chunk)
            content = b''.join(chunks)
            detected_mime, _ = ContentValidator.validate_content(content, extension)
            if extension == 'pdf' or detected_mime == 'application/pdf':
                ContentValidator.validate_pdf_structure(content)
        except FileTooLargeError as exc:
            return Response(
                {'error': 'file_too_large', 'detail': str(exc)},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )
        except FileValidationError as exc:
            return Response(
                {'error': 'bad_request', 'detail': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME', '').strip()
        upload_preset = os.environ.get('CLOUDINARY_UPLOAD_PRESET_NAME', '').strip()
        if not cloud_name or not upload_preset:
            return Response(
                {'error': 'storage_unavailable', 'detail': 'Document storage is temporarily unavailable. Please try again later.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            import cloudinary
            import cloudinary.uploader

            cloudinary.config(cloud_name=cloud_name)
            stream = io.BytesIO(content)
            stream.name = safe_name
            result = cloudinary.uploader.unsigned_upload(
                stream, upload_preset, resource_type='auto', filename_override=safe_name,
            )
        except Exception:
            return Response(
                {'error': 'storage_unavailable', 'detail': 'Document storage is temporarily unavailable. Please try again later.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {'url': result['secure_url'], 'original_filename': safe_name},
            status=status.HTTP_201_CREATED,
        )


def get_user_college(user):
    return user.college

class NominationListView(APIView):
    permission_classes = [IsAuthenticated, HasApprovedCollege]

    def get(self, request):
        user = request.user
        college = get_user_college(user)
            
        nom_id = "nep-excellence-nomination-2025"
        
        # Check current status
        try:
            nom = Nomination.objects.get(form_id=nom_id, college=college)
            if nom.is_submitted:
                status_str = "submitted"
            else:
                status_str = "draft"
        except Nomination.DoesNotExist:
            status_str = "not_started"
            
        forms = [
            {
                "id": nom_id,
                "title": "Haryana State NEP 2020 Implementation Excellence Award — Nomination Form 2025",
                "issued_by": "HSHEC",
                "academic_session": "2024-25",
                "total_marks": 100,
                "total_indicators": 20,
                "status": status_str
            }
        ]
        return Response(forms, status=status.HTTP_200_OK)

class NominationDetailView(APIView):
    permission_classes = [IsAuthenticated, HasApprovedCollege]

    def get(self, request, form_id):
        user = request.user
        college = get_user_college(user)
            
        # Get or create
        nom, created = Nomination.objects.get_or_create(
            form_id=form_id,
            college=college,
            defaults={
                'answers': {},
                'score': 0,
                'award_category': 'No Award'
            }
        )
        
        serializer = NominationSerializer(nom)
        return Response(serializer.data, status=status.HTTP_200_OK)

class NominationSaveView(APIView):
    permission_classes = [IsAuthenticated, HasApprovedCollege]

    def post(self, request, form_id):
        user = request.user
        college = get_user_college(user)
            
        try:
            nom = Nomination.objects.get(form_id=form_id, college=college)
        except Nomination.DoesNotExist:
            return Response({'detail': 'Nomination not found.'}, status=status.HTTP_404_NOT_FOUND)
            
        if nom.is_submitted:
            if nom.status == "Clarification Requested":
                active_req = ClarificationRequest.objects.filter(nomination=nom, status="Pending").first()
                if not active_req:
                    return Response({'detail': 'This nomination has already been submitted and cannot be edited.'}, status=status.HTTP_400_BAD_REQUEST)
                
                allowed_fields = active_req.fields_to_edit or []
                incoming_answers = request.data.get('answers', {})
                
                # Check for changes outside allowed fields
                for key, val in incoming_answers.items():
                    current_val = nom.answers.get(key)
                    if current_val != val and key not in allowed_fields:
                        return Response({
                            'detail': f'You are only allowed to edit fields requested for clarification: {", ".join(allowed_fields)}'
                        }, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'detail': 'This nomination has already been submitted and cannot be edited.'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Update basic info fields safely (avoid overwriting with empty/null values if they are already populated)
        head_name = request.data.get('head_name')
        if head_name is not None and head_name != "":
            nom.head_name = head_name
            
        head_contact = request.data.get('head_contact')
        if head_contact is not None and head_contact != "":
            nom.head_contact = head_contact
            
        address = request.data.get('address')
        if address is not None and address != "":
            nom.address = address
            
        institution_type = request.data.get('institution_type')
        if institution_type is not None and institution_type != "":
            nom.institution_type = institution_type
        
        # Save answers
        answers = request.data.get('answers', nom.answers)
        nom.answers = answers
        
        # Recalculate score
        score, category = calculate_nomination_score(answers)
        nom.score = score
        nom.award_category = category
        if not nom.status or nom.status == "Sent Back":
            nom.status = "Draft"
        nom.save()
        
        serializer = NominationSerializer(nom)
        return Response({
            'message': 'Draft saved successfully.',
            'nomination': serializer.data
        }, status=status.HTTP_200_OK)

class NominationSubmitView(APIView):
    permission_classes = [IsAuthenticated, HasApprovedCollege]

    def post(self, request, form_id):
        user = request.user
        college = get_user_college(user)
            
        try:
            nom = Nomination.objects.get(form_id=form_id, college=college)
        except Nomination.DoesNotExist:
            return Response({'detail': 'Nomination not found.'}, status=status.HTTP_404_NOT_FOUND)
            
        if nom.is_submitted:
            return Response({'detail': 'This nomination has already been submitted.'}, status=status.HTTP_400_BAD_REQUEST)
            
        # 1. Validate basic info
        basic_fields = [nom.head_name, nom.head_contact, nom.address, nom.institution_type]
        if not all(basic_fields):
            return Response({'detail': 'Please fill all fields in Section 1 (Institution Basic Info).'}, status=status.HTTP_400_BAD_REQUEST)
            
        # 2. Check at least 10 indicators filled
        answers = nom.answers or {}
        filled_count = 0
        for i in range(1, 21):
            key = f"indicator_{i}"
            ind_ans = answers.get(key, {})
            # Either value is set, or for indicator 20, percentage is provided
            if ind_ans.get('value') or (i == 20 and ind_ans.get('percentage') not in [None, '']):
                filled_count += 1
                
        if filled_count < 10:
            return Response({'detail': f'You must fill out at least 10 out of the 20 indicators (currently filled: {filled_count}).'}, status=status.HTTP_400_BAD_REQUEST)
            
        # 3. Check declaration checkbox
        declaration_accepted = request.data.get('declaration_accepted', False)
        if not declaration_accepted:
            return Response({'detail': 'You must accept the declaration before submitting.'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Perform submission locking
        score, category = calculate_nomination_score(answers)
        nom.score = score
        nom.award_category = category
        nom.is_submitted = True
        nom.submitted_at = timezone.now()
        nom.status = "Pending Review"
        
        # Append history log
        timestamp = timezone.now().strftime("%d/%m/%Y %H:%M")
        nom.history = nom.history or []
        nom.history.append({
            "date": timestamp,
            "status": "Pending Review",
            "user": f"{user.full_name or user.username} (Principal)"
        })
        
        nom.save()
        
        # Invalidate dashboard stats cache on submission
        try:
            from apps.admin_panel.services import invalidate_dashboard_stats_cache
            invalidate_dashboard_stats_cache()
        except Exception:
            pass
        
        serializer = NominationSerializer(nom)
        return Response({
            'message': 'Nomination submitted successfully. Form is now locked.',
            'nomination': serializer.data
        }, status=status.HTTP_200_OK)


class MySubmissionsListView(APIView):
    permission_classes = [IsAuthenticated, HasApprovedCollege]

    def get(self, request):
        user = request.user
        college = get_user_college(user)
        nominations = Nomination.objects.filter(college=college).order_by('-updated_at')
        serializer = NominationSerializer(nominations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

