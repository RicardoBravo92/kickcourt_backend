from .base import *

SECRET_KEY = 'test-secret-key-not-for-production'

DEBUG = True
ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'test_db.sqlite3',
        'TEST': {
            'NAME': BASE_DIR / 'test_db.sqlite3',
        },
    }
}

# Disable migrations for speed
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Faster password hashing (secure but fast for tests)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

# Email backend (console for any Django mail usage)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Celery always eager, so email tasks run synchronously
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Local memory cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Disable throttling in tests (keep the base scopes so throttle classes that
# reference 'auth' / 'check_availability' do not blow up with a 500).
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    **REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'],
    'anon': None,
    'user': None,
    'auth': None,
    'check_availability': None,
}

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}