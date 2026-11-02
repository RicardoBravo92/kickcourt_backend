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

# Validate CORS origins in production - no wildcards
_raw_cors = os.getenv('CORS_ALLOWED_ORIGINS', '')
if _raw_cors:
    cors_origins = [o.strip() for o in _raw_cors.split(',') if o.strip()]
    for origin in cors_origins:
        if '*' in origin or origin.count('//') > 1:
            raise ImproperlyConfigured(f'Invalid CORS origin in production: {origin}')

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Security headers
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'

# Media: Render's disk is ephemeral, so uploads (court images) must live in
# object storage. Setting AWS_STORAGE_BUCKET_NAME enables S3-compatible
# storage (AWS S3, Cloudflare R2, Backblaze B2, MinIO...).
_s3_bucket = os.getenv('AWS_STORAGE_BUCKET_NAME', '')
if _s3_bucket:
    _s3_options = {
        'bucket_name': _s3_bucket,
        'querystring_auth': False,
        'file_overwrite': False,
    }
    if os.getenv('AWS_S3_REGION_NAME'):
        _s3_options['region_name'] = os.getenv('AWS_S3_REGION_NAME')
    if os.getenv('AWS_S3_ENDPOINT_URL'):
        _s3_options['endpoint_url'] = os.getenv('AWS_S3_ENDPOINT_URL')
    _s3_domain = os.getenv('AWS_S3_CUSTOM_DOMAIN', '')
    if _s3_domain:
        _s3_options['custom_domain'] = _s3_domain

    STORAGES['default'] = {
        'BACKEND': 'storages.backends.s3.S3Storage',
        'OPTIONS': _s3_options,
    }
    _media_base = _s3_domain or f'{_s3_bucket}.s3.amazonaws.com'
    MEDIA_URL = os.getenv('MEDIA_URL', f'https://{_media_base}/')

# Static files: WhiteNoise serves them from the ASGI process, so no separate
# CDN/nginx is required. Manifest storage adds hashed, compressed filenames.
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# Media: Render's disk is ephemeral, so uploaded files (court images) must go
# to object storage. Point these at any S3-compatible bucket (AWS S3,
# Cloudflare R2, Backblaze B2, ...). Without a bucket, Django keeps using the
# local filesystem (fine for development, unsuitable for production).
_media_bucket = os.getenv('AWS_STORAGE_BUCKET_NAME', '')
if _media_bucket:
    STORAGES['default'] = {
        'BACKEND': 'storages.backends.s3.S3Storage',
        'OPTIONS': {
            'bucket_name': _media_bucket,
            'region_name': os.getenv('AWS_S3_REGION_NAME') or None,
            'endpoint_url': os.getenv('AWS_S3_ENDPOINT_URL') or None,
            'custom_domain': os.getenv('AWS_S3_CUSTOM_DOMAIN') or None,
            'querystring_auth': False,
            'file_overwrite': False,
        },
    }
    MEDIA_URL = os.getenv('MEDIA_URL', f'https://{_media_bucket}.s3.amazonaws.com/')

# Content Security Policy (django-csp >= 4.0 uses this dict format).
# The middleware is enabled in production.py only, so the Angular dev server
# (HMR + WebSockets) is not affected locally.
CONTENT_SECURITY_POLICY = {
    'DIRECTIVES': {
        'default-src': ["'self'"],
        'script-src': ["'self'"],
        'style-src': ["'self'", "'unsafe-inline'"],
        'img-src': ["'self'", 'data:', 'https:'],
        'font-src': ["'self'"],
        'connect-src': ["'self'", 'https:'],
        'object-src': ["'none'"],
        'frame-ancestors': ["'none'"],
        'base-uri': ["'self'"],
        'form-action': ["'self'"],
    }
}

# Attach the CSP middleware right after SecurityMiddleware.
MIDDLEWARE.insert(
    MIDDLEWARE.index('django.middleware.security.SecurityMiddleware') + 1,
    'csp.middleware.CSPMiddleware',
)

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

# Channels: use Redis when available, otherwise in-memory (single-process only).
# WARNING: the in-memory layer does not share WebSocket state across processes,
# so production should either point REDIS_URL at a real Redis or run daphne with
# a single worker.
_redis_url = os.getenv('REDIS_URL', '')
if _redis_url and _redis_url != 'redis://localhost:6379/0':
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {'hosts': [_redis_url]},
        },
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

# Celery: run eagerly only when no broker is configured. With Redis in
# production (REDIS_URL) tasks must be dispatched asynchronously, otherwise
# every booking request performs the email send inline.
CELERY_TASK_ALWAYS_EAGER = not bool(
    os.getenv('CELERY_BROKER_URL') or os.getenv('REDIS_URL')
)
CELERY_TASK_EAGER_PROPAGATES = False

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
