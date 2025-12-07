from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

import io
from PIL import Image

PROFILE_PIC_URL = reverse("profiles:profile-pic")


def create_user(username="picuser", email="picuser@example.com", password="Testpass123!", role="pathfinder"):
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

    def test_upload_profile_picture_success(self):
        # Create an Enabler profile so profile exists
        enabler_payload = {
            "base_details": {
                "address": "123 St",
                "city": "City",
                "state": "State",
                "country": "Country",
                "contact_email": "user@example.com",
                "phone_number": "",
                "website": "",
                "bio": "",
            },
            "name": "Org",
        }
        self.client.post(reverse("profiles:enabler-profile"), enabler_payload, format="json")

        img_io = make_image_bytesio("PNG")
        image_file = SimpleUploadedFile("avatar.png", img_io.read(), content_type="image/png")

        resp = self.client.patch(PROFILE_PIC_URL, {"profile_pic": image_file}, format="multipart")
        self.assertIn(resp.status_code, (200,))
        self.assertIn("profile_pic", resp.data)
        self.assertTrue(str(resp.data["profile_pic"]).endswith(".png"))

    @override_settings(MAX_PROFILE_PIC_MB=0)  # force any non-empty upload to be too large
    def test_reject_large_image(self):
        enabler_payload = {
            "base_details": {
                "address": "123 St",
                "city": "City",
                "state": "State",
                "country": "Country",
                "contact_email": "user@example.com",
                "phone_number": "",
                "website": "",
                "bio": "",
            },
            "name": "Org",
        }
        self.client.post(reverse("profiles:enabler-profile"), enabler_payload, format="json")

        img_io = io.BytesIO()
        img = Image.new("RGBA", size=(50, 50), color=(255, 0, 0, 255))
        img.save(img_io, format="PNG")
        img_io.seek(0)
        image_file = SimpleUploadedFile("too_big.png", img_io.read(), content_type="image/png")

        resp = self.client.patch(PROFILE_PIC_URL, {"profile_pic": image_file}, format="multipart")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Image too large", str(resp.data))

    def test_reject_invalid_image_type(self):
        enabler_payload = {
            "base_details": {
                "address": "123 St",
                "city": "City",
                "state": "State",
                "country": "Country",
                "contact_email": "user@example.com",
                "phone_number": "",
                "website": "",
                "bio": "",
            },
            "name": "Org",
        }
        self.client.post(reverse("profiles:enabler-profile"), enabler_payload, format="json")

        not_image = SimpleUploadedFile("bad.txt", b"not an image", content_type="text/plain")
        resp = self.client.patch(PROFILE_PIC_URL, {"profile_pic": not_image}, format="multipart")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("valid image", str(resp.data).lower())

    def test_cleanup_on_replace(self):
        enabler_payload = {
            "base_details": {
                "address": "123 St",
                "city": "City",
                "state": "State",
                "country": "Country",
                "contact_email": "user@example.com",
                "phone_number": "",
                "website": "",
                "bio": "",
            },
            "name": "Org",
        }
        self.client.post(reverse("profiles:enabler-profile"), enabler_payload, format="json")

        # Upload first image
        img_io1 = make_image_bytesio("PNG")
        image_file1 = SimpleUploadedFile("avatar1.png", img_io1.read(), content_type="image/png")
        resp1 = self.client.patch(PROFILE_PIC_URL, {"profile_pic": image_file1}, format="multipart")
        self.assertEqual(resp1.status_code, 200)
        first_url = resp1.data.get("profile_pic")
        self.assertTrue(first_url)

        # Upload second image and ensure URL changes (implying cleanup attempted)
        img_io2 = make_image_bytesio("PNG", color=(0, 200, 0))
        image_file2 = SimpleUploadedFile("avatar2.png", img_io2.read(), content_type="image/png")
        resp2 = self.client.patch(PROFILE_PIC_URL, {"profile_pic": image_file2}, format="multipart")
        self.assertEqual(resp2.status_code, 200)
        second_url = resp2.data.get("profile_pic")
        self.assertTrue(second_url)
        self.assertNotEqual(first_url, second_url)
