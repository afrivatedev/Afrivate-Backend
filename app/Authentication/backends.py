from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
import logging

User = get_user_model()

class CustomAuthenticationBackend(ModelBackend):
    def authenticate(self, request, email_or_username=None, password=None, **kwargs):
        logging.info(f"Attempting to authenticate user: {email_or_username}")
        if email_or_username is None or password is None:
            logging.warning("Email/Username or password not provided for authentication")
            return None

        user = None # Initialize user to None
        try:
            # Try to fetch the user by email
            user = User.objects.get(email=email_or_username) # is this right

            # Check if the password is correct and if the user can authenticate
            if user.check_password(password) and self.user_can_authenticate(user):
                logging.info(f"User authenticated successfully: {email_or_username}")
                return user
            logging.warning(f"Authentication failed for user: {email_or_username}, user may be inactive")
            return None # Return None if authentication fails
        except User.DoesNotExist:
            logging.warning(f"User does not exist: {email_or_username}")
            return None

    def get_user(self, user_id):
        try:
            logging.info(f"Fetching user: {user_id}")
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            logging.warning(f"User does not exist: {user_id}")
            return None
        

"""
Make sure user is able to register and login using email/username and password
"""