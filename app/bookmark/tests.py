from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Opportunity, Bookmark

# Create your tests here.


User = get_user_model()

class BookmarkTests(APITestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(username="testuser", password="password123")
        self.client = APIClient()
        self.client.login(username="testuser", password="password123")

        # Create an opportunity
        self.opportunity = Opportunity.objects.create(
            title="Community Cleanup",
            description="Help clean up the park",
            link="http://example.com/apply",
            is_open=True
        )

    def test_list_opportunities(self):
        url = reverse("opportunity-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Community Cleanup")

    def test_add_bookmark(self):
        url = reverse("bookmark-add")
        response = self.client.post(url, {"opportunity_id": self.opportunity.id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Bookmark.objects.count(), 1)

    def test_prevent_duplicate_bookmark(self):
        url = reverse("bookmark-add")
        self.client.post(url, {"opportunity_id": self.opportunity.id})
        response = self.client.post(url, {"opportunity_id": self.opportunity.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already bookmarked", str(response.data))

    def test_list_bookmarks(self):
        Bookmark.objects.create(user=self.user, opportunity=self.opportunity)
        url = reverse("bookmark-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["opportunity"]["title"], "Community Cleanup")

    def test_delete_bookmark(self):
        bookmark = Bookmark.objects.create(user=self.user, opportunity=self.opportunity)
        url = reverse("bookmark-delete", args=[bookmark.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Bookmark.objects.count(), 0)