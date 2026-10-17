from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import DEV_INSECURE_SECRET_KEY, os

DEBUG = False
# Never mounted in production, whatever the environment says (FIN-01).
ENABLE_DJANGO_ADMIN = False


def _require_strong_secret(name):
	value = os.environ.get(name, '')
	if not value or value == DEV_INSECURE_SECRET_KEY or value.startswith('django-insecure-') or len(value) < 50:
		raise ImproperlyConfigured(
			f"{name} must be set to a random value of at least 50 characters in production "
			f"(the committed development key is refused)."
		)
	return value


SECRET_KEY = _require_strong_secret('DJANGO_SECRET_KEY')
JWT_SIGNING_KEY = _require_strong_secret('JWT_SIGNING_KEY') if os.environ.get('JWT_SIGNING_KEY') else SECRET_KEY
JWT_PREVIOUS_SIGNING_KEYS = [
	k for k in JWT_PREVIOUS_SIGNING_KEYS if k != DEV_INSECURE_SECRET_KEY and not k.startswith('django-insecure-')  # noqa: F405
]

if not ALLOWED_HOSTS:  # noqa: F405
	raise ImproperlyConfigured("ALLOWED_HOSTS must list the production host names.")


def _require_postgres_database():
	"""
	Production data lives only in an explicitly configured PostgreSQL database. There is no fallback: base.py's
	SQLite defaults (the repository's db.sqlite3, or the test-runner switch) never apply here (FIN-07).
	"""
	import dj_database_url

	url = os.environ.get('DATABASE_URL', '').strip()
	if not url:
		raise ImproperlyConfigured("DATABASE_URL must point to the production PostgreSQL database.")
	try:
		config = dj_database_url.parse(url, conn_max_age=600, conn_health_checks=True)
	except Exception as exc:
		raise ImproperlyConfigured("DATABASE_URL is not a valid database URL.") from exc
	if config.get('ENGINE') not in ('django.db.backends.postgresql', 'django.contrib.gis.db.backends.postgis'):
		raise ImproperlyConfigured("Production requires a PostgreSQL DATABASE_URL (SQLite and other engines are refused).")
	return {'default': config}


DATABASES = _require_postgres_database()

_DEV_SMS_BACKENDS = ('apps.authentication.sms.ConsoleSMSBackend', 'apps.authentication.sms.LocmemSMSBackend')
if SMS_BACKEND in _DEV_SMS_BACKENDS:  # noqa: F405
	raise ImproperlyConfigured("A development SMS backend cannot be used in production.")

if EMAIL_BACKEND in ('django.core.mail.backends.console.EmailBackend', 'django.core.mail.backends.locmem.EmailBackend'):  # noqa: F405
	raise ImproperlyConfigured("A development e-mail backend cannot be used in production.")

SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'True').lower() in ('true', '1')
SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', 60 * 60 * 24 * 30))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get('SECURE_HSTS_INCLUDE_SUBDOMAINS', 'False').lower() in ('true', '1')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
if os.environ.get('SECURE_PROXY_SSL_HEADER', '').lower() in ('true', '1'):
	SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
