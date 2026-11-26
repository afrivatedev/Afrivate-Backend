"""Per-account sign-in lockout.

After MAX_FAILED_ATTEMPTS wrong passwords for one account inside LOCKOUT_SECONDS,
sign-in for that account is refused until the window ends. The limit follows the
account, not the IP, so changing X-Forwarded-For does not get around it.

Keys are hashed, so emails are never stored in the cache as plain text.
"""
import hashlib

from django.core.cache import cache

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60
LOCKOUT_MESSAGE = "Too many failed sign-in attempts. Please try again in about 15 minutes."


def _key(scope, identifier):
    digest = hashlib.sha256(identifier.strip().lower().encode('utf-8')).hexdigest()
    return f"signin-fail:{scope}:{digest}"


def is_locked_out(scope, identifier):
    if not identifier:
        return False
    return (cache.get(_key(scope, identifier)) or 0) >= MAX_FAILED_ATTEMPTS


def record_failed_attempt(scope, identifier):
    if not identifier:
        return
    key = _key(scope, identifier)
    # add() starts the window on the first failure; incr() counts the rest.
    cache.add(key, 0, LOCKOUT_SECONDS)
    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, LOCKOUT_SECONDS)


def clear_failed_attempts(scope, identifier):
    if identifier:
        cache.delete(_key(scope, identifier))
