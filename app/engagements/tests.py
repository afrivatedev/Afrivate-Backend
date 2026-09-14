from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from opportunities.models import Opportunity
from applications.models import Application
from engagements.models import EngagementRecord, Certificate
from django.urls import reverse
import uuid

User = get_user_model()

class EngagementTests(TestCase):
    def setUp(self):
        self.enabler = User.objects.create_user(
            username='org',
            email='org@example.com',
            password='password123',
            role='enabler',
            is_email_verified=True
        )
        self.pathfinder = User.objects.create_user(
            username='vol',
            email='vol@example.com',
            password='password123',
            role='pathfinder',
            is_email_verified=True
        )
        self.opportunity = Opportunity.objects.create(
            title='Test Opp',
            link='https://example.com/test',
            created_by=self.enabler,
            role_skill_tags=['Leadership']
        )
        self.application = Application.objects.create(
            user=self.pathfinder,
            opportunity=self.opportunity,
            status='pending'
        )
        self.client = APIClient()

    def test_engagement_record_auto_creation(self):
        # Change status to accepted
        self.application.status = 'accepted'
        self.application.save()

        # Check if EngagementRecord was created
        self.assertTrue(EngagementRecord.objects.filter(volunteer=self.pathfinder, opportunity=self.opportunity).exists())
        record = EngagementRecord.objects.get(volunteer=self.pathfinder, opportunity=self.opportunity)
        self.assertEqual(record.status, 'in_progress')
        self.assertEqual(record.organization, self.enabler)

    def test_request_attestation(self):
        # Create record directly for API testing
        record = EngagementRecord.objects.create(
            volunteer=self.pathfinder,
            organization=self.enabler,
            opportunity=self.opportunity,
            role_title=self.opportunity.title,
            status='in_progress'
        )
        
        self.client.force_authenticate(user=self.pathfinder)
        url = f'/api/engagements/engagements/{record.id}/request_attestation/'
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        
        record.refresh_from_db()
        self.assertEqual(record.status, 'pending_attestation')

    def test_attest_engagement(self):
        record = EngagementRecord.objects.create(
            volunteer=self.pathfinder,
            organization=self.enabler,
            opportunity=self.opportunity,
            role_title=self.opportunity.title,
            status='pending_attestation'
        )
        
        self.client.force_authenticate(user=self.enabler)
        url = f'/api/engagements/engagements/{record.id}/attest/'
        response = self.client.post(url, {'attestation_notes': 'Great job'})
        self.assertEqual(response.status_code, 200)
        
        record.refresh_from_db()
        self.assertEqual(record.status, 'attested')
        self.assertEqual(record.attested_by_user, self.enabler)

    def test_generate_certificate(self):
        record = EngagementRecord.objects.create(
            volunteer=self.pathfinder,
            organization=self.enabler,
            opportunity=self.opportunity,
            role_title=self.opportunity.title,
            status='attested'
        )
        
        self.client.force_authenticate(user=self.pathfinder)
        url = f'/api/engagements/engagements/{record.id}/generate_certificate/'
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        
        self.assertTrue(Certificate.objects.filter(engagement_record=record).exists())
