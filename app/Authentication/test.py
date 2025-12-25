# from django.test import TestCase
# from django.urls import reverse
# from rest_framework.test import APITestCase
# from rest_framework import status
# from user_database.models import WaitlistEmail


# class WaitlistEntryModelTest(TestCase):
#     def test_create_entry(self):
#         """Test creating a waitlist entry"""
#         entry = WaitlistEmail.objects.create(
#             email='test@example.com',
#             name='Test User'
#         )
#         self.assertEqual(entry.email, 'test@example.com')
#         self.assertEqual(entry.name, 'Test User')
#         self.assertFalse(entry.is_notified)

#     def test_email_uniqueness(self):
#         """Test that emails must be unique"""
#         WaitlistEmail.objects.create(email='test@example.com')
        
#         with self.assertRaises(Exception):
#             WaitlistEmail.objects.create(email='test@example.com')


# class WaitlistAPITest(APITestCase):
#     def setUp(self):
#         self.signup_url = reverse('waitlist:signup')
#         self.check_url = reverse('waitlist:check_email')
#         self.stats_url = reverse('waitlist:stats')

#     def test_successful_signup(self):
#         """Test successful waitlist signup"""
#         data = {
#             'email': 'newuser@example.com',
#             'name': 'New User',
#             'referral_source': 'twitter'
#         }
#         response = self.client.post(self.signup_url, data, format='json')
        
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
#         self.assertTrue(response.data['success'])
#         self.assertEqual(WaitlistEmail.objects.count(), 1)

#     def test_duplicate_email(self):
#         """Test that duplicate emails are rejected"""
#         email = 'duplicate@example.com'
        
#         # First signup
#         self.client.post(self.signup_url, {'email': email}, format='json')
        
#         # Second signup with same email
#         response = self.client.post(self.signup_url, {'email': email}, format='json')
        
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#         self.assertFalse(response.data['success'])
#         self.assertEqual(WaitlistEmail.objects.count(), 1)

#     def test_invalid_email(self):
#         """Test that invalid emails are rejected"""
#         data = {'email': 'not-an-email'}
#         response = self.client.post(self.signup_url, data, format='json')
        
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#         self.assertFalse(response.data['success'])

#     def test_missing_email(self):
#         """Test that missing email is rejected"""
#         data = {'name': 'John Doe'}
#         response = self.client.post(self.signup_url, data, format='json')
        
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

#     def test_check_email_exists(self):
#         """Test checking if email exists"""
#         email = 'existing@example.com'
#         WaitlistEmail.objects.create(email=email)
        
#         response = self.client.get(f'{self.check_url}?email={email}')
        
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertTrue(response.data['exists'])

#     def test_check_email_not_exists(self):
#         """Test checking if email doesn't exist"""
#         response = self.client.get(f'{self.check_url}?email=notfound@example.com')
        
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertFalse(response.data['exists'])

#     def test_stats_endpoint(self):
#         """Test statistics endpoint"""
#         # Create some entries
#         WaitlistEmail.objects.create(email='user1@example.com')
#         WaitlistEmail.objects.create(email='user2@example.com')
        
#         response = self.client.get(self.stats_url)
        
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.data['total_signups'], 2)
#         self.assertIn('signups_today', response.data)

#     def test_rate_limiting(self):
#         """Test that rate limiting works (requires proper throttle settings)"""
#         # This test depends on your throttle settings
#         # Make multiple requests rapidly
#         for i in range(6):
#             response = self.client.post(
#                 self.signup_url,
#                 {'email': f'user{i}@example.com'},
#                 format='json'
#             )
        
#         # The 6th request should be throttled (with 5/hour limit)
#         self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


# # Run tests with:
# # python manage.py test waitlist

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch
from user_database.models import WaitlistEmail

class WaitlistEmailViewTests(APITestCase):
    def setUp(self):
        self.url = reverse('accounts:waitlist-email')
        self.valid_payload = {
            "email": "test@example.com",
            "name": "John Doe"
        }

    @patch('Authentication.views.send_waitlist_verification_email') 
    def test_waitlist_signup_success(self, mock_send_email):
        """Test successful waitlist signup and email trigger"""
        
        mock_send_email.return_return_value = True
        
        response = self.client.post(self.url, self.valid_payload, format='json')
        
        # Assertions
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(WaitlistEmail.objects.count(), 1)
        self.assertEqual(WaitlistEmail.objects.get().email, "test@example.com")
        self.assertTrue(mock_send_email.called)

    def test_waitlist_signup_invalid_email(self):
        """Test signup fails with bad email format"""
        invalid_payload = {"email": "not-an-email", "name": "John"}
        response = self.client.post(self.url, invalid_payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('errors', response.data)

    @patch('Authentication.views.send_waitlist_verification_email')
    def test_email_send_failure(self, mock_send_email):
        """Test response when email service fails"""
        mock_send_email.return_value = False # Simulate email failure
        
        response = self.client.post(self.url, self.valid_payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertFalse(response.data['success'], False)
        self.assertEqual(response.data['message'], 'Failed to send verification email. Please try again.')


# from django.utils import timezone
# from datetime import timedelta
# from django.urls import reverse
# from rest_framework import status
# from rest_framework.test import APITestCase
# from .models import EmailVerification, WaitlistEmail

# class VerifyEmailViewTests(APITestCase):
#     def setUp(self):
#         self.url = reverse('accounts:verify-email')
        
#         # Create a valid waitlist entry and verification token
#         self.waitlist_entry = WaitlistEmail.objects.create(email="user@example.com")
#         self.verification = EmailVerification.create_verification(
#             email="user@example.com",
#             verification_type='waitlist'
#         )
#         self.waitlist_entry.verification = self.verification
#         self.waitlist_entry.save()

#     def test_successful_verification(self):
#         """Test that a valid token verifies the email"""
#         response = self.client.get(f"{self.url}?token={self.verification.token}")
        
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.verification.refresh_from_db()
#         self.waitlist_entry.refresh_from_db()
#         self.assertTrue(self.verification.is_verified)
#         self.assertTrue(self.waitlist_entry.is_verified)

#     def test_expired_token(self):
#         """Test that an expired token returns a 400 error"""
#         # Manually expire the token
#         self.verification.expires_at = timezone.now() - timedelta(hours=1)
#         self.verification.save()
        
#         response = self.client.get(f"{self.url}?token={self.verification.token}")
        
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#         self.assertIn("expired", response.data['message'].lower())

#     def test_invalid_token(self):
#         """Test that a non-existent token returns a 400 error"""
#         response = self.client.get(f"{self.url}?token=wrong-token-123")
        
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)