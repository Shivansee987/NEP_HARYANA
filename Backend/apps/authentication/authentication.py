import time

from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from django.contrib.auth import get_user_model
from django.core.cache import cache
from .utils import ACCESS, decode_token

User = get_user_model()

USER_AUTH_CACHE_TTL = 60  # seconds


def get_user_cache_key(user_id: int) -> str:
    return f"jwt_user_auth_{user_id}"


def invalidate_user_cache(user_id: int):
    """Call whenever user password, token_version, status, or role changes."""
    cache.delete(get_user_cache_key(user_id))


def _revoked_access_key(jti: str) -> str:
    return f"jwt_revoked_access_{jti}"


def revoke_access_token(payload) -> None:
    """
    Rejects one access token for the rest of its lifetime (logout, S-12). Other sessions of the same user are not
    affected; ending all of them is user.revoke_sessions().
    """
    jti = (payload or {}).get('jti')
    exp = (payload or {}).get('exp')
    if not jti or not exp:
        return
    remaining = int(exp - time.time())
    if remaining > 0:
        cache.set(_revoked_access_key(jti), True, timeout=remaining)


class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None
            
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            raise exceptions.AuthenticationFailed('Authorization header must be Bearer <token>')
            
        access_token = parts[1]
        
        payload = decode_token(access_token, ACCESS)
        if not payload:
            raise exceptions.AuthenticationFailed('Invalid or expired access token')
            
        user_id = payload.get('user_id')
        if not user_id:
            raise exceptions.AuthenticationFailed('Token lacks user ID')

        jti = payload.get('jti')
        if jti and cache.get(_revoked_access_key(jti)):
            raise exceptions.AuthenticationFailed('Session has been revoked. Please sign in again.')
            
        cache_key = get_user_cache_key(user_id)
        user = cache.get(cache_key)

        if user is None:
            try:
                user = User.objects.select_related('college', 'university').get(id=user_id)
            except User.DoesNotExist:
                raise exceptions.AuthenticationFailed('User not found')
            
            # Cache active user for short duration to eliminate duplicate DB lookups
            if user.is_active:
                cache.set(cache_key, user, timeout=USER_AUTH_CACHE_TTL)
            
        if not user.is_active:
            raise exceptions.AuthenticationFailed('User account is disabled')

        if payload.get('tv') != user.token_version:
            raise exceptions.AuthenticationFailed('Session has been revoked. Please sign in again.')
            
        return (user, payload)

    def authenticate_header(self, request):
        return 'Bearer'
