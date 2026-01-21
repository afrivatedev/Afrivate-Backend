"""
Tests for the Profile Picture API endpoint.
Covers upload and validation; uses enabler profile as representative since both
profile types share the same profile_pic behavior.
"""
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

import io
from PIL import Image

PROFILE_PIC_URL = reverse("profiles:profile-pic")
ENABLER_PROFILE_URL = reverse("profiles:enabler-profile")


def create_user(username="picuser", email="picuser@example.com", password="Testpass123!", role="enabler"):
    return get_user_model().objects.create_user(email=email, username=username, password=password, role=role)


def make_image_bytesio(fmt="PNG", size=(50, 50), color=(200, 10, 10)):
    f = io.BytesIO()
    image = Image.new("RGBA" if fmt.upper() == "PNG" else "RGB", size=size, color=color)
    image.save(f, fmt)
    f.seek(0)
    return f


class ProfilePictureAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def _create_enabler_profile(self):
        payload = {
            "name": "Org",
            "address": "123 St",
            "city": "City",
            "state": "State",
            "country": "Country",
            "phone_number": "",
            "website": "",
            "about": "",
        }
        return self.client.post(ENABLER_PROFILE_URL, payload, format="json")

    def test_get_profile_picture_without_profile_returns_404(self):
        resp = self.client.get(PROFILE_PIC_URL) # this would log a 404 Not Found error to the terminal
        self.assertEqual(resp.status_code, 404)

    def test_upload_profile_picture_success(self):
        # Ensure profile exists
        resp_prof = self._create_enabler_profile()
        self.assertIn(resp_prof.status_code, (200, 201))

        img_io = make_image_bytesio("PNG")
        image_file = SimpleUploadedFile("avatar.png", img_io.read(), content_type="image/png")

        resp = self.client.patch(PROFILE_PIC_URL, {"profile_pic": image_file}, format="multipart")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("profile_pic", resp.data)

    def test_get_profile_picture_after_upload(self):
        self._create_enabler_profile()
        img_io = make_image_bytesio("PNG")
        image_file = SimpleUploadedFile("avatar.png", img_io.read(), content_type="image/png")
        self.client.patch(PROFILE_PIC_URL, {"profile_pic": image_file}, format="multipart")

        resp = self.client.get(PROFILE_PIC_URL)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("profile_pic", resp.data)
        self.assertTrue(resp.data.get("profile_pic"))

    @override_settings(MAX_PROFILE_PIC_MB=0)  # force any non-empty upload to be too large
    def test_reject_large_image(self):
        self._create_enabler_profile()

        img_io = io.BytesIO()
        img = Image.new("RGBA", size=(50, 50), color=(255, 0, 0, 255))
        img.save(img_io, format="PNG")
        img_io.seek(0)
        image_file = SimpleUploadedFile("too_big.png", img_io.read(), content_type="image/png")

        resp = self.client.patch(PROFILE_PIC_URL, {"profile_pic": image_file}, format="multipart") # would log a 400 Bad Request error to the terminal
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Image too large", str(resp.data))

    def test_reject_invalid_image_type(self):
        self._create_enabler_profile()

        not_image = SimpleUploadedFile("bad.txt", b"not an image", content_type="text/plain")
        resp = self.client.patch(PROFILE_PIC_URL, {"profile_pic": not_image}, format="multipart") # would log a 400 Bad Request error to the terminal
        self.assertEqual(resp.status_code, 400)
        self.assertIn("valid image", str(resp.data).lower())

    def test_url_changes_on_replace(self):
        self._create_enabler_profile()

        # Upload first image
        img_io1 = make_image_bytesio("PNG")
        image_file1 = SimpleUploadedFile("avatar1.png", img_io1.read(), content_type="image/png")
        resp1 = self.client.patch(PROFILE_PIC_URL, {"profile_pic": image_file1}, format="multipart")
        self.assertEqual(resp1.status_code, 200)
        first_url = resp1.data.get("profile_pic")
        self.assertTrue(first_url)

        # Upload second image and ensure URL changes
        img_io2 = make_image_bytesio("PNG", color=(0, 200, 0))
        image_file2 = SimpleUploadedFile("avatar2.png", img_io2.read(), content_type="image/png")
        resp2 = self.client.patch(PROFILE_PIC_URL, {"profile_pic": image_file2}, format="multipart")
        self.assertEqual(resp2.status_code, 200)
        second_url = resp2.data.get("profile_pic")
        self.assertTrue(second_url)
        self.assertNotEqual(first_url, second_url)
