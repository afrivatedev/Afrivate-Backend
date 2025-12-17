from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from user_database.models import WaitlistEmail


class WaitlistEntryModelTest(TestCase):
    def test_create_entry(self):
        """Test creating a waitlist entry"""
        entry = WaitlistEmail.objects.create(
            email='test@example.com',
            name='Test User'
        )
        self.assertEqual(entry.email, 'test@example.com')
        self.assertEqual(entry.name, 'Test User')
        self.assertFalse(entry.is_notified)

    def test_email_uniqueness(self):
        """Test that emails must be unique"""
        WaitlistEmail.objects.create(email='test@example.com')
        
        with self.assertRaises(Exception):
            WaitlistEmail.objects.create(email='test@example.com')


class WaitlistAPITest(APITestCase):
    def setUp(self):
        self.signup_url = reverse('waitlist:signup')
        self.check_url = reverse('waitlist:check_email')
        self.stats_url = reverse('waitlist:stats')

    def test_successful_signup(self):
        """Test successful waitlist signup"""
        data = {
            'email': 'newuser@example.com',
            'name': 'New User',
            'referral_source': 'twitter'
        }
        response = self.client.post(self.signup_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(WaitlistEmail.objects.count(), 1)

    def test_duplicate_email(self):
        """Test that duplicate emails are rejected"""
        email = 'duplicate@example.com'
        
        # First signup
        self.client.post(self.signup_url, {'email': email}, format='json')
        
        # Second signup with same email
        response = self.client.post(self.signup_url, {'email': email}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertEqual(WaitlistEmail.objects.count(), 1)

    def test_invalid_email(self):
        """Test that invalid emails are rejected"""
        data = {'email': 'not-an-email'}
        response = self.client.post(self.signup_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

    def test_missing_email(self):
        """Test that missing email is rejected"""
        data = {'name': 'John Doe'}
        response = self.client.post(self.signup_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_check_email_exists(self):
        """Test checking if email exists"""
        email = 'existing@example.com'
        WaitlistEmail.objects.create(email=email)
        
        response = self.client.get(f'{self.check_url}?email={email}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['exists'])

    def test_check_email_not_exists(self):
        """Test checking if email doesn't exist"""
        response = self.client.get(f'{self.check_url}?email=notfound@example.com')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['exists'])

    def test_stats_endpoint(self):
        """Test statistics endpoint"""
        # Create some entries
        WaitlistEmail.objects.create(email='user1@example.com')
        WaitlistEmail.objects.create(email='user2@example.com')
        
        response = self.client.get(self.stats_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_signups'], 2)
        self.assertIn('signups_today', response.data)

    def test_rate_limiting(self):
        """Test that rate limiting works (requires proper throttle settings)"""
        # This test depends on your throttle settings
        # Make multiple requests rapidly
        for i in range(6):
            response = self.client.post(
                self.signup_url,
                {'email': f'user{i}@example.com'},
                format='json'
            )
        
        # The 6th request should be throttled (with 5/hour limit)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


# Run tests with:
# python manage.py test waitlist