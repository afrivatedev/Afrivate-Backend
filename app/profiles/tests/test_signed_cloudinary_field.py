"""
Tests for SignedCloudinaryFileField and its usage in CredentialSerializer
and ApplicationSerializer.

These tests verify that:
1. The field generates a signed Cloudinary URL for a valid stored file.
2. The field returns None when the value is empty / has no name.
3. The field falls back to the plain URL when Cloudinary signing raises an
   exception, so responses are never silently broken.
4. CredentialSerializer produces a signed URL for the document field.
5. ApplicationSerializer produces a signed URL for the resume field.
6. ApplicationListSerializer produces a signed URL for the resume field.
"""

from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from profiles.serializers import (
    CredentialSerializer,
    SignedCloudinaryFileField,
)
from applications.serializers import ApplicationSerializer, ApplicationListSerializer

User = get_user_model()


class SignedCloudinaryFileFieldTests(TestCase):
    """Unit tests for SignedCloudinaryFileField.to_representation."""

    def _make_file_value(self, name):
        """Return a mock file-field value with a given name."""
        mock_file = MagicMock()
        mock_file.name = name
        mock_file.url = f"https://res.cloudinary.com/test_cloud/raw/upload/{name}"
        return mock_file

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    @patch("profiles.serializers.cloudinary.utils.cloudinary_url")
    def test_returns_signed_url_for_valid_file(self, mock_cloudinary_url):
        """
        When a file has a name, the field should call cloudinary_url with
        sign_url=True and return the resulting URL.
        """
        signed = "https://res.cloudinary.com/test_cloud/raw/upload/s--SIG--/resumes/cv.pdf"
        mock_cloudinary_url.return_value = (signed, {})

        field = SignedCloudinaryFileField()
        result = field.to_representation(self._make_file_value("resumes/cv.pdf"))

        self.assertEqual(result, signed)
        mock_cloudinary_url.assert_called_once_with(
            "resumes/cv.pdf",
            resource_type="raw",
            type="upload",
            sign_url=True,
            secure=True,
        )

    # ------------------------------------------------------------------
    # Null / empty cases
    # ------------------------------------------------------------------

    def test_returns_none_for_falsy_value(self):
        """The field should return None when value itself is falsy (e.g. None)."""
        field = SignedCloudinaryFileField(required=False, allow_null=True)
        self.assertIsNone(field.to_representation(None))

    def test_returns_none_when_name_is_empty(self):
        """The field should return None when value.name is an empty string."""
        mock_file = MagicMock()
        mock_file.name = ""
        field = SignedCloudinaryFileField(required=False, allow_null=True)
        self.assertIsNone(field.to_representation(mock_file))

    # ------------------------------------------------------------------
    # Fallback on exception
    # ------------------------------------------------------------------

    @patch("profiles.serializers.cloudinary.utils.cloudinary_url", side_effect=Exception("signing failed"))
    def test_falls_back_to_plain_url_on_exception(self, _mock):
        """
        When cloudinary_url raises an exception the field should fall back to
        the plain storage URL instead of propagating the error.
        """
        plain_url = "https://res.cloudinary.com/test_cloud/raw/upload/resumes/cv.pdf"
        file_value = self._make_file_value("resumes/cv.pdf")
        file_value.url = plain_url

        field = SignedCloudinaryFileField()
        result = field.to_representation(file_value)

        self.assertEqual(result, plain_url)

    @patch("profiles.serializers.cloudinary.utils.cloudinary_url", side_effect=Exception("signing failed"))
    def test_falls_back_to_absolute_url_when_request_present(self, _mock):
        """
        When cloudinary_url fails and a request is in the serializer context,
        the fallback should use request.build_absolute_uri().
        """
        plain_url = "https://res.cloudinary.com/test_cloud/raw/upload/resumes/cv.pdf"
        file_value = self._make_file_value("resumes/cv.pdf")
        file_value.url = plain_url

        mock_request = MagicMock()
        mock_request.build_absolute_uri.return_value = plain_url

        field = SignedCloudinaryFileField()
        field._context = {"request": mock_request}  # inject context

        result = field.to_representation(file_value)

        self.assertEqual(result, plain_url)


