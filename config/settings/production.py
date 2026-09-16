from django.core.exceptions import ImproperlyConfigured

from .base import *

DEBUG = False

if not SECRET_KEY:
    raise ImproperlyConfigured('DJANGO_SECRET_KEY environment variable must be set in production.')
if len(SECRET_KEY) < 32 or SECRET_KEY.startswith('django-insecure'):
    raise ImproperlyConfigured(
        'DJANGO_SECRET_KEY is insecure: use a strong, randomly generated secret of at least 32 characters.'
    )

_allowed_hosts = os.getenv('ALLOWED_HOSTS') or os.getenv('DJANGO_ALLOWED_HOSTS') or ''
ALLOWED_HOSTS = [host.strip() for host in _allowed_hosts.split(',') if host.strip()]
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured('ALLOWED_HOSTS environment variable must be set in production.')

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Neon requires SSL
DATABASES['default']['OPTIONS'] = {
    'sslmode': os.getenv('DB_SSLMODE', 'require'),
}

# Use local memory cache (Render free tier has no Redis)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Disable Celery (requires Redis)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': True,
        },
    },
}
