"""
Privacy tests for profiles and documents.

1. Only verified users can see a profile at all. Verified users see contact email and phone,
   never the street address and never documents. Unverified users are refused.
2. Owners must still see their own details (regression).
3. Documents (ID files, credentials, CVs) are private: uploads are stored as
   'authenticated' and the links we hand out expire.
"""
import re
import time
from unittest import mock

import cloudinary
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from Afrivate.private_files import (
    PRIVATE_ASSET_TYPE,
    PRIVATE_LINK_TTL_SECONDS,
    PrivateRawMediaCloudinaryStorage,
    signed_private_url,
)
from profiles.models import Credential, EnablerProfileExtra, PathfinderProfileExtra, Profile
from profiles.serializers import CredentialSerializer

User = get_user_model()

SECRET_PHONE = '+2348000000111'
SECRET_EMAIL = 'private.person@example.com'
SECRET_ADDRESS = '12 Secret Street, Lagos'
SECRET_GMAIL = 'hidden.gmail@example.com'
STORED_DOC = 'media/afrivate/credentials/user_1/abc.pdf'


def _configure_cloudinary():
    # Dummy values: we only build and sign links here, we never call Cloudinary.
    cloudinary.config(cloud_name='testcloud', api_key='123456789012345', api_secret='dummysecret')


