from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']
ENABLE_DJANGO_ADMIN = True

# Default to Console Email Backend in development so invitations print to console
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')

# Local development prints SMS messages (including OTP codes) to the runserver console instead of sending them.
SMS_BACKEND = os.environ.get('SMS_BACKEND', 'apps.authentication.sms.ConsoleSMSBackend')
if 'test' in sys.argv:
	SMS_BACKEND = 'apps.authentication.sms.LocmemSMSBackend'
