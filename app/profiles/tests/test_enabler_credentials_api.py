"""
Tests for EnablerCredentialViewSet CRUD and scoping.
"""
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

# from profiles.models import EnablerCredential

CREDENTIALS_LIST_URL = reverse("profiles:enabler-credential-list")


def create_user(username="u", email="u@example.com", password="Testpass123!", role="enabler"):
    return get_user_model().objects.create_user(email=email, username=username, password=password, role=role)


class EnablerCredentialAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(self.user)
        # Create enabler profile so FK can attach
        self.client.post(reverse("profiles:enabler-profile"), {"name": "Org"}, format="json")

    # def test_create_list_detail_update_delete_credential(self):
    #     # Create
    #     doc = SimpleUploadedFile("id.pdf", b"%PDF-1.4 fake", content_type="application/pdf")
    #     payload = {"name": "Gov ID", "document": doc}
    #     resp = self.client.post(CREDENTIALS_LIST_URL, payload, format="multipart")
    #     self.assertIn(resp.status_code, (200, 201))
    #     cred_id = resp.data.get("id")
    #     self.assertTrue(cred_id)
    #
    #     # List
    #     resp = self.client.get(CREDENTIALS_LIST_URL)
    #     self.assertEqual(resp.status_code, 200)
    #     self.assertGreaterEqual(len(resp.data), 1)
    #
    #     # Detail
    #     detail_url = reverse("profiles:enabler-credential-detail", args=[cred_id])
    #     resp = self.client.get(detail_url)
    #     self.assertEqual(resp.status_code, 200)
    #     self.assertEqual(resp.data.get("name"), "Gov ID")
    #
    #     # Update
    #     resp = self.client.patch(detail_url, {"name": "Gov ID v2"}, format="multipart")
    #     self.assertEqual(resp.status_code, 200)
    #     self.assertEqual(resp.data.get("name"), "Gov ID v2")
    #
    #     # Delete
    #     resp = self.client.delete(detail_url)
    #     self.assertIn(resp.status_code, (200, 204))
    #     # Verify detail returns 404 after deletion
    #     resp = self.client.get(detail_url) # this logs out Not found error to the terinal
    #     self.assertEqual(resp.status_code, 404)

    # def test_scoped_to_current_user(self):
    #     # Create one for self
    #     doc = SimpleUploadedFile("id.pdf", b"fake", content_type="application/pdf")
    #     self.client.post(CREDENTIALS_LIST_URL, {"name": "A", "document": doc}, format="multipart")
    #
    #     # Another user + profile
    #     other = create_user(username="o", email="o@example.com", role="enabler")
    #     client2 = APIClient()
    #     client2.force_authenticate(other)
    #     client2.post(reverse("profiles:enabler-profile"), {"name": "Other Org"}, format="json")
    #     doc2 = SimpleUploadedFile("id2.pdf", b"fake2", content_type="application/pdf")
    #     client2.post(CREDENTIALS_LIST_URL, {"name": "B", "document": doc2}, format="multipart")
    #
    #     # List should show only self's items
    #     resp = self.client.get(CREDENTIALS_LIST_URL)
    #     self.assertEqual(resp.status_code, 200)
    #     self.assertTrue(all(item.get("name") != "B" for item in resp.data))

    # def test_unauthenticated_denied(self):
    #     client = APIClient()
    #     doc = SimpleUploadedFile("id.pdf", b"fake", content_type="application/pdf")
    #     resp = client.post(CREDENTIALS_LIST_URL, {"name": "A", "document": doc}, format="multipart" # this would log out Unauthorized error to the terminal
    #     self.assertEqual(resp.status_code, 401)

    def test_pathfinder_user_cannot_create_enabler_credential(self):
        other = create_user(username="pf", email="pf@example.com", role="pathfinder")
        client2 = APIClient()
        client2.force_authenticate(other)
        # No enabler profile; should 404 on create
        doc = SimpleUploadedFile("id.pdf", b"fake", content_type="application/pdf")
        resp = client2.post(CREDENTIALS_LIST_URL, {"name": "A", "document": doc}, format="multipart") # would log out Not found error to the terminal
        self.assertEqual(resp.status_code, 404)
