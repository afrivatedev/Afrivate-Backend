from django.utils import timezone
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
import uuid

from .models import EngagementRecord, TaskEntry, Certificate
from .serializers import (
    EngagementRecordSerializer,
    TaskEntrySerializer,
    CertificateSerializer,
    PublicCertificateSerializer
)
from user_database.permissions import IsPathfinderUser, IsEnablerUser

class EngagementRecordViewSet(viewsets.ModelViewSet):
    serializer_class = EngagementRecordSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'pathfinder':
            return EngagementRecord.objects.filter(volunteer=user)
        elif user.role == 'enabler':
            return EngagementRecord.objects.filter(organization=user)
        return EngagementRecord.objects.none()

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsEnablerUser])
    def pending_attestations(self, request):
        """Organization only: View all engagements waiting for attestation."""
        qs = self.get_queryset().filter(status='pending_attestation')
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsPathfinderUser])
    def request_attestation(self, request, pk=None):
        """Volunteer only: Submit engagement for review."""
        engagement = self.get_object()
        if engagement.status != 'in_progress' and engagement.status != 'disputed':
            return Response({'error': 'Can only request attestation for in progress or disputed engagements.'}, status=status.HTTP_400_BAD_REQUEST)
        
        engagement.status = 'pending_attestation'
        engagement.save()
        # TODO: Trigger notification to organization here
        return Response({'status': 'Attestation requested.'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsEnablerUser])
    def attest(self, request, pk=None):
        """Organization only: Confirm the details are accurate and lock the record."""
        engagement = self.get_object()
        if engagement.status != 'pending_attestation':
            return Response({'error': 'Can only attest engagements that are pending attestation.'}, status=status.HTTP_400_BAD_REQUEST)
        
        engagement.status = 'attested'
        engagement.attested_by_user = request.user
        engagement.attested_at = timezone.now()
        
        # Optionally save any notes
        notes = request.data.get('attestation_notes', '')
        if notes:
            engagement.attestation_notes = notes
            
        engagement.save()
        
        # TODO: Trigger notification to volunteer here
        return Response({'status': 'Engagement attested successfully.'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsEnablerUser])
    def dispute(self, request, pk=None):
        """Organization only: Flag engagement details as incorrect."""
        engagement = self.get_object()
        if engagement.status != 'pending_attestation':
            return Response({'error': 'Can only dispute engagements that are pending attestation.'}, status=status.HTTP_400_BAD_REQUEST)
        
        reason = request.data.get('dispute_reason')
        if not reason:
            return Response({'error': 'dispute_reason is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
        engagement.status = 'disputed'
        engagement.dispute_reason = reason
        engagement.save()
        
        # TODO: Trigger notification to volunteer
        return Response({'status': 'Engagement disputed.'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsPathfinderUser])
    def generate_certificate(self, request, pk=None):
        """Volunteer only: Generate certificate once attested."""
        from django.conf import settings
        engagement = self.get_object()
        if engagement.status != 'attested':
            return Response({'error': 'Can only generate a certificate for attested engagements.'}, status=status.HTTP_400_BAD_REQUEST)
        
        if hasattr(engagement, 'certificate'):
            return Response({'error': 'Certificate already exists.'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Basic certificate creation for now. PDF generation can be done async or here.
        cert = Certificate.objects.create(
            engagement_record=engagement
        )
        # Construct verification URL
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        cert.verification_page_url = f"{frontend_url}/verify/{cert.id}"
        cert.save()
        
        return Response(CertificateSerializer(cert).data)

class TaskEntryViewSet(viewsets.ModelViewSet):
    serializer_class = TaskEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        engagement_id = self.kwargs.get('engagement_record_id')
        if not engagement_id:
            return TaskEntry.objects.none()
            
        # Ensure user has access to the engagement
        user = self.request.user
        if user.role == 'pathfinder':
            qs = EngagementRecord.objects.filter(id=engagement_id, volunteer=user)
        else:
            qs = EngagementRecord.objects.filter(id=engagement_id, organization=user)
            
        if not qs.exists():
            return TaskEntry.objects.none()
            
        return TaskEntry.objects.filter(engagement_record_id=engagement_id)

    def perform_create(self, serializer):
        from rest_framework import serializers
        engagement_id = self.kwargs.get('engagement_record_id')
        engagement = get_object_or_404(EngagementRecord, id=engagement_id)
        
        # Can only add tasks if in progress or disputed
        if engagement.status not in ['in_progress', 'disputed', 'pending_attestation']:
             raise serializers.ValidationError("Cannot add tasks to locked engagement.")
             
        # Only volunteer can add tasks in our current MVP, or coordinator can add if they need to
        logged_by = 'volunteer' if self.request.user.role == 'pathfinder' else 'coordinator'
        
        serializer.save(engagement_record=engagement, logged_by=logged_by)

class PublicCertificateVerificationView(generics.RetrieveAPIView):
    """
    Publicly accessible endpoint to retrieve certificate details for verification.
    No authentication required.
    """
    queryset = Certificate.objects.filter(revoked=False)
    serializer_class = PublicCertificateSerializer
    permission_classes = [AllowAny]
    lookup_field = 'id'

class DownloadCertificatePDFView(generics.RetrieveAPIView):
    """
    Endpoint to download the generated PDF.
    """
    queryset = Certificate.objects.filter(revoked=False)
    permission_classes = [AllowAny]
    lookup_field = 'id'
    
    def get(self, request, *args, **kwargs):
        cert = self.get_object()
        if not cert.pdf_file:
            # Fallback or generate on the fly
            # We will implement xhtml2pdf generation here
            return Response({'error': 'PDF not generated yet.'}, status=status.HTTP_404_NOT_FOUND)
        
        # For a Cloudinary backed FileField, return the URL to redirect to
        return Response({'pdf_url': cert.pdf_file.url})
