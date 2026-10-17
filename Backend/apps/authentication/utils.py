import datetime
import hashlib
import jwt
import uuid
from django.conf import settings
from django.utils import timezone
from .models import RefreshToken

ACCESS = 'access'
REFRESH = 'refresh'


def _signing_key():
    return getattr(settings, 'JWT_SIGNING_KEY', None) or settings.SECRET_KEY


def _verification_keys():
    """Current signing key first, then retired keys still accepted during a staged rotation."""
    keys = [_signing_key()]
    keys += [k for k in getattr(settings, 'JWT_PREVIOUS_SIGNING_KEYS', []) if k and k not in keys]
    return keys


def _encode(user, token_type, lifetime, **extra):
    now = timezone.now()
    payload = {
        'user_id': user.id,
        'typ': token_type,
        'tv': user.token_version,
        'exp': now + lifetime,
        'iat': now,
        **extra,
    }
    return jwt.encode(payload, _signing_key(), algorithm='HS256')


def generate_access_token(user):
    minutes = getattr(settings, 'JWT_ACCESS_TOKEN_MINUTES', 15)
    return _encode(user, ACCESS, datetime.timedelta(minutes=minutes), email=user.email, role=user.role)


def generate_refresh_token(user):
    days = getattr(settings, 'JWT_REFRESH_TOKEN_DAYS', 7)
    return _encode(user, REFRESH, datetime.timedelta(days=days), jti=str(uuid.uuid4()))


def decode_token(token, expected_type=None):
    """
    Returns the payload of a valid, unexpired token signed with a current or retired key, or None.
    When expected_type is given the token's "typ" claim must match, so a refresh token can never be
    used as an access token (and vice versa).
    """
    for key in _verification_keys():
        try:
            payload = jwt.decode(token, key, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            continue
        if expected_type and payload.get('typ') != expected_type:
            return None
        return payload
    return None


def hash_token(token_str):
    return hashlib.sha256(token_str.encode('utf-8')).hexdigest()


def generate_auth_tokens(user):
    access_token = generate_access_token(user)
    refresh_token = generate_refresh_token(user)

    hashed = hash_token(refresh_token)
    decoded_refresh = decode_token(refresh_token, REFRESH)
    expires_at = datetime.datetime.fromtimestamp(decoded_refresh['exp'], tz=datetime.timezone.utc)

    RefreshToken.objects.create(
        user=user,
        token=hashed,
        expires_at=expires_at
    )
    return {
        'access': access_token,
        'refresh': refresh_token
    }


def rotate_refresh_token_header(old_refresh_token_str):
    payload = decode_token(old_refresh_token_str, REFRESH)
    if not payload:
        return None

    hashed_old = hash_token(old_refresh_token_str)

    try:
        db_token = RefreshToken.objects.select_related('user').get(token=hashed_old)
    except RefreshToken.DoesNotExist:
        return None

    user = db_token.user

    if db_token.is_revoked:
        # Reuse of a rotated token: revoke the whole family.
        RefreshToken.objects.filter(user=user, is_revoked=False).update(is_revoked=True)
        return None

    if db_token.expires_at < timezone.now() or not user.is_active or payload.get('tv') != user.token_version:
        db_token.is_revoked = True
        db_token.save(update_fields=['is_revoked'])
        return None

    db_token.is_revoked = True
    db_token.save(update_fields=['is_revoked'])

    return generate_auth_tokens(user)
