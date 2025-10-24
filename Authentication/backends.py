from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model


User = get_user_model()

class CustomAuthenticationBackend(ModelBackend):
    def authenticate(self, request, email=None, password=None, **kwargs):
        if email is None or password is None:
            return None

        user = None # Initialize user to None

        try:
            # Try to fetch the user by email
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            print(f"User does not exist: {email}")
            return None

        # Check if the password is correct and if the user can authenticate
        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None # Return None if authentication fails

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None