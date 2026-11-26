"""
Hours, dates and task logs must be frozen once an engagement is waiting for
sign-off or has been signed off. Otherwise a volunteer can change the hours
shown on a certificate after the organisation has confirmed them.
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from engagements.models import EngagementRecord, TaskEntry
from opportunities.models import Opportunity

User = get_user_model()


class HoursLockingTests(TestCase):
    def setUp(self):
        self.org = User.objects.create_user(
            username='org', email='org@example.com', password='password123',
            role='enabler', is_email_verified=True,
        )
        self.volunteer = User.objects.create_user(
            username='vol', email='vol@example.com', password='password123',
            role='pathfinder', is_email_verified=True,
        )
        self.stranger = User.objects.create_user(
            username='stranger', email='stranger@example.com', password='password123',
            role='pathfinder', is_email_verified=True,
        )
        self.opportunity = Opportunity.objects.create(
            title='Test Opp', link='https://example.com/test',
            created_by=self.org, role_skill_tags=['Leadership'],
        )
        self.record = EngagementRecord.objects.create(
            volunteer=self.volunteer, organization=self.org,
            opportunity=self.opportunity, role_title='Test Opp',
            total_hours=Decimal('10.00'), end_date=date(2026, 1, 31),
            status='in_progress',
        )
        self.client = APIClient()
        self.detail_url = f'/api/engagements/engagements/{self.record.id}/'
        self.tasks_url = f'/api/engagements/engagements/{self.record.id}/tasks/'

    def _as(self, user):
        self.client.force_authenticate(user=user)

    def _request_and_attest(self):
        self._as(self.volunteer)
        self.assertEqual(
            self.client.post(f'{self.detail_url}request_attestation/').status_code, 200)
        self._as(self.org)
        self.assertEqual(
            self.client.post(f'{self.detail_url}attest/', {}, format='json').status_code, 200)
        self.record.refresh_from_db()

    # --- hours and dates on the engagement record -------------------------

    def test_volunteer_can_correct_hours_while_in_progress(self):
        self._as(self.volunteer)
        response = self.client.patch(self.detail_url, {'total_hours': '12.50'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.record.refresh_from_db()
        self.assertEqual(self.record.total_hours, Decimal('12.50'))

    def test_hours_cannot_change_while_pending_attestation(self):
        self._as(self.volunteer)
        self.client.post(f'{self.detail_url}request_attestation/')
        response = self.client.patch(self.detail_url, {'total_hours': '99'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.record.refresh_from_db()
        self.assertEqual(self.record.total_hours, Decimal('10.00'))

    def test_hours_and_end_date_cannot_change_after_attestation(self):
        self._request_and_attest()
        self._as(self.volunteer)
        response = self.client.patch(
            self.detail_url, {'total_hours': '99', 'end_date': '2030-01-01'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.record.refresh_from_db()
        self.assertEqual(self.record.total_hours, Decimal('10.00'))
        self.assertEqual(self.record.end_date, date(2026, 1, 31))

    def test_organisation_cannot_change_hours(self):
        self._as(self.org)
        response = self.client.patch(self.detail_url, {'total_hours': '1'}, format='json')
        self.assertEqual(response.status_code, 403)
        self.record.refresh_from_db()
        self.assertEqual(self.record.total_hours, Decimal('10.00'))

    def test_attestation_notes_and_dispute_reason_are_not_writable(self):
        self._as(self.volunteer)
        response = self.client.patch(self.detail_url, {
            'attestation_notes': 'I was great',
            'dispute_reason': 'Not a real dispute',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.record.refresh_from_db()
        self.assertIsNone(self.record.attestation_notes)
        self.assertIsNone(self.record.dispute_reason)

    def test_attested_record_cannot_be_deleted(self):
        self._request_and_attest()
        self._as(self.volunteer)
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, 400)
        self.assertTrue(EngagementRecord.objects.filter(id=self.record.id).exists())

    # --- task log ----------------------------------------------------------

    def test_volunteer_can_log_task_while_in_progress(self):
        self._as(self.volunteer)
        response = self.client.post(
            self.tasks_url, {'date': '2026-01-05', 'description': 'Helped at the clinic'},
            format='json')
        self.assertEqual(response.status_code, 201)

    def test_cannot_log_task_on_someone_elses_record(self):
        self._as(self.stranger)
        response = self.client.post(
            self.tasks_url, {'date': '2026-01-05', 'description': 'Padding hours'},
            format='json')
        self.assertEqual(response.status_code, 404)
        self.assertFalse(TaskEntry.objects.filter(engagement_record=self.record).exists())

    def test_cannot_log_task_while_pending_attestation(self):
        self._as(self.volunteer)
        self.client.post(f'{self.detail_url}request_attestation/')
        response = self.client.post(
            self.tasks_url, {'date': '2026-01-05', 'description': 'Late entry'},
            format='json')
        self.assertEqual(response.status_code, 400)

    def test_task_cannot_be_edited_or_deleted_after_attestation(self):
        task = TaskEntry.objects.create(
            engagement_record=self.record, date=date(2026, 1, 5),
            description='Original', logged_by='volunteer',
        )
        self._request_and_attest()
        self._as(self.volunteer)

        edit = self.client.patch(
            f'{self.tasks_url}{task.id}/', {'description': 'Changed'}, format='json')
        self.assertEqual(edit.status_code, 400)

        delete = self.client.delete(f'{self.tasks_url}{task.id}/')
        self.assertEqual(delete.status_code, 400)

        task.refresh_from_db()
        self.assertEqual(task.description, 'Original')

    # --- the normal flow still works ---------------------------------------

    def test_normal_flow_still_issues_certificate(self):
        self._request_and_attest()
        self._as(self.volunteer)
        response = self.client.post(f'{self.detail_url}generate_certificate/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(hasattr(self.record, 'certificate'))
