from django.test import TestCase
from django.contrib.auth import get_user_model, authenticate
from profiles.models import Profile, EnablerProfileExtra, PathfinderProfileExtra
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

logger.info("Starting Authentication tests...")
class AfrivateLogicTest(TestCase):
    def setUp(self):
        logger.info("Setting up test data for Authentication tests.")
        self.password = "SecurePass123!"

    def test_signal_creates_enabler_profile(self):
        """Checks if an Enabler user automatically gets the right profile pipes."""
        logger.info("Testing signal for Enabler profile creation.")
        user = User.objects.create_user(
            username="enabler_test", 
            email="enabler@test.com", 
            password=self.password, 
            role="enabler"
        )
        self.assertTrue(Profile.objects.filter(user=user).exists())
        logger.info(f"Profile created for user: {user.username} (ID: {user.id})")
        self.assertTrue(EnablerProfileExtra.objects.filter(profile=user.profile).exists())
        logger.info(f"EnablerProfileExtra created for user: {user.username} (ID: {user.id})")


    def test_signal_creates_pathfinder_profile(self):
        """Checks if a Pathfinder user automatically gets the right profile pipes."""
        logger.info("Testing signal for Pathfinder profile creation.")
        user = User.objects.create_user(
            username="pathfinder_test", 
            email="pathfinder@gmail.com",
            password=self.password,
            role="pathfinder"
        )

        self.assertTrue(Profile.objects.filter(user=user).exists()) # Check if base profile is created
        logger.info(f"Profile created for user: {user.username} (ID: {user.id})")
        self.assertTrue(PathfinderProfileExtra.objects.filter(profile=user.profile).exists()) # Check if PathfinderProfileExtra is created
        logger.info(f"PathfinderProfileExtra created for user: {user.username} (ID: {user.id})")

    def test_custom_auth_backend(self):
        """Checks if login works with both Email and Username."""
        logger.info("Testing custom authentication backend for both username and email login.")
        user = User.objects.create_user(
            username="pathfinder_test", 
            email="pathfinder@test.com", 
            password=self.password, 
            role="pathfinder"
        )
        # Test Username login
        try: 
            auth_user = authenticate(username="pathfinder_test", password=self.password)
            logger.info(f"Authentication with username returned: {auth_user}")
            self.assertEqual(auth_user, user)
            logger.info(f"Authentication successful for username: {user.username} (ID: {user.id})")
            # Test Email login
            auth_email = authenticate(username="pathfinder@test.com", password=self.password)
            logger.info(f"Authentication with email returned: {auth_email}")    
            self.assertEqual(auth_email, user)
            logger.info(f"Authentication successful for email: {user.email} (ID: {user.id})")
        except Exception as e:
            logger.error(f"Authentication test failed: {e}")
            self.fail(f"Authentication test raised an exception: {e}")

    def test_profile_data_integrity(self):
        """Ensures that the profile data matches the user data."""
        logger.info("Testing data integrity between User and Profile models.")
        user = User.objects.create_user(
            username="data_integrity_test", 
            email="data_integrity@test.com",
            password=self.password,
            role="pathfinder",
            first_name="Data",
            last_name="Integrity"
        )
        profile = Profile.objects.get(user=user)
        logger.info(f"Checking profile data for user: {user.username} (ID: {user.id})")
        self.assertEqual(profile.contact_email, user.email)
        logger.info(f"Profile contact_email matches user email for user: {user.username} (ID: {user.id})")
        pathfinder_extra = PathfinderProfileExtra.objects.get(profile=profile)
        self.assertEqual(pathfinder_extra.first_name, user.first_name)
        self.assertEqual(pathfinder_extra.last_name, user.last_name)
        self.assertEqual(pathfinder_extra.gmail, user.email)
        logger.info(f"PathfinderProfileExtra data matches user data for user: {user.username} (ID: {user.id})")

    
logger.info("Authentication tests completed.")