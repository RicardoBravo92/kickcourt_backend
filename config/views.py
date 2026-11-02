"""Project-wide infrastructure views (not domain logic)."""

import logging

from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


@never_cache
@require_GET
def health(request):
    """Liveness/readiness probe used by Render and external monitors.

    Returns 200 only when the database answers a trivial query. Kept
    dependency-free (no DRF, no auth) so it stays cheap under polling.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception:  # noqa: BLE001 - report, never raise from a probe
        logger.exception('Health check failed: database unreachable')
        return JsonResponse(
            {'status': 'error', 'database': 'unreachable'}, status=503
        )

    return JsonResponse({'status': 'ok', 'database': 'ok'})
