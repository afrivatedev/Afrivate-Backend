"""Batch 8: organization representative access, uploader record, expiring
document links, and the lock on name/SCUML after verification.

1. A pending representative applicant cannot see the organization's documents,
   representatives or details, and cannot upload documents.
2. A verified representative can see and upload; the upload records who did it.
3. The organization list ("mine") shows a pending applicant nothing.
4. Signed document links carry an expiry about 15 minutes away.
5. Name and SCUML number cannot change once the organization is verified.
"""
import time
from types import SimpleNamespace
from unittest import mock
from urllib.parse import parse_qs, urlparse

import cloudinary
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from user_database.models import CustomUser
from .models import Organization, OrganizationDocument, OrganizationRepresentative
from .serializers import SIGNED_LINK_TTL_SECONDS, SignedPrivateFileField
from .storage import PrivateRawMediaCloudinaryStorage


class OrgAccessBase(APITestCase):
    def setUp(self):
        cloudinary.config(cloud_name='demo', api_key='123456', api_secret='test-secret-not-real')
        self.creator = CustomUser.objects.create_user(
            username='creator', email='creator@example.com', password='Pass123!',
            role='enabler', is_email_verified=True,
        )
        self.applicant = CustomUser.objects.create_user(
            username='applicant', email='applicant@example.com', password='Pass123!',
            role='enabler', is_email_verified=True,
        )
        self.organization = Organization.objects.create(
            name='Test Org', organization_type='ngo', country='Nigeria', created_by=self.creator,
            tier=Organization.Tier.TIER_3, tier_status=Organization.TierStatus.ACTIVE,
        )
        self.representative = OrganizationRepresentative.objects.create(
            organization=self.organization, user=self.applicant, full_name='Jane Doe',
            role_title='Coordinator', work_email='jane@testorg.com', phone_number='+2348000000000',
            social_media_url='https://linkedin.com/in/janedoe',
        )
        self.doc = OrganizationDocument.objects.create(
            organization=self.organization, document_type=OrganizationDocument.DocumentType.CAC_CERTIFICATE,
            file='org_documents/cac.pdf',
        )
        self.docs_url = reverse('organization-document-list-create', args=[self.organization.id])
        self.reps_url = reverse('organization-representative-list-create', args=[self.organization.id])
        self.detail_url = reverse('organization-detail', args=[self.organization.id])

    def verify_applicant(self):
        self.representative.verification_status = OrganizationRepresentative.VerificationStatus.VERIFIED
        self.representative.save(update_fields=['verification_status'])


class PendingApplicantAccessTests(OrgAccessBase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.applicant)

    def test_pending_applicant_cannot_list_documents(self):
        self.assertEqual(self.client.get(self.docs_url).status_code, status.HTTP_403_FORBIDDEN)

    def test_pending_applicant_cannot_list_representatives(self):
        self.assertEqual(self.client.get(self.reps_url).status_code, status.HTTP_403_FORBIDDEN)

    def test_pending_applicant_cannot_upload_document(self):
        fake = SimpleUploadedFile('cert.pdf', b'%PDF-1.4 fake', content_type='application/pdf')
        response = self.client.post(
            self.docs_url, {'document_type': 'cac_certificate', 'file': fake}, format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_pending_applicant_cannot_see_organization_detail(self):
        self.assertEqual(self.client.get(self.detail_url).status_code, status.HTTP_403_FORBIDDEN)

    def test_pending_applicant_sees_only_own_application(self):
        response = self.client.get(reverse('organization-representative-me'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_mine_list_hides_organization_from_pending_applicant(self):
        response = self.client.get(reverse('organization-mine'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [str(item['id']) for item in response.data]
        self.assertNotIn(str(self.organization.id), ids)


class VerifiedRepresentativeAccessTests(OrgAccessBase):
    def setUp(self):
        super().setUp()
        self.verify_applicant()
        self.client.force_authenticate(user=self.applicant)

    def test_verified_representative_lists_documents(self):
        self.assertEqual(self.client.get(self.docs_url).status_code, status.HTTP_200_OK)

    @mock.patch.object(PrivateRawMediaCloudinaryStorage, '_save', return_value='org_documents/letter.pdf')
    def test_verified_representative_upload_records_uploader(self, _save):
        # Stub the Cloudinary upload so the test never talks to the network.
        fake = SimpleUploadedFile('letter.pdf', b'%PDF-1.4 fake', content_type='application/pdf')
        response = self.client.post(
            self.docs_url, {'document_type': 'letterhead', 'file': fake}, format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        uploaded = OrganizationDocument.objects.get(pk=response.data['id'])
        self.assertEqual(uploaded.uploaded_by_id, self.applicant.id)

    def test_mine_list_shows_organization_to_verified_representative(self):
        response = self.client.get(reverse('organization-mine'))
        ids = [str(item['id']) for item in response.data]
        self.assertIn(str(self.organization.id), ids)


class ExpiringDocumentLinkTests(OrgAccessBase):
    def test_document_link_expires_in_about_fifteen_minutes(self):
        field = SignedPrivateFileField()
        before = int(time.time())
        url = field.to_representation(self.doc.file)
        self.assertIsNotNone(url)
        query = parse_qs(urlparse(url).query)
        self.assertIn('signature', query)
        expires_at = int(query['expires_at'][0])
        self.assertGreaterEqual(expires_at, before + SIGNED_LINK_TTL_SECONDS - 5)
        self.assertLessEqual(expires_at, before + SIGNED_LINK_TTL_SECONDS + 5)

    def test_empty_file_gives_no_link(self):
        self.assertIsNone(SignedPrivateFileField().to_representation(SimpleNamespace(name='')))


class VerifiedOrganizationLockTests(OrgAccessBase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.creator)

    def test_unverified_organization_name_can_change(self):
        response = self.client.patch(self.detail_url, {'name': 'New Name'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_tier_1_organization_name_is_locked(self):
        self.organization.tier = Organization.Tier.TIER_1
        self.organization.save(update_fields=['tier'])
        response = self.client.patch(self.detail_url, {'name': 'Ministry of Everything'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.organization.refresh_from_db()
        self.assertEqual(self.organization.name, 'Test Org')

    def test_verified_organization_description_can_still_change(self):
        self.organization.tier = Organization.Tier.TIER_1
        self.organization.save(update_fields=['tier'])
        response = self.client.patch(self.detail_url, {'description': 'Updated text'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
