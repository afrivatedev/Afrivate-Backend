"""
Tests for CertificationViewSet CRUD and scoping.
"""
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

CERT_LIST_URL = reverse("profiles:certification-list")


def create_user(username="pf", email="pf@example.com", password="Testpass123!", role="pathfinder"):
    """Helper to create user."""
    return get_user_model().objects.create_user(email=email, username=username, password=password, role=role)


class CertificationAPITests(TestCase):
    """Tests for Pathfinder Certification API CRUD and scoping."""
    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(self.user)
        # Create pathfinder profile so FK can attach
        payload = {"first_name": "Path", "last_name": "Finder"}
        self.client.post(reverse("profiles:pathfinder-profile"), payload, format="json")

    def test_crud_certification(self):
        """Test create, list, detail, update, delete of certifications."""
        # Create
        doc = SimpleUploadedFile("cert.pdf", b"%PDF fake", content_type="application/pdf")
        payload = {"name": "NIN", "document": doc}
        resp = self.client.post(CERT_LIST_URL, payload, format="multipart")
        self.assertIn(resp.status_code, (200, 201))
        cert_id = resp.data.get("id")
        self.assertTrue(cert_id)

        # List
        resp = self.client.get(CERT_LIST_URL)
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.data), 1)

        # Detail
        detail_url = reverse("profiles:certification-detail", args=[cert_id])
        resp = self.client.get(detail_url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("name"), "NIN")

        # Patch
        resp = self.client.patch(detail_url, {"name": "NIN v2"}, format="multipart")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("name"), "NIN v2")

        # Delete
        resp = self.client.delete(detail_url)
        self.assertIn(resp.status_code, (200, 204))
        # Verify detail returns 404 after deletion
        resp = self.client.get(detail_url) # this would log out a Not found error to the terminal
        self.assertEqual(resp.status_code, 404)

    def test_scoped_to_current_user(self):
        # Create one for self
        doc = SimpleUploadedFile("c1.pdf", b"fake1", content_type="application/pdf")
        self.client.post(CERT_LIST_URL, {"name": "A", "document": doc}, format="multipart")

        # Another user + profile
        other = create_user(username="pf2", email="pf2@example.com")
        client2 = APIClient()
        client2.force_authenticate(other)
        client2.post(reverse("profiles:pathfinder-profile"), {"first_name": "P", "last_name": "F"}, format="json")
        doc2 = SimpleUploadedFile("c2.pdf", b"fake2", content_type="application/pdf")
        client2.post(CERT_LIST_URL, {"name": "B", "document": doc2}, format="multipart")

        resp = self.client.get(CERT_LIST_URL)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(all(item.get("name") != "B" for item in resp.data))

    def test_unauthenticated_denied(self):
        client = APIClient()
        doc = SimpleUploadedFile("c.pdf", b"fake", content_type="application/pdf")
        resp = client.post(CERT_LIST_URL, {"name": "X", "document": doc}, format="multipart") # this would log out a Not authenticated error to the terminal
        self.assertEqual(resp.status_code, 401)

    def test_enabler_user_cannot_create_pathfinder_cert(self):
        """Ensure enabler role user cannot create pathfinder certification."""
        other = get_user_model().objects.create_user(email="e@example.com", username="e", password="Testpass123!", role="enabler")
        client2 = APIClient()
        client2.force_authenticate(other)
        doc = SimpleUploadedFile("c.pdf", b"fake", content_type="application/pdf")
        resp = client2.post(CERT_LIST_URL, {"name": "X", "document": doc}, format="multipart") # this would log out a Not found error to the terminal
        self.assertEqual(resp.status_code, 404)
