import os

from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

# Celery >= 5.6 gives CELERY_* environment variables precedence over Django
# settings. A local .env that points CELERY_BROKER_URL at Redis would then
# silently defeat config.settings.development's in-memory broker. Mirror the
# resolved Django settings back into the environment so they stay the single
# source of truth.
os.environ['CELERY_BROKER_URL'] = settings.CELERY_BROKER_URL
os.environ['CELERY_RESULT_BACKEND'] = settings.CELERY_RESULT_BACKEND

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
