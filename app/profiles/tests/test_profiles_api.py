"""
Tests for the profiles API endpoints, covering both pathfinder and enabler profiles.
"""


from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


from rest_framework.test import APIClient




PATHFINDER_PROFILE_URL = reverse("profiles:pathfinder-profile")
ENABLER_PROFILE_URL = reverse("profiles:enabler-profile")



def create_user(username="testuser",
                email="testuser@example.com",
                password="Testpass123!",
                role="enabler"):
    """create user helper function for tests"""
    return get_user_model().objects.create_user(email=email,username=username,password=password,role=role)

ENABLER_PAYLOAD = {
            "base_details":{
                         "address": "456 Road",
                         "city": "Accra",
                         "state": "Greater Accra",
                         "country": "Ghana",
                         "contact_email": "enabler@example.com",
                         "phone_number": "1234567890",
                         "website": "https://enablerco.com",
                         "bio": "We enable things",
            },
            "social_links": [
                {"platform_name": "LinkedIn", "platform_url": "https://linkedin.com/in/enabler"}
            ],
            "name": "Enabler Co",
        }

PATHFINDER_PAYLOAD = {
            "base_details":{
                         "address": "456 Road",
                         "city": "Ikeja",
                         "state": "Lagos",
                         "country": "Nigeria",
                         "contact_email": "pathfinder@example.com",
                         "phone_number": "+2347012244534",
                         "website": "https://pathfinderad.com",
                         "bio": "put me on bro",
                        },
            "social_links": [
                {"platform_name":"Twitter", "platform_url": "https://twitter.com/pathfinder"},
                {"platform_name":"GitHub", "platform_url": "https://github.com/pathfinder"},
            ],
            "first_name": "Path",
            "last_name": "Finder",
            "other_name": "The Seeker",
}