class PublicProfilePrivacyTests(TestCase):
    def setUp(self):
        _configure_cloudinary()
        self.owner = User.objects.create_user(
            username='pf', email='pf@example.com', password='password123',
            role='pathfinder', is_email_verified=True,
        )
        self.viewer = User.objects.create_user(
            username='viewer', email='viewer@example.com', password='password123',
            role='pathfinder', is_email_verified=True,
        )
        self.unverified = User.objects.create_user(
            username='new', email='new@example.com', password='password123',
            role='pathfinder', is_email_verified=False,
        )
        self.org = User.objects.create_user(
            username='org', email='org@example.com', password='password123',
            role='enabler', is_email_verified=True,
        )

        profile, _ = Profile.objects.update_or_create(user=self.owner, defaults={
            'contact_email': SECRET_EMAIL, 'phone_number': SECRET_PHONE,
            'address': SECRET_ADDRESS, 'state': 'Lagos', 'country': 'Nigeria',
            'bio': 'Public bio',
        })
        PathfinderProfileExtra.objects.update_or_create(profile=profile, defaults={
            'first_name': 'Ada', 'last_name': 'Okafor', 'title': 'Designer',
            'gmail': SECRET_GMAIL,
        })
        Credential.objects.create(
            profile=profile, document_name='National ID', document=STORED_DOC,
        )

        org_profile, _ = Profile.objects.update_or_create(user=self.org, defaults={
            'contact_email': 'hr@org.example.com', 'phone_number': '+2348000000222',
            'address': 'Org Street 1', 'website': 'https://org.example.com',
        })
        EnablerProfileExtra.objects.update_or_create(profile=org_profile, defaults={
            'name': 'Org Ltd', 'employees': 20, 'role': 'HR',
        })

        self.client = APIClient()

    def _public_pathfinder(self, viewer):
        self.client.force_authenticate(user=viewer)
        return self.client.get(f'/api/profile/pathfinderprofile/user/{self.owner.id}/')

    def test_verified_user_sees_pathfinder_contact_email_and_phone(self):
        response = self._public_pathfinder(self.viewer)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['base_details']['contact_email'], SECRET_EMAIL)
        self.assertEqual(response.data['base_details']['phone_number'], SECRET_PHONE)
        self.assertEqual(response.data['gmail'], SECRET_GMAIL)

    def test_verified_user_never_sees_street_address(self):
        response = self._public_pathfinder(self.viewer)
        body = response.content.decode()
        self.assertNotIn(SECRET_ADDRESS, body)
        self.assertNotIn('address', body)

    def test_other_user_cannot_see_documents_on_pathfinder_profile(self):
        response = self._public_pathfinder(self.viewer)
        self.assertNotIn('credentials', response.data)
        self.assertNotIn('cloudinary', response.content.decode())

    def test_public_pathfinder_still_shows_public_information(self):
        response = self._public_pathfinder(self.viewer)
        self.assertEqual(response.data['first_name'], 'Ada')
        self.assertEqual(response.data['title'], 'Designer')
        self.assertEqual(response.data['base_details']['state'], 'Lagos')
        self.assertEqual(response.data['base_details']['bio'], 'Public bio')

    def test_verified_user_sees_organisation_contact_email_and_phone(self):
        self.client.force_authenticate(user=self.viewer)
        response = self.client.get(f'/api/profile/enablerprofile/user/{self.org.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], 'Org Ltd')
        self.assertEqual(response.data['base_details']['contact_email'], 'hr@org.example.com')
        self.assertEqual(response.data['base_details']['phone_number'], '+2348000000222')
        self.assertEqual(response.data['base_details']['website'], 'https://org.example.com')

    def test_organisation_street_address_stays_hidden(self):
        self.client.force_authenticate(user=self.viewer)
        response = self.client.get(f'/api/profile/enablerprofile/user/{self.org.id}/')
        self.assertNotIn('Org Street 1', response.content.decode())

    def test_unverified_user_still_blocked(self):
        response = self._public_pathfinder(self.unverified)
        self.assertEqual(response.status_code, 403)

    def test_unverified_user_blocked_from_organisation_contact(self):
        self.client.force_authenticate(user=self.unverified)
        response = self.client.get(f'/api/profile/enablerprofile/user/{self.org.id}/')
        self.assertEqual(response.status_code, 403)

    def test_owner_still_sees_own_details(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get('/api/profile/pathfinderprofile/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['base_details']['contact_email'], SECRET_EMAIL)
        self.assertEqual(response.data['base_details']['phone_number'], SECRET_PHONE)
        self.assertEqual(len(response.data['credentials']), 1)


class PrivateDocumentTests(TestCase):
    def setUp(self):
        _configure_cloudinary()

    def test_document_link_is_signed_private_and_expiring(self):
        link = signed_private_url(STORED_DOC)
        self.assertIn('/raw/download?', link)
        self.assertIn(f'type={PRIVATE_ASSET_TYPE}', link)
        self.assertIn('signature=', link)
        self.assertNotIn('/raw/upload/', link)

        expires_at = int(re.search(r'expires_at=(\d+)', link).group(1))
        now = int(time.time())
        self.assertGreater(expires_at, now)
        self.assertLessEqual(expires_at - now, PRIVATE_LINK_TTL_SECONDS + 5)

    def test_credential_serializer_returns_private_link(self):
        user = User.objects.create_user(
            username='cred', email='cred@example.com', password='password123',
            role='pathfinder', is_email_verified=True,
        )
        profile, _ = Profile.objects.update_or_create(user=user, defaults={})
        credential = Credential.objects.create(
            profile=profile, document_name='ID', document=STORED_DOC,
        )
        data = CredentialSerializer(credential).data
        self.assertIn(f'type={PRIVATE_ASSET_TYPE}', data['document'])
        self.assertIn('expires_at=', data['document'])

    def test_document_field_uses_private_storage(self):
        self.assertIsInstance(
            Credential._meta.get_field('document').storage, PrivateRawMediaCloudinaryStorage)

    def test_uploads_are_stored_as_authenticated(self):
        storage = PrivateRawMediaCloudinaryStorage()
        with mock.patch('Afrivate.private_files.cloudinary.uploader.upload') as upload:
            upload.return_value = {'public_id': 'media/afrivate/resumes/user_1/x.pdf'}
            storage._upload('media/afrivate/resumes/user_1/x.pdf', b'%PDF')
        options = upload.call_args.kwargs
        self.assertEqual(options['type'], PRIVATE_ASSET_TYPE)
        self.assertEqual(options['resource_type'], 'raw')

    def test_delete_targets_the_private_asset(self):
        storage = PrivateRawMediaCloudinaryStorage()
        with mock.patch('Afrivate.private_files.cloudinary.uploader.destroy') as destroy:
            destroy.return_value = {'result': 'ok'}
            self.assertTrue(storage.delete('media/afrivate/resumes/user_1/x.pdf'))
        self.assertEqual(destroy.call_args.kwargs['type'], PRIVATE_ASSET_TYPE)

    def test_storage_url_is_never_the_public_address(self):
        url = PrivateRawMediaCloudinaryStorage().url(STORED_DOC)
        self.assertIn(f'type={PRIVATE_ASSET_TYPE}', url)
        self.assertNotIn('/raw/upload/', url)

    def test_no_public_fallback_when_link_cannot_be_made(self):
        """If signing fails, the response must be empty, not the public address."""
        user = User.objects.create_user(
            username='cred2', email='cred2@example.com', password='password123',
            role='pathfinder', is_email_verified=True,
        )
        profile, _ = Profile.objects.update_or_create(user=user, defaults={})
        credential = Credential.objects.create(
            profile=profile, document_name='ID', document=STORED_DOC,
        )
        with mock.patch('profiles.serializers.signed_private_url', side_effect=Exception('boom')):
            data = CredentialSerializer(credential).data
        self.assertIsNone(data['document'])


class ApplicationResumeLinkTests(TestCase):
    """The application list must hand out the same private link as the credential endpoint."""

    def test_list_resume_link_is_private_and_expiring(self):
        from types import SimpleNamespace
        from applications.serializers import ApplicationListSerializer

        _configure_cloudinary()
        obj = SimpleNamespace(profile_resume=SimpleNamespace(document=SimpleNamespace(name=STORED_DOC)))
        link = ApplicationListSerializer().get_profile_resume_url(obj)

        self.assertIsNotNone(link)
        self.assertIn('/raw/download?', link)
        self.assertIn(f'type={PRIVATE_ASSET_TYPE}', link)
        self.assertIn('expires_at=', link)
        self.assertNotIn('/raw/upload/', link)