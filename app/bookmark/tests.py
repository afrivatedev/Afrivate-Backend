from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Opportunity, Bookmark
from django.utils import timezone
from datetime import timedelta

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


class OpportunityTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='pathfinder', password='password123')
        self.other_user = User.objects.create_user(username='enabler', password='password123')
        self.client.force_authenticate(user=self.user)
        
        self.opportunity = Opportunity.objects.create(
            title="Old Opportunity",
            opportunity_type="internship",
            description="Test description",
            link="https://google.com",
            created_by=self.user
        )

    def test_create_opportunity_sets_user(self):
        """Test if the creator is automatically assigned."""
        url = reverse('opportunity-list')
        data = {
            "title": "New Job",
            "opportunity_type": "job",
            "description": "Description",
            "link": "https://secure-link.com"
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['created_by_name'], self.user.username)

    def test_https_validation(self):
        """Test that insecure links are rejected."""
        url = reverse('opportunity-list')
        data = {"title": "Bad Link", "link": "http://insecure.com"} # Note: http instead of https
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("HTTPS", str(response.data['link']))

    def test_edit_window_enforcement(self):
        """Test that editing is blocked after the time limit."""
        # Manually backdate the opportunity
        self.opportunity.posted_at = timezone.now() - timedelta(hours=25)
        self.opportunity.save()

        url = reverse('opportunity-detail', kwargs={'pk': self.opportunity.pk})
        data = {"title": "Updated Title"}
        response = self.client.patch(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("edit window", str(response.data['non_field_errors']))

    def test_unauthorized_edit(self):
        """Test that User B cannot edit User A's post."""
        self.client.force_authenticate(user=self.other_user)
        url = reverse('opportunity-detail', kwargs={'pk': self.opportunity.pk})
        response = self.client.patch(url, {"title": "Hacked Title"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

class BookmarkTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='password123')
        self.opp = Opportunity.objects.create(title="Save Me", link="https://test.com")
        self.client.force_authenticate(user=self.user)

    def test_duplicate_bookmark_prevention(self):
        url = reverse('bookmark-list')
        data = {"opportunity_id": self.opp.id}
        # First save
        self.client.post(url, data)
        # Second save
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)