class CredentialSerializerDocumentFieldTests(TestCase):
    """Integration tests verifying CredentialSerializer uses SignedCloudinaryFileField."""

    @patch("profiles.serializers.cloudinary.utils.cloudinary_url")
    def test_credential_document_url_is_signed(self, mock_cloudinary_url):
        """CredentialSerializer should return a signed URL for the document field."""
        signed = "https://res.cloudinary.com/test_cloud/raw/upload/s--SIG--/afrivate/credentials/user_1/doc.pdf"
        mock_cloudinary_url.return_value = (signed, {})

        mock_file = MagicMock()
        mock_file.name = "afrivate/credentials/user_1/doc.pdf"
        mock_file.url = "https://res.cloudinary.com/test_cloud/raw/upload/afrivate/credentials/user_1/doc.pdf"

        mock_credential = MagicMock()
        mock_credential.id = 1
        mock_credential.document_name = "Government ID"
        mock_credential.document = mock_file
        mock_credential.is_verified = False

        serializer = CredentialSerializer(mock_credential)
        data = serializer.data

        self.assertEqual(data["document"], signed)
        mock_cloudinary_url.assert_called_once_with(
            "afrivate/credentials/user_1/doc.pdf",
            resource_type="raw",
            type="upload",
            sign_url=True,
            secure=True,
        )

    @patch("profiles.serializers.cloudinary.utils.cloudinary_url")
    def test_credential_document_is_none_when_empty(self, mock_cloudinary_url):
        """CredentialSerializer should return None for the document field when empty."""
        mock_file = MagicMock()
        mock_file.name = ""

        mock_credential = MagicMock()
        mock_credential.id = 1
        mock_credential.document_name = "Government ID"
        mock_credential.document = mock_file
        mock_credential.is_verified = False

        serializer = CredentialSerializer(mock_credential)
        data = serializer.data

        self.assertIsNone(data["document"])
        mock_cloudinary_url.assert_not_called()


class ApplicationSerializerResumeFieldTests(TestCase):
    """Integration tests verifying ApplicationSerializer uses SignedCloudinaryFileField."""

    def _make_application_mock(self, resume_name):
        """Return a mock Application instance."""
        mock_file = MagicMock()
        mock_file.name = resume_name
        mock_file.url = f"https://res.cloudinary.com/test_cloud/raw/upload/{resume_name}"

        mock_app = MagicMock()
        mock_app.id = 1
        mock_app.user.username = "testuser"
        mock_app.user.id = 1
        mock_app.user.email = "test@example.com"
        mock_app.opportunity.title = "Engineer"
        mock_app.resume = mock_file
        mock_app.status = "pending"
        mock_app.cover_letter = "Hello"
        mock_app.applied_at = "2026-01-01T00:00:00Z"
        mock_app.reviewed_at = None
        return mock_app

    @patch("profiles.serializers.cloudinary.utils.cloudinary_url")
    def test_application_resume_url_is_signed(self, mock_cloudinary_url):
        """ApplicationListSerializer should return a signed URL for the resume field."""
        signed = "https://res.cloudinary.com/test_cloud/raw/upload/s--SIG--/resumes/cv.pdf"
        mock_cloudinary_url.return_value = (signed, {})

        mock_app = self._make_application_mock("resumes/cv.pdf")

        serializer = ApplicationListSerializer(mock_app)
        data = serializer.data

        self.assertEqual(data["resume"], signed)

    @patch("profiles.serializers.cloudinary.utils.cloudinary_url")
    def test_application_resume_is_none_when_empty(self, mock_cloudinary_url):
        """ApplicationListSerializer should return None for resume when not present."""
        mock_file = MagicMock()
        mock_file.name = ""

        mock_app = self._make_application_mock("")
        mock_app.resume = mock_file

        serializer = ApplicationListSerializer(mock_app)
        data = serializer.data

        self.assertIsNone(data["resume"])
        mock_cloudinary_url.assert_not_called()
