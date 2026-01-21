"""
Comprehensive tests for the profile endpoints (enabler and pathfinder).
Uses force_authenticate for all authenticated flows.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

ENABLER_PROFILE_URL = reverse("profiles:enabler-profile")
PATHFINDER_PROFILE_URL = reverse("profiles:pathfinder-profile")


def create_user(
    username="testuser",
    email="testuser@example.com",
    password="Testpass123!",
    role="enabler",
):
    return get_user_model().objects.create_user(
        email=email, username=username, password=password, role=role
    )


class EnablerProfileAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_user(role="enabler")
        self.client.force_authenticate(self.user)

    def test_create_enabler_profile_success(self):
        payload = {
            "name": "Enabler Co",
            "address": "456 Road",
            "city": "Accra",
            "state": "Greater Accra",
            "country": "Ghana",
            "phone_number": "1234567890",
            "website": "https://enablerco.com",
            "about": "We enable things",
        }
        resp = self.client.post(ENABLER_PROFILE_URL, payload, format="json")
        self.assertIn(resp.status_code, (200, 201))
        # Serializer returns flat fields
        self.assertEqual(resp.data.get("name"), payload["name"])
        self.assertEqual(resp.data.get("city"), payload["city"])

    def test_get_enabler_profile_after_create(self):
        self.client.post(ENABLER_PROFILE_URL, {"name": "Enabler Co"}, format="json")
        resp = self.client.get(ENABLER_PROFILE_URL)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("name"), "Enabler Co")

    def test_update_enabler_profile(self):
        self.client.post(ENABLER_PROFILE_URL, {"name": "Enabler Co"}, format="json")
        update_payload = {
            "name": "New Enabler",
            "city": "Kumasi",
        }
        resp = self.client.put(ENABLER_PROFILE_URL, update_payload, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("name"), "New Enabler")
        self.assertEqual(resp.data.get("city"), "Kumasi")

    def test_partial_update_enabler_profile(self):
        self.client.post(ENABLER_PROFILE_URL, {"name": "Enabler Co"}, format="json")
        resp = self.client.patch(ENABLER_PROFILE_URL, {"city": "Tema"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("city"), "Tema")

    def test_unauthenticated_access_denied(self):
        client = APIClient()  # unauthenticated
        resp = client.post(ENABLER_PROFILE_URL, {"name": "X"}, format="json") # this will log unauthenticated access to the terminal
        self.assertEqual(resp.status_code, 401)
        resp = client.get(ENABLER_PROFILE_URL)
        self.assertEqual(resp.status_code, 401)

    def test_enabler_with_profile_cannot_create_pathfinder_profile(self):
        """A user who already has an Enabler profile should not be able to create a Pathfinder profile."""
        # create enabler profile first
        resp = self.client.post(ENABLER_PROFILE_URL, {"name": "Enabler Co"}, format="json")
        self.assertIn(resp.status_code, (200, 201))

        # attempt to create a pathfinder profile for the same user
        pf_payload = {"first_name": "Path", "last_name": "Finder"}
        resp2 = self.client.post(PATHFINDER_PROFILE_URL, pf_payload, format="json")
        # view raises Http404 when trying to create the opposite profile
        self.assertEqual(resp2.status_code, 404)


class PathfinderProfileAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_user(username="pf", email="pf@example.com", role="pathfinder")
        self.client.force_authenticate(self.user)

    def test_create_pathfinder_profile_success(self):
        payload = {
            "first_name": "Path",
            "last_name": "Finder",
            "other_name": "The Seeker",
            "address": "456 Road",
            "city": "Ikeja",
            "state": "Lagos",
            "country": "Nigeria",
            "phone_number": "+2347012244534",
            "website": "https://pathfinderad.com",
            "about": "put me on bro",
        }
        resp = self.client.post(PATHFINDER_PROFILE_URL, payload, format="json")
        self.assertIn(resp.status_code, (200, 201))
        self.assertEqual(resp.data.get("first_name"), payload["first_name"])
        self.assertEqual(resp.data.get("city"), payload["city"])  # flat field

    def test_get_pathfinder_profile_after_create(self):
        self.client.post(PATHFINDER_PROFILE_URL, {"first_name": "Path", "last_name": "Finder"}, format="json")
        resp = self.client.get(PATHFINDER_PROFILE_URL)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("first_name"), "Path")

    def test_update_pathfinder_profile(self):
        self.client.post(PATHFINDER_PROFILE_URL, {"first_name": "P", "last_name": "F"}, format="json")
        update_payload = {
            "first_name": "New",
            "last_name": "Name",
            "city": "VI",
        }
        resp = self.client.put(PATHFINDER_PROFILE_URL, update_payload, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("first_name"), "New")
        self.assertEqual(resp.data.get("city"), "VI")

    def test_partial_update_pathfinder_profile(self):
        self.client.post(PATHFINDER_PROFILE_URL, {"first_name": "P", "last_name": "F"}, format="json")
        resp = self.client.patch(PATHFINDER_PROFILE_URL, {"city": "Ibadan"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("city"), "Ibadan")

    def test_unauthenticated_access_denied(self):
        client = APIClient()
        resp = client.post(PATHFINDER_PROFILE_URL, {"first_name": "A", "last_name": "B"}, format="json")
        self.assertEqual(resp.status_code, 401)
        resp = client.get(PATHFINDER_PROFILE_URL)
        self.assertEqual(resp.status_code, 401)

    def test_pathfinder_with_profile_cannot_create_enabler_profile(self):
        """A user who already has a Pathfinder profile should not be able to create an Enabler profile."""
        # create pathfinder profile first
        resp = self.client.post(PATHFINDER_PROFILE_URL, {"first_name": "Path", "last_name": "Finder"}, format="json")
        self.assertIn(resp.status_code, (200, 201))

        # attempt to create an enabler profile for the same user
        en_payload = {"name": "Enabler Co"}
        resp2 = self.client.post(ENABLER_PROFILE_URL, en_payload, format="json")
        # view raises Http404 when trying to create the opposite profile
        self.assertEqual(resp2.status_code, 404)
