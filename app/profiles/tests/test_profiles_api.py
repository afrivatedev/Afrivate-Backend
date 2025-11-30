from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from rest_framework.test import APIClient
from django.urls import reverse

import io
from PIL import Image


class ProfilesAPITestCase(TestCase):
    """Integration-style tests for the profiles endpoints (pathfinder & enabler)."""

    def setUp(self):
        self.client = APIClient()
        self.register_url = "/api/auth/register/"
        self.login_url = "/api/auth/login/"
        self.pathfinder_url = "/api/profile/pathfinderprofile/"
        self.enabler_url = "/api/profile/enablerprofile/"
        self.pathfinder_pic_url = "/api/profile/pathfinderprofile/profile-pic/"
        self.enabler_pic_url = "/api/profile/enableprofile/profile-pic/"

    def _register_and_login(self, username="testuser", email="testuser@example.com", password="Testpass123!", role="pathfinder"):
        """Register a user via the API and return access token and basic user info."""
        register_payload = {
            "username": username,
            "email": email,
            "password": password,
            "password2": password,
            "role": role,
        }
        # Register
        resp = self.client.post(self.register_url, register_payload, format="json")
        self.assertIn(resp.status_code, (201,))

        # Login to get tokens
        login_payload = {"username_or_email": email, "password": password}
        resp = self.client.post(self.login_url, login_payload, format="json")
        self.assertEqual(resp.status_code, 200)
        access = resp.data.get("access")
        self.assertIsNotNone(access)

        return access

    def _auth_client(self, access_token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        return self.client

    def _make_test_image_file(self, name="test.png"):
        """Create an in-memory PNG image and return a SimpleUploadedFile suitable for upload."""
        f = io.BytesIO()
        image = Image.new('RGBA', size=(50, 50), color=(155, 0, 0))
        image.save(f, 'PNG')
        f.seek(0)
        return SimpleUploadedFile(name, f.read(), content_type='image/png')

    def test_pathfinder_profile_crud_and_picture_upload(self):
        access = self._register_and_login(role="pathfinder")
        client = self._auth_client(access)

        # Create profile
        payload = {
            "firstname": "John",
            "lastname": "Doe",
            "address": "123 Street",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
            "email": "testuser@example.com",
            "social_links": [
                {"platform_name": "Twitter", "platform_url": "https://twitter.com/johndoe"},
            ],
        }
        resp = client.post(self.pathfinder_url, payload, format="json")
        self.assertIn(resp.status_code, (200, 201))

        # Retrieve profile
        resp = client.get(self.pathfinder_url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("firstname"), "John")
        # verify nested social links were created and returned
        social_links = resp.data.get("social_links")
        self.assertIsNotNone(social_links)
        self.assertIsInstance(social_links, list)
        self.assertGreaterEqual(len(social_links), 1)
        self.assertEqual(social_links[0].get("platform_name"), "Twitter")

        # Update profile (partial)
        resp = client.patch(self.pathfinder_url, {"city": "Abuja"}, format="json")
        self.assertIn(resp.status_code, (200,))
        self.assertEqual(resp.data.get("city"), "Abuja")

        # Upload profile picture (PUT multipart)
        image = self._make_test_image_file()
        resp = client.put(self.pathfinder_pic_url, {"profile_pic": image}, format="multipart")
        self.assertIn(resp.status_code, (200,))
        self.assertIn("profile_pic", resp.data)

        # Retrieve pic endpoint should still return
        resp = client.get(self.pathfinder_pic_url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("profile_pic", resp.data)

    def test_enabler_profile_crud_and_picture_upload(self):
        access = self._register_and_login(username="enabler1", email="enabler@example.com", role="enabler")
        client = self._auth_client(access)

        payload = {
            "name": "Enabler Co",
            "address": "456 Road",
            "city": "Accra",
            "state": "Greater Accra",
            "country": "Ghana",
            "email": "enabler@example.com",
            "social_links": [
                {"platform_name": "LinkedIn", "platform_url": "https://linkedin.com/in/enabler"}
            ],
        }
        resp = client.post(self.enabler_url, payload, format="json")
        self.assertIn(resp.status_code, (200, 201))

        # Retrieve
        resp = client.get(self.enabler_url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("name"), "Enabler Co")
        # verify nested social links for enabler
        e_links = resp.data.get("social_links")
        self.assertIsNotNone(e_links)
        self.assertIsInstance(e_links, list)
        self.assertGreaterEqual(len(e_links), 1)
        self.assertEqual(e_links[0].get("platform_name"), "LinkedIn")

        # Update (full)
        payload_update = payload.copy()
        payload_update["city"] = "Kumasi"
        resp = client.put(self.enabler_url, payload_update, format="json")
        self.assertIn(resp.status_code, (200,))
        self.assertEqual(resp.data.get("city"), "Kumasi")

        # Upload profile picture
        image = self._make_test_image_file(name="enabler.png")
        resp = client.put(self.enabler_pic_url, {"profile_pic": image}, format="multipart")
        self.assertIn(resp.status_code, (200,))
        self.assertIn("profile_pic", resp.data)

    def test_unauthorized_access_denied(self):
        # No token set
        resp = self.client.get(self.pathfinder_url)
        self.assertIn(resp.status_code, (401, 403))