class TestEnablerProfileAPITestCase(TestCase):
    """Integration-style tests for the profiles endpoints (pathfinder & enabler)."""

    def setUp(self):
        self.client = APIClient()
        user = create_user(role="enabler")
        self.client.force_authenticate(user=user) # this helps us avoid the unnecessary registration/login steps for each test

    def test_crud_on_enabler_profile(self):
        """Testing full CRUD operations on the enabler profile"""
        resp = self.client.post(ENABLER_PROFILE_URL, ENABLER_PAYLOAD, format="json")
        self.assertIn(resp.status_code, (200, 201))
        self.assertIn("base_details", resp.data.keys())
        self.assertIn("social_links", resp.data.keys())
        self.assertIn("name", resp.data.keys())

        # verify nested social links for enabler
        social_links = resp.data.get("social_links")
        self.assertIsNotNone(social_links)
        self.assertIsInstance(social_links, list)
        self.assertGreaterEqual(len(social_links), 1)
        self.assertEqual(social_links[0].get("platform_name"), "LinkedIn")

        # verify profile nested data
        base_details_data = resp.data.get("base_details")
        self.assertIsNotNone(base_details_data)
        self.assertEqual(base_details_data.get("city"), "Accra")

        # test retrieval of enabler profile
        resp = self.client.get(ENABLER_PROFILE_URL)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("name"), "Enabler Co")

        # test full update
        payload_update = ENABLER_PAYLOAD.copy()
        payload_update["base_details"]["city"] = "Kumasi"
        resp = self.client.put(ENABLER_PROFILE_URL, payload_update, format="json")
        self.assertIn(resp.status_code, (200,))
        base_details_data = resp.data.get("base_details")
        self.assertEqual(base_details_data["city"], "Kumasi")

        # test partial update
        partial_payload  = {
            "name":"new enalbler"
        }
        resp = self.client.patch(ENABLER_PROFILE_URL, partial_payload, format="json")
        name = resp.data.get("name")
        self.assertIsNotNone(name)

    def test_enabler_profile_creation_without_base_details_fails(self):
        """Test that creating an enabler profile without base_details fails"""
        invalid_payload = ENABLER_PAYLOAD.copy()
        invalid_payload.pop("base_details")
        resp = self.client.post(ENABLER_PROFILE_URL, invalid_payload, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_enabler_profile_creation_without_social_links_succeeds(self):
        """Test that creating an enabler profile without social_links succeeds"""
        payload = ENABLER_PAYLOAD.copy()
        payload.pop("social_links")
        resp = self.client.post(ENABLER_PROFILE_URL, payload, format="json")
        self.assertIn(resp.status_code, (200, 201))
        self.assertIn("base_details", resp.data.keys())
        self.assertIn("social_links", resp.data.keys())
        self.assertEqual(len(resp.data.get("social_links")), 0)
        self.assertIn("name", resp.data.keys())

    def test_only_enabler_user_cannot_create_pathfinder_profile(self):
        """Test that a user with enabler role cannot create a pathfinder profile"""
        resp = self.client.post(PATHFINDER_PROFILE_URL, PATHFINDER_PAYLOAD, format="json")
        self.assertEqual(resp.status_code, 400)

class TestPathfinderProfileAPITestCase(TestCase):
    """Integration-style tests for the pathfinder profile endpoint."""
    def setUp(self):
        self.client = APIClient()
        user = create_user(role="pathfinder")
        self.client.force_authenticate(user=user) # this helps us avoid the unnecessary registration/login steps for each test

    def test_crud_on_pathfinder_profile(self):
        """Testing full CRUD operations on the pathfinder profile"""
        resp = self.client.post(PATHFINDER_PROFILE_URL, PATHFINDER_PAYLOAD, format="json")
        self.assertIn(resp.status_code, (200, 201))
        self.assertIn("base_details", resp.data.keys())
        self.assertIn("social_links", resp.data.keys())
        self.assertIn("first_name", resp.data.keys())

        # verify nested social links for enabler
        social_links = resp.data.get("social_links")
        self.assertIsNotNone(social_links)
        self.assertIsInstance(social_links, list)
        self.assertEqual(len(social_links), 2)
        self.assertEqual(social_links[1].get("platform_name"), "GitHub")

        # verify profile nested data
        base_details_data = resp.data.get("base_details")
        self.assertIsNotNone(base_details_data)
        self.assertEqual(base_details_data.get("city"), "Ikeja")

        # test retrieval of enabler profile
        resp = self.client.get(PATHFINDER_PROFILE_URL)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("other_name"), "The Seeker")

        # test full update
        payload_update = PATHFINDER_PAYLOAD.copy()
        payload_update["base_details"]["city"] = "Victoria Island"
        resp = self.client.put(PATHFINDER_PROFILE_URL, payload_update, format="json")
        self.assertIn(resp.status_code, (200,))
        base_details_data = resp.data.get("base_details")
        self.assertEqual(base_details_data["city"], "Victoria Island")

        # test partial update
        partial_payload  = {
            "base_details":{
                         "address": "46 Nnamdi Azikiwe Hostel",
                         "city": "Ibadan",
                         "state": "Oyo",
                         "country": "Nigeria",
                         "contact_email": "pathfinder@example.com",
                         "phone_number": "+2347012244534",
                         "website": "https://pathfinderad.com",
                         "bio": "put me on bro",
                        },
            "social_links": [
                {"platform_name":"LinkedIn", "platform_url": "https://linkedin.com/pathfinder"},
                 ],
        }
        resp = self.client.patch(PATHFINDER_PROFILE_URL, partial_payload, format="json")
        social_links = resp.data.get("social_links")
        self.assertIsInstance(social_links, list)
        self.assertEqual(len(social_links), 1)
        self.assertEqual(social_links[0].get("platform_name"), "LinkedIn")
        address = resp.data.get("base_details").get("address")
        self.assertIsNotNone(address)
        self.assertEqual(address, "46 Nnamdi Azikiwe Hostel")

    def test_pathfinder_profile_creation_without_base_details_fails(self):
        """Test that creating a pathfinder profile without base_details fails"""
        invalid_payload = PATHFINDER_PAYLOAD.copy()
        invalid_payload.pop("base_details")
        resp = self.client.post(PATHFINDER_PROFILE_URL, invalid_payload, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_pathfinder_profile_creation_without_social_links_succeeds(self):
        """Test that creating a pathfinder profile without social_links succeeds"""
        payload = PATHFINDER_PAYLOAD.copy()
        payload.pop("social_links")
        resp = self.client.post(PATHFINDER_PROFILE_URL, payload, format="json")
        self.assertIn(resp.status_code, (200, 201))
        self.assertIn("base_details", resp.data.keys())
        self.assertIn("social_links", resp.data.keys())
        self.assertEqual(len(resp.data.get("social_links")), 0)
        self.assertIn("first_name", resp.data.keys())

    def test_only_pathfinder_user_cannot_create_enabler_profile(self):
        """Test that a user with pathfinder role cannot create an enabler profile"""
        resp = self.client.post(ENABLER_PROFILE_URL, ENABLER_PAYLOAD, format="json")
        self.assertEqual(resp.status_code, 400)


