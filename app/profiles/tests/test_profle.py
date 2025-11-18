from django.test.testcases import TestCase
from django.contrib.auth import get_user_model

from rest_framework.test import APIClient

def create_user(email="testuser@gmail.com", password="Testuser2025+"):
    """create user helper function"""
    user = get_user_model().objects.create_user(email=email, password=password)
    return user

class ProfilesTest(TestCase):
    """test to create user profile on signup."""
    def SetUp(self):
        self.client = APIClient()
        self.user = create_user()
