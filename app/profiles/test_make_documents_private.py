"""
The one-off command that moves old public documents to private storage.
Cloudinary is mocked, so these tests never touch a real account.
"""
from io import StringIO
from unittest import mock

import cloudinary
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from Afrivate.private_files import PRIVATE_ASSET_TYPE
from profiles.models import Credential, Profile

User = get_user_model()
LEGACY_NAME = 'media/afrivate/credentials/user_1/old-id.pdf'


def _response(status):
    response = mock.Mock()
    response.status_code = status
    response.content = b'%PDF-1.4 fake'
    return response


class MakeDocumentsPrivateTests(TestCase):
    def setUp(self):
        cloudinary.config(cloud_name='testcloud', api_key='123456789012345', api_secret='dummysecret')
        user = User.objects.create_user(
            username='legacy', email='legacy@example.com', password='password123',
            role='pathfinder', is_email_verified=True,
        )
        profile, _ = Profile.objects.update_or_create(user=user, defaults={})
        self.credential = Credential.objects.create(
            profile=profile, document_name='Old ID', document=LEGACY_NAME,
        )

    def _run(self, *args):
        out = StringIO()
        call_command('make_documents_private', *args, stdout=out)
        return out.getvalue()

    def test_dry_run_changes_nothing(self):
        with mock.patch('requests.get', return_value=_response(200)), \
                mock.patch('cloudinary.uploader.upload') as upload, \
                mock.patch('cloudinary.uploader.destroy') as destroy:
            output = self._run()
        upload.assert_not_called()
        destroy.assert_not_called()
        self.assertIn('would-move', output)
        self.assertIn('DRY RUN', output)

    def test_apply_uploads_private_copy_then_deletes_public(self):
        responses = [_response(200), _response(200)]  # public copy, then verified private copy
        with mock.patch('requests.get', side_effect=responses), \
                mock.patch('cloudinary.uploader.upload') as upload, \
                mock.patch('cloudinary.uploader.destroy') as destroy:
            output = self._run('--apply')

        upload.assert_called_once()
        self.assertEqual(upload.call_args.kwargs['type'], PRIVATE_ASSET_TYPE)
        self.assertEqual(upload.call_args.kwargs['public_id'], LEGACY_NAME)

        destroy.assert_called_once()
        self.assertEqual(destroy.call_args.kwargs['type'], 'upload')
        self.assertIn('moved', output)

    def test_public_copy_is_kept_if_private_copy_cannot_be_verified(self):
        responses = [_response(200), _response(404)]  # private copy not readable
        with mock.patch('requests.get', side_effect=responses), \
                mock.patch('cloudinary.uploader.upload') as upload, \
                mock.patch('cloudinary.uploader.destroy') as destroy:
            output = self._run('--apply')

        upload.assert_called_once()
        destroy.assert_not_called()
        self.assertIn('kept-public', output)

    def test_already_private_files_are_skipped(self):
        with mock.patch('requests.get', return_value=_response(404)), \
                mock.patch('cloudinary.uploader.upload') as upload, \
                mock.patch('cloudinary.uploader.destroy') as destroy:
            output = self._run('--apply')

        upload.assert_not_called()
        destroy.assert_not_called()
        self.assertIn('not-public', output)
