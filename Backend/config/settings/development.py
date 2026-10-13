from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']

# Default to Console Email Backend in development so invitations print to console
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
