from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken


def revoke_all_sessions(user):
    """Blacklist every refresh token issued to this user.

    Used after a password reset or change, so a stolen refresh token stops
    working and every signed-in device has to sign in again. Access tokens
    expire on their own within the hour.
    """
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)
