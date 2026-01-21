"""
Tests for SocialLink ViewSets (enabler and pathfinder).
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

ENABLER_SL_LIST = reverse("profiles:enabler-social-link-list")
PATHFINDER_SL_LIST = reverse("profiles:pathfinder-social-link-list")


def create_user(username="u", email="u@example.com", password="Testpass123!", role="enabler"):
    return get_user_model().objects.create_user(email=email, username=username, password=password, role=role)


class EnablerSocialLinksAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_user(role="enabler")
        self.client.force_authenticate(self.user)
        # Create profile
        self.client.post(reverse("profiles:enabler-profile"), {"name": "Enabler"}, format="json")

    def test_crud_enabler_social_links(self):
        # Create
        payload = {"platform_url": "https://linkedin.com/in/enabler"}
        resp = self.client.post(ENABLER_SL_LIST, payload, format="json")
        self.assertIn(resp.status_code, (200, 201))
        sl_id = resp.data.get("id")
        self.assertTrue(sl_id)

        # List
        resp = self.client.get(ENABLER_SL_LIST)
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.data), 1)

        # Detail
        detail_url = reverse("profiles:enabler-social-link-detail", args=[sl_id])
        resp = self.client.get(detail_url)
        self.assertEqual(resp.status_code, 200)

        # Update
        resp = self.client.patch(detail_url, {"platform_url": "https://x.com/enabler"}, format="json")
        self.assertEqual(resp.status_code, 200)

        # Delete
        resp = self.client.delete(detail_url)
        self.assertIn(resp.status_code, (200, 204))

    def test_is_scoped_to_current_user(self):
        # Create one for self
        self.client.post(ENABLER_SL_LIST, {"platform_url": "https://a.com"}, format="json")

        # Another user
        other = create_user(username="o", email="o@example.com", role="enabler")
        client2 = APIClient(); client2.force_authenticate(other)
        client2.post(reverse("profiles:enabler-profile"), {"name": "O"}, format="json")
        client2.post(ENABLER_SL_LIST, {"platform_url": "https://b.com"}, format="json")

        resp = self.client.get(ENABLER_SL_LIST)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(all(item.get("platform_url") != "https://b.com" for item in resp.data))

    def test_unauthenticated_denied(self):
        client = APIClient()
        resp = client.post(ENABLER_SL_LIST, {"platform_url": "https://a.com"}, format="json")
        self.assertEqual(resp.status_code, 401)
        resp = client.get(ENABLER_SL_LIST)
        self.assertEqual(resp.status_code, 401)


class PathfinderSocialLinksAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_user(username="pf", email="pf@example.com", role="pathfinder")
        self.client.force_authenticate(self.user)
        # Create profile
        payload = {"first_name": "P", "last_name": "F"}
        self.client.post(reverse("profiles:pathfinder-profile"), payload, format="json")

    def test_crud_pathfinder_social_links(self):
        # Create requires platform_name + url for pathfinder
        payload = {"platform_name": "Twitter", "platform_url": "https://twitter.com/pf"}
        resp = self.client.post(PATHFINDER_SL_LIST, payload, format="json")
        self.assertIn(resp.status_code, (200, 201))
        sl_id = resp.data.get("id")

        # List
        resp = self.client.get(PATHFINDER_SL_LIST)
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.data), 1)

        # Detail
        detail_url = reverse("profiles:pathfinder-social-link-detail", args=[sl_id])
        resp = self.client.get(detail_url)
        self.assertEqual(resp.status_code, 200)

        # Update
        resp = self.client.patch(detail_url, {"platform_name": "X"}, format="json")
        self.assertEqual(resp.status_code, 200)

        # Delete
        resp = self.client.delete(detail_url)
        self.assertIn(resp.status_code, (200, 204))

    def test_scoped_to_current_user(self):
        # Create for self
        self.client.post(PATHFINDER_SL_LIST, {"platform_name": "A", "platform_url": "https://a.com"}, format="json")

        # Another user
        other = create_user(username="pf2", email="pf2@example.com", role="pathfinder")
        client2 = APIClient(); client2.force_authenticate(other)
        client2.post(reverse("profiles:pathfinder-profile"), {"first_name": "P", "last_name": "F"}, format="json")
        client2.post(PATHFINDER_SL_LIST, {"platform_name": "B", "platform_url": "https://b.com"}, format="json")

        resp = self.client.get(PATHFINDER_SL_LIST)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(all(item.get("platform_name") != "B" for item in resp.data))

    def test_unauthenticated_denied(self):
        client = APIClient()
        resp = client.post(PATHFINDER_SL_LIST, {"platform_name": "X", "platform_url": "https://x.com"}, format="json")
        self.assertEqual(resp.status_code, 401)
        resp = client.get(PATHFINDER_SL_LIST)
        self.assertEqual(resp.status_code, 401)
