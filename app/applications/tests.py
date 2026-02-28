from django.test import TestCase

# Create your tests here.

def test_enabler_cannot_apply(self):
    """Checks that an Enabler cannot apply for an opportunity."""
    self.client.force_authenticate(user=self.enabler_user)
    response = self.client.post('/api/applications/', {'opportunity': self.opp.id, 'cover_letter': 'Hi'})
    self.assertEqual(response.status_code, 403) # Or 400 depending on your Permission class

def test_duplicate_application_fails(self):
    """Checks that a Pathfinder cannot apply twice."""
    self.client.force_authenticate(user=self.pathfinder_user)
    # First attempt
    self.client.post('/api/applications/', {'opportunity': self.opp.id, 'cover_letter': 'Hi'})
    # Second attempt
    response = self.client.post('/api/applications/', {'opportunity': self.opp.id, 'cover_letter': 'Hi again'})
    self.assertEqual(response.status_code, 400)
    self.assertIn("already applied", response.data['detail'])