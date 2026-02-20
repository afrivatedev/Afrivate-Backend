from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

User = get_user_model()

class ProfilePermissionTests(APITestCase):
    def setUp(self):
        self.enabler_user = User.objects.create_user(
            username='enabler_test', email='enabler@test.com', password='pass', role='enabler'
        )
        self.pathfinder_user = User.objects.create_user(
            username='pathfinder_test', email='pathfinder@test.com', password='pass', role='pathfinder'
        )

    def test_enabler_cannot_access_pathfinder_endpoint(self):
        """Ensure enablers get a validation error or permission denied on pathfinder url"""
        self.client.force_authenticate(user=self.enabler_user)
        url = reverse('profiles:pathfinder-profile')
        response = self.client.get(url)
        # Based on your view logic, this should fail because the user role != pathfinder
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_pathfinder_cannot_access_enabler_endpoint(self):
        self.client.force_authenticate(user=self.pathfinder_user)
        url = reverse('profiles:enabler-profile')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_skills_replaces_old_ones(self):
        self.client.force_authenticate(user=self.pathfinder_user)
        url = reverse('profiles:pathfinder-profile')
        
        # First update: 2 skills

        data = {
            "first_name": "John",
            "last_name": "Doe", 
            "title": "Dev",
            "base_details": {
                "contact_email": "t@t.com", 
                "address": "123 Street", 
                "state": "Lagos", 
                "country": "Nigeria"
                # "city": "Ikeja"  
            },
            "skills": [{"name": "Python"}, {"name": "Django"}]
        }

        self.client.put(url, data, format='json')
        
        # Second update: Replace with 1 new skill
        new_data = data.copy()
        new_data["skills"] = [{"name": "React"}]
        self.client.put(url, new_data, format='json')
        
        # Verify the skills count is 1 (old ones deleted)
        from profiles.models import PathfinderSkill
        count = PathfinderSkill.objects.filter(pathfinder__profile__user=self.pathfinder_user).count()
        self.assertEqual(count, 1)