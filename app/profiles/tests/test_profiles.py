from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()

class ProfileTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.enabler_user = User.objects.create_user(
            username='enabler_user', 
            email='enabler@test.com', 
            password='password123',
            role='enabler'
        )

    def test_enabler_cannot_create_pathfinder_profile(self):
        self.client.force_authenticate(user=self.enabler_user)
        url = reverse('profiles:pathfinder-profile')
        data = {
            "first_name": "Hack",
            "base_details": {"contact_email": "hack@test.com", "address": "...", "state": "...", "country": "..."}
        }
        response = self.client.post(url, data, format='json')
        # This should fail because the user is an 'enabler'
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